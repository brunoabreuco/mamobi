import hashlib
from unittest.mock import MagicMock

import pytest
from flask import Flask

from datetime import datetime, timezone, timedelta
from mamobi.models import User, db, Event, EventParticipation, EventCategory
from mamobi.api_routes import api
from mamobi.auth import issue_tokens


# ------------------------------------------------------------------ fixtures

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = "test-secret-key-32chars-padding!!"

    db.init_app(app)

    # Mock Supabase -- nenhum teste faz chamada de rede real
    app.extensions["supabase"] = MagicMock()

    app.register_blueprint(api)

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def supabase_mock(app):
    return app.extensions["supabase"]


def _create_user(app, **kwargs) -> User:
    defaults = {
        "phone": "+5511999990000",
        "full_name": "Maria Teste",
        "neighborhood": "Centro",
        "role": "participante",
        "is_active": True,
    }
    defaults.update(kwargs)
    with app.app_context():
        user = User(**defaults)
        db.session.add(user)
        db.session.commit()
        # Retorna id para recarregar fora do contexto
        return user.id

# _auth_header: emite JWT real em vez de mockar supabase
def _auth_header(app, user_id: str) -> dict:
    with app.app_context():
        user = db.session.get(User, user_id)
        tokens = issue_tokens(str(user.id), user.role)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


# ------------------------------------------------------------------ GET /api/me

def test_get_me_sem_token_retorna_401(client):
    resp = client.get("/api/me")
    assert resp.status_code == 401


def test_get_me_token_invalido_retorna_401(client, supabase_mock):
    supabase_mock.auth.get_user.side_effect = Exception("invalid jwt")
    resp = client.get("/api/me", headers={"Authorization": "Bearer invalido"})
    assert resp.status_code == 401


