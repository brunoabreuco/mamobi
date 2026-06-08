import os
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from maes_mobilizadoras.app_factory import create_app
from maes_mobilizadoras.auth import issue_tokens
from maes_mobilizadoras.models import db, User, EventCategory, Event

from conftest import _TEST_ENV


@pytest.fixture
def app():
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-key-32chars-padding!!",
        "RATELIMIT_STORAGE_URI": "memory://",
        "RATELIMIT_ENABLED": True,
    }
    with patch.dict(os.environ, _TEST_ENV):
        with patch("maes_mobilizadoras.app_factory.create_client") as mock_supabase:
            mock_supabase.return_value = MagicMock()
            application = create_app(test_config=test_config)

        with application.app_context():
            db.create_all()
            yield application
            db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def base_data(app):
    with app.app_context():
        # Cria categorias
        category = EventCategory(name="Saúde")
        db.session.add(category)

        # Cria usuários com diferentes roles
        organizadora = User(
            phone="11999999991",
            full_name="Maria Organizadora",
            neighborhood="Centro",
            role="organizadora",
        )
        coordenadora = User(
            phone="11999999992",
            full_name="Ana Coordenadora",
            neighborhood="Centro",
            role="coordenadora",
        )
        participante = User(
            phone="11999999993",
            full_name="Joana Participante",
            neighborhood="Centro",
            role="participante",
        )
        outra_organizadora = User(
            phone="11999999994",
            full_name="Carla Outra Organizadora",
            neighborhood="Centro",
            role="organizadora",
        )
        db.session.add_all([organizadora, coordenadora, participante, outra_organizadora, category])
        db.session.commit()

        db.session.refresh(organizadora)
        db.session.refresh(coordenadora)
        db.session.refresh(participante)
        db.session.refresh(outra_organizadora)
        db.session.refresh(category)

        return {
            "category_id": category.id,
            "organizadora_id": organizadora.id,
            "coordenadora_id": coordenadora.id,
            "participante_id": participante.id,
            "outra_organizadora_id": outra_organizadora.id,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_headers(user_id: str, role: str) -> dict:
    """Gera cabeçalho Authorization Bearer para o usuário informado."""
    tokens = issue_tokens(user_id, role)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _create_event(
    app,
    organizer_id: str,
    category_id: int,
    *,
    title: str = "Evento Teste",
    status: str = "draft",
    days_ahead: int = 5,
) -> str:
    """Persiste um evento e retorna seu id."""
    ev = Event(
        title=title,
        event_datetime=datetime.now(timezone.utc) + timedelta(days=days_ahead),
        location_name="Praça Central",
        category_id=category_id,
        organizer_id=organizer_id,
        status=status,
    )
    db.session.add(ev)
    db.session.commit()
    return ev.id


# ---------------------------------------------------------------------------
# POST /api/acoes
# ---------------------------------------------------------------------------

def test_create_acao_success(client, base_data):
    """TESTE: POST válido persiste e retorna 201"""
    payload = {
        "title": "Ação Comunitária",
        "description": "Limpeza da praça",
        "event_datetime": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "location_name": "Praça Central",
        "category_id": base_data["category_id"],
        "organizer_id": base_data["organizadora_id"],
        "max_participants": 50,
    }
    headers = _auth_headers(base_data["organizadora_id"], "organizadora")
    response = client.post("/api/acoes", json=payload, headers=headers)

    assert response.status_code == 201
    data = response.get_json()
    assert "data" in data
    assert "metadata" in data
    assert data["data"]["title"] == "Ação Comunitária"
    assert data["metadata"]["id"] is not None
    assert data["metadata"]["participant_count"] == 0


def test_create_acao_status_default_draft(client, base_data):
    """TESTE: status default deve ser draft"""
    payload = {
        "title": "Ação Comunitária",
        "event_datetime": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "location_name": "Praça Central",
        "category_id": base_data["category_id"],
        "organizer_id": base_data["organizadora_id"],
    }
    headers = _auth_headers(base_data["organizadora_id"], "organizadora")
    response = client.post("/api/acoes", json=payload, headers=headers)

    assert response.status_code == 201
    assert response.get_json()["data"]["status"] == "draft"


def test_create_acao_no_title(client, base_data):
    """TESTE: sem título retorna 400 com erro no campo title"""
    payload = {
        "description": "Limpeza da praça",
        "event_datetime": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "location_name": "Praça Central",
        "category_id": base_data["category_id"],
        "organizer_id": base_data["organizadora_id"],
    }
    headers = _auth_headers(base_data["organizadora_id"], "organizadora")
    response = client.post("/api/acoes", json=payload, headers=headers)

    assert response.status_code == 400
    data = response.get_json()
    assert "errors" in data
    assert "title" in data["errors"]


def test_create_acao_invalid_date(client, base_data):
    """TESTE: data inválida retorna 400 com erro no campo event_datetime"""
    payload = {
        "title": "Ação Comunitária",
        "event_datetime": "not-a-valid-date",
        "location_name": "Praça Central",
        "category_id": base_data["category_id"],
        "organizer_id": base_data["organizadora_id"],
    }
    headers = _auth_headers(base_data["organizadora_id"], "organizadora")
    response = client.post("/api/acoes", json=payload, headers=headers)

    assert response.status_code == 400
    data = response.get_json()
    assert "errors" in data
    assert "event_datetime" in data["errors"]


def test_create_acao_past_date(client, base_data):
    """TESTE: data no passado retorna 400"""
    payload = {
        "title": "Ação Comunitária",
        "event_datetime": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        "location_name": "Praça Central",
        "category_id": base_data["category_id"],
        "organizer_id": base_data["organizadora_id"],
    }
    headers = _auth_headers(base_data["organizadora_id"], "organizadora")
    response = client.post("/api/acoes", json=payload, headers=headers)

    assert response.status_code == 400
    data = response.get_json()
    assert "errors" in data


def test_create_acao_invalid_status(client, base_data):
    """TESTE: status inválido retorna 400"""
    payload = {
        "title": "Ação Comunitária",
        "event_datetime": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "location_name": "Praça Central",
        "category_id": base_data["category_id"],
        "organizer_id": base_data["organizadora_id"],
        "status": "invalido",
    }
    headers = _auth_headers(base_data["organizadora_id"], "organizadora")
    response = client.post("/api/acoes", json=payload, headers=headers)

    assert response.status_code == 400
    data = response.get_json()
    assert "errors" in data
    assert "status" in data["errors"]


def test_rate_limiting(client, base_data):
    """TESTE: 11ª requisição retorna 429"""
    payload = {
        "title": "Ação Comunitária",
        "event_datetime": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "location_name": "Praça Central",
        "category_id": base_data["category_id"],
        "organizer_id": base_data["organizadora_id"],
    }
    headers = _auth_headers(base_data["organizadora_id"], "organizadora")

    for i in range(10):
        response = client.post("/api/acoes", json=payload, headers=headers)
        assert response.status_code == 201

    response_limited = client.post("/api/acoes", json=payload, headers=headers)
    assert response_limited.status_code == 429


# ---------------------------------------------------------------------------
# GET /api/acoes (lista paginada)
# ---------------------------------------------------------------------------

def test_list_acoes_retorna_eventos_existentes(client, app, base_data):
    """TESTE: GET /api/acoes retorna lista com ações existentes"""
    _create_event(app, base_data["organizadora_id"], base_data["category_id"], title="Ação A")
    _create_event(app, base_data["organizadora_id"], base_data["category_id"], title="Ação B")

    headers = _auth_headers(base_data["organizadora_id"], "organizadora")
    response = client.get("/api/acoes", headers=headers)

    assert response.status_code == 200
    body = response.get_json()
    assert "items" in body
    assert "pagination" in body
    assert len(body["items"]) == 2
    assert body["pagination"]["total"] == 2
    titles = {item["data"]["title"] for item in body["items"]}
    assert titles == {"Ação A", "Ação B"}


def test_list_acoes_sem_resultados_retorna_lista_vazia(client, app, base_data):
    """TESTE: GET /api/acoes sem eventos retorna 200 com lista vazia"""
    headers = _auth_headers(base_data["organizadora_id"], "organizadora")
    response = client.get("/api/acoes", headers=headers)

    assert response.status_code == 200
    body = response.get_json()
    assert body["items"] == []
    assert body["pagination"]["total"] == 0


def test_list_acoes_filtro_status(client, app, base_data):
    """TESTE: GET /api/acoes com filtro de status retorna apenas ações do status informado"""
    _create_event(app, base_data["organizadora_id"], base_data["category_id"], status="draft")
    _create_event(app, base_data["organizadora_id"], base_data["category_id"], status="active")
    _create_event(app, base_data["organizadora_id"], base_data["category_id"], status="active")

    headers = _auth_headers(base_data["organizadora_id"], "organizadora")
    response = client.get("/api/acoes?status=active", headers=headers)

    assert response.status_code == 200
    body = response.get_json()
    assert body["pagination"]["total"] == 2
    assert all(item["data"]["status"] == "active" for item in body["items"])


# ---------------------------------------------------------------------------
# GET /api/acoes/<id>
# ---------------------------------------------------------------------------

def test_get_acao_retorna_correta(client, app, base_data):
    """TESTE: GET /api/acoes/<id> retorna a ação correta"""
    event_id = _create_event(
        app,
        base_data["organizadora_id"],
        base_data["category_id"],
        title="Evento Específico",
    )
    headers = _auth_headers(base_data["organizadora_id"], "organizadora")
    response = client.get(f"/api/acoes/{event_id}", headers=headers)

    assert response.status_code == 200
    body = response.get_json()
    assert body["metadata"]["id"] == event_id
    assert body["data"]["title"] == "Evento Específico"


def test_get_acao_inexistente_retorna_404(client, app, base_data):
    """TESTE: GET /api/acoes/<id> com id inexistente retorna 404"""
    headers = _auth_headers(base_data["organizadora_id"], "organizadora")
    response = client.get("/api/acoes/id-que-nao-existe", headers=headers)

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/acoes/<id>
# ---------------------------------------------------------------------------

def test_patch_atualiza_apenas_campos_enviados(client, app, base_data):
    """TESTE: PATCH atualiza apenas os campos enviados; demais permanecem inalterados"""
    event_id = _create_event(
        app,
        base_data["organizadora_id"],
        base_data["category_id"],
        title="Título Original",
        status="draft",
    )
    headers = _auth_headers(base_data["organizadora_id"], "organizadora")
    response = client.patch(
        f"/api/acoes/{event_id}",
        json={"title": "Título Atualizado"},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["data"]["title"] == "Título Atualizado"
    assert body["data"]["location_name"] == "Praça Central"
    assert body["data"]["status"] == "draft"


def test_patch_campo_invalido_retorna_400(client, app, base_data):
    """TESTE: PATCH com campo inválido (status fora do enum) retorna 400"""
    event_id = _create_event(app, base_data["organizadora_id"], base_data["category_id"])
    headers = _auth_headers(base_data["organizadora_id"], "organizadora")
    response = client.patch(
        f"/api/acoes/{event_id}",
        json={"status": "status_invalido"},
        headers=headers,
    )

    assert response.status_code == 400
    body = response.get_json()
    assert "errors" in body
    assert "status" in body["errors"]


def test_patch_nao_permite_alterar_organizer_id(client, app, base_data):
    """TESTE: PATCH não permite alterar organizer_id; retorna 400 com erro no campo"""
    event_id = _create_event(app, base_data["organizadora_id"], base_data["category_id"])
    headers = _auth_headers(base_data["organizadora_id"], "organizadora")
    response = client.patch(
        f"/api/acoes/{event_id}",
        json={"organizer_id": "outro-id-qualquer"},
        headers=headers,
    )

    assert response.status_code == 400
    body = response.get_json()
    assert "errors" in body
    assert "organizer_id" in body["errors"]


def test_patch_nao_permite_alterar_participant_count(client, app, base_data):
    """TESTE: PATCH não permite alterar participant_count; retorna 400 com erro no campo"""
    event_id = _create_event(app, base_data["organizadora_id"], base_data["category_id"])
    headers = _auth_headers(base_data["organizadora_id"], "organizadora")
    response = client.patch(
        f"/api/acoes/{event_id}",
        json={"participant_count": 99},
        headers=headers,
    )

    assert response.status_code == 400
    body = response.get_json()
    assert "errors" in body
    assert "participant_count" in body["errors"]


# ---------------------------------------------------------------------------
# DELETE /api/acoes/<id>
# ---------------------------------------------------------------------------

def test_delete_remove_acao_retorna_204(client, app, base_data):
    """TESTE: DELETE remove a ação e retorna 204"""
    event_id = _create_event(app, base_data["organizadora_id"], base_data["category_id"])
    headers = _auth_headers(base_data["organizadora_id"], "organizadora")
    response = client.delete(f"/api/acoes/{event_id}", headers=headers)

    assert response.status_code == 204

    # Confirma que o evento foi removido do banco
    get_response = client.get(f"/api/acoes/{event_id}", headers=headers)
    assert get_response.status_code == 404


def test_delete_inexistente_retorna_404(client, app, base_data):
    """TESTE: DELETE com id inexistente retorna 404"""
    headers = _auth_headers(base_data["organizadora_id"], "organizadora")
    response = client.delete("/api/acoes/id-que-nao-existe", headers=headers)

    assert response.status_code == 404


def test_delete_proibido_para_nao_organizadora(client, app, base_data):
    """TESTE: DELETE por usuária que não é a organizadora retorna 403"""
    event_id = _create_event(app, base_data["organizadora_id"], base_data["category_id"])
    # Cria um segundo usuário que NÃO é o organizador do evento
    outra_user = User(
        phone="11999999999",
        full_name="Outra Usuária",
        neighborhood="Centro",
        role="participante",
    )
    db.session.add(outra_user)
    db.session.commit()
    outra_user_id = outra_user.id

    headers = _auth_headers(outra_user_id, "participante")
    response = client.delete(f"/api/acoes/{event_id}", headers=headers)

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# TESTES DE AUTORIZAÇÃO (require_minimum_role)
# ---------------------------------------------------------------------------

def test_create_acao_unauthenticated_returns_401(client, base_data):
    """POST sem token deve retornar 401"""
    payload = {
        "title": "Ação sem auth",
        "event_datetime": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "location_name": "Praça Central",
        "category_id": base_data["category_id"],
        "organizer_id": base_data["organizadora_id"],
    }
    response = client.post("/api/acoes", json=payload)
    assert response.status_code == 401
    assert "error" in response.get_json()


def test_create_acao_participante_returns_403(client, base_data):
    """Participante NÃO pode criar ação"""
    headers = _auth_headers(base_data["participante_id"], "participante")
    payload = {
        "title": "Ação de participante",
        "event_datetime": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "location_name": "Praça Central",
        "category_id": base_data["category_id"],
        "organizer_id": base_data["participante_id"],
    }
    response = client.post("/api/acoes", json=payload, headers=headers)
    assert response.status_code == 403
    assert response.get_json()["error"] == "forbidden"


def test_create_acao_organizadora_returns_201(client, base_data):
    """Organizadora pode criar ação"""
    headers = _auth_headers(base_data["organizadora_id"], "organizadora")
    payload = {
        "title": "Ação da organizadora",
        "event_datetime": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "location_name": "Praça Central",
        "category_id": base_data["category_id"],
        "organizer_id": base_data["organizadora_id"],
    }
    response = client.post("/api/acoes", json=payload, headers=headers)
    assert response.status_code == 201


def test_create_acao_coordenadora_returns_201(client, base_data):
    """Coordenadora pode criar ação (nível hierárquico superior)"""
    headers = _auth_headers(base_data["coordenadora_id"], "coordenadora")
    payload = {
        "title": "Ação da coordenadora",
        "event_datetime": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "location_name": "Praça Central",
        "category_id": base_data["category_id"],
        "organizer_id": base_data["coordenadora_id"],
    }
    response = client.post("/api/acoes", json=payload, headers=headers)
    assert response.status_code == 201


def test_patch_acao_organizadora_propria_returns_200(client, app, base_data):
    """Organizadora pode editar seu próprio evento"""
    event_id = _create_event(app, base_data["organizadora_id"], base_data["category_id"])
    headers = _auth_headers(base_data["organizadora_id"], "organizadora")
    response = client.patch(
        f"/api/acoes/{event_id}",
        json={"title": "Título alterado pela organizadora"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["title"] == "Título alterado pela organizadora"


def test_patch_acao_organizadora_outra_returns_403(client, app, base_data):
    """Organizadora NÃO pode editar evento de outra organizadora"""
    event_id = _create_event(app, base_data["organizadora_id"], base_data["category_id"])
    headers = _auth_headers(base_data["outra_organizadora_id"], "organizadora")
    response = client.patch(
        f"/api/acoes/{event_id}",
        json={"title": "Tentativa de edição"},
        headers=headers,
    )
    assert response.status_code == 403
    assert response.get_json()["error"] == "Sem permissão para editar esta ação"


def test_patch_acao_coordenadora_qualquer_returns_200(client, app, base_data):
    """Coordenadora pode editar evento de qualquer organizadora"""
    event_id = _create_event(app, base_data["organizadora_id"], base_data["category_id"])
    headers = _auth_headers(base_data["coordenadora_id"], "coordenadora")
    response = client.patch(
        f"/api/acoes/{event_id}",
        json={"title": "Editado pela coordenadora"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["title"] == "Editado pela coordenadora"


def test_patch_acao_participante_returns_403(client, app, base_data):
    """Participante não pode editar nenhum evento"""
    event_id = _create_event(app, base_data["organizadora_id"], base_data["category_id"])
    headers = _auth_headers(base_data["participante_id"], "participante")
    response = client.patch(
        f"/api/acoes/{event_id}",
        json={"title": "Tentativa"},
        headers=headers,
    )
    assert response.status_code == 403


def test_delete_acao_organizadora_propria_returns_204(client, app, base_data):
    """Organizadora pode deletar seu próprio evento"""
    event_id = _create_event(app, base_data["organizadora_id"], base_data["category_id"])
    headers = _auth_headers(base_data["organizadora_id"], "organizadora")
    response = client.delete(f"/api/acoes/{event_id}", headers=headers)
    assert response.status_code == 204


def test_delete_acao_organizadora_outra_returns_403(client, app, base_data):
    """Organizadora NÃO pode deletar evento de outra organizadora"""
    event_id = _create_event(app, base_data["organizadora_id"], base_data["category_id"])
    headers = _auth_headers(base_data["outra_organizadora_id"], "organizadora")
    response = client.delete(f"/api/acoes/{event_id}", headers=headers)
    assert response.status_code == 403
    assert response.get_json()["error"] == "Sem permissão para remover esta ação"


def test_delete_acao_coordenadora_qualquer_returns_204(client, app, base_data):
    """Coordenadora pode deletar evento de qualquer organizadora"""
    event_id = _create_event(app, base_data["organizadora_id"], base_data["category_id"])
    headers = _auth_headers(base_data["coordenadora_id"], "coordenadora")
    response = client.delete(f"/api/acoes/{event_id}", headers=headers)
    assert response.status_code == 204


def test_delete_acao_participante_returns_403(client, app, base_data):
    """Participante não pode deletar nenhum evento"""
    event_id = _create_event(app, base_data["organizadora_id"], base_data["category_id"])
    headers = _auth_headers(base_data["participante_id"], "participante")
    response = client.delete(f"/api/acoes/{event_id}", headers=headers)
    assert response.status_code == 403