def test_get_me_retorna_perfil_correto(client, app):
    uid = _create_user(app, full_name="Maria Silva", phone="+5511999990001")
    headers = _auth_header(app, uid)

    resp = client.get("/api/me", headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["full_name"] == "Maria Silva"
    assert data["phone"] == "+5511999990001"
    assert "role" in data


def test_get_me_retorna_counts_corretos(client, app):
    uid = _create_user(app, full_name="Maria Silva", phone="+5511999990020")
    headers = _auth_header(app, uid)

    with app.app_context():
        category = EventCategory(name="Saúde")
        db.session.add(category)
        db.session.commit()
        
        # Create 1 event as organizer
        event = Event(
            title="Ação Teste",
            event_datetime=datetime.now(timezone.utc) + timedelta(days=1),
            location_name="Rua Teste",
            category_id=category.id,
            organizer_id=uid,
            status="active"
        )
        db.session.add(event)
        db.session.commit()
        
        # Create 1 participation as confirmed
        participation = EventParticipation(
            event_id=event.id, user_id=uid, status="confirmed"
        )
        db.session.add(participation)
        db.session.commit()

    resp = client.get("/api/me", headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["created_events_count"] == 1
    assert data["participated_events_count"] == 1


def test_get_me_usuario_inativo_retorna_404(client, app):
    uid = _create_user(app, phone="+5511999990002", is_active=False)
    headers = _auth_header(app, uid)

    resp = client.get("/api/me", headers=headers)
    assert resp.status_code == 404


# ------------------------------------------------------------------ PATCH /api/me

def test_patch_me_atualiza_full_name(client, app):
    uid = _create_user(app, phone="+5511999990003")
    headers = _auth_header(app, uid)

    resp = client.patch("/api/me", json={"full_name": "Maria Atualizada"}, headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["profile"]["full_name"] == "Maria Atualizada"

    with app.app_context():
        user = db.session.get(User, uid)
        assert user.full_name == "Maria Atualizada"


def test_patch_me_tenta_alterar_role_retorna_400(client, app):
    uid = _create_user(app, phone="+5511999990004")
    headers = _auth_header(app, uid)

    resp = client.patch("/api/me", json={"role": "organizadora"}, headers=headers)
    assert resp.status_code == 400


def test_patch_me_phone_diferente_dispara_otp_e_nao_atualiza(client, app, supabase_mock):
    uid = _create_user(app, phone="+5511999990005")
    headers = _auth_header(app, uid)
    supabase_mock.auth.sign_in_with_otp.return_value = MagicMock()

    resp = client.patch("/api/me", json={"phone": "+5511888880005"}, headers=headers)
    assert resp.status_code == 202
    assert resp.get_json()["phone_change_pending"] is True

    supabase_mock.auth.sign_in_with_otp.assert_called_once_with({"phone": "+5511888880005"})

    with app.app_context():
        user = db.session.get(User, uid)
        assert user.phone == "+5511999990005"       # nao mudou
        assert user.pending_phone == "+5511888880005"


def test_patch_me_phone_igual_nao_dispara_otp(client, app, supabase_mock):
    uid = _create_user(app, phone="+5511999990006")
    headers = _auth_header(app, uid)

    resp = client.patch("/api/me", json={"phone": "+5511999990006"}, headers=headers)
    assert resp.status_code == 200
    supabase_mock.auth.sign_in_with_otp.assert_not_called()


# ------------------------------------------------------------------ POST /api/me/phone/confirm

def test_confirm_phone_valido_atualiza_telefone(client, app, supabase_mock):
    uid = _create_user(app, phone="+5511999990007", pending_phone="+5511888880007")
    headers = _auth_header(app, uid)
    supabase_mock.auth.verify_otp.return_value = MagicMock()

    resp = client.post("/api/me/phone/confirm", json={"token": "123456"}, headers=headers)
    assert resp.status_code == 200

    with app.app_context():
        user = db.session.get(User, uid)
        assert user.phone == "+5511888880007"
        assert user.pending_phone is None


def test_confirm_phone_sem_pending_retorna_400(client, app):
    uid = _create_user(app, phone="+5511999990008")
    headers = _auth_header(app, uid)

    resp = client.post("/api/me/phone/confirm", json={"token": "123456"}, headers=headers)
    assert resp.status_code == 400


def test_confirm_phone_otp_invalido_retorna_401(client, app, supabase_mock):
    uid = _create_user(app, phone="+5511999990009", pending_phone="+5511888880009")
    headers = _auth_header(app, uid)
    supabase_mock.auth.verify_otp.side_effect = Exception("invalid otp")

    resp = client.post("/api/me/phone/confirm", json={"token": "000000"}, headers=headers)
    assert resp.status_code == 401

    with app.app_context():
        user = db.session.get(User, uid)
        assert user.phone == "+5511999990009"  # nao mudou


def test_confirm_phone_token_formato_invalido_retorna_400(client, app):
    uid = _create_user(app, phone="+5511999990010", pending_phone="+5511888880010")
    headers = _auth_header(app, uid)

    resp = client.post("/api/me/phone/confirm", json={"token": "abc"}, headers=headers)
    assert resp.status_code == 400


# ------------------------------------------------------------------ DELETE /api/me

def test_delete_me_retorna_204(client, app):
    uid = _create_user(app, phone="+5511999990011")
    headers = _auth_header(app, uid)

    resp = client.delete("/api/me", headers=headers)
    assert resp.status_code == 204


def test_delete_me_anonimiza_dados(client, app):
    uid = _create_user(app, phone="+5511999990012", full_name="Maria Secreta",
                       avatar_url="https://exemplo.com/foto.jpg")
    headers = _auth_header(app, uid)

    client.delete("/api/me", headers=headers)

    with app.app_context():
        user = db.session.get(User, uid)
        assert user.full_name == "Removido"
        assert user.avatar_url is None
        assert user.is_active is False
        assert user.phone != "+5511999990012"
        assert user.phone.startswith("del_")


def test_delete_me_impede_acesso_posterior(client, app):
    uid = _create_user(app, phone="+5511999990013")
    headers = _auth_header(app, uid)

    client.delete("/api/me", headers=headers)

    resp = client.get("/api/me", headers=headers)
    assert resp.status_code == 404


def test_delete_me_chama_supabase_delete_user(client, app, supabase_mock):
    uid = _create_user(app, phone="+5511999990014")
    headers = _auth_header(app, uid)

    client.delete("/api/me", headers=headers)

    supabase_mock.auth.admin.delete_user.assert_called_once_with(uid)