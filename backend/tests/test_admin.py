"""
Testes para o blueprint /admin — gestão de roles.

Fixtures base (participante, organizadora, client, app) vêm do conftest.py.
A fixture coordenadora é local pois não existe no conftest.
"""
from __future__ import annotations

import uuid

import pytest

from mamobi.auth import issue_tokens
from mamobi.models import RoleChange, User, db


# ---------------------------------------------------------------------------
# Fixture local
# ---------------------------------------------------------------------------

@pytest.fixture
def coordenadora(app):
    with app.app_context():
        user = User(
            id=str(uuid.uuid4()),
            phone="+5511999990003",
            full_name="Coordenadora Teste",
            neighborhood="Parelheiros",
            role="coordenadora",
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def auth_header(user) -> dict:
    tokens = issue_tokens(str(user.id), user.role)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


# ---------------------------------------------------------------------------
# GET /admin/users
# ---------------------------------------------------------------------------

class TestListUsers:
    def test_coordenadora_recebe_200_com_paginacao(self, client, coordenadora):
        r = client.get("/admin/users", headers=auth_header(coordenadora))
        assert r.status_code == 200
        body = r.get_json()
        assert "items" in body
        assert "pagination" in body

    def test_organizadora_recebe_403(self, client, organizadora):
        r = client.get("/admin/users", headers=auth_header(organizadora))
        assert r.status_code == 403

    def test_participante_recebe_403(self, client, participante):
        r = client.get("/admin/users", headers=auth_header(participante))
        assert r.status_code == 403

    def test_sem_token_recebe_401(self, client):
        r = client.get("/admin/users")
        assert r.status_code == 401

    def test_filtro_por_role_retorna_apenas_role_solicitada(
        self, client, coordenadora, organizadora, participante
    ):
        r = client.get("/admin/users?role=organizadora", headers=auth_header(coordenadora))
        assert r.status_code == 200
        items = r.get_json()["items"]
        assert len(items) >= 1
        assert all(u["role"] == "organizadora" for u in items)

    def test_paginacao_respeita_page_size(self, client, app, coordenadora):
        # Cria 3 usuárias extras para garantir mais de 1 item
        with app.app_context():
            for i in range(3):
                u = User(
                    id=str(uuid.uuid4()),
                    phone=f"+551199988{i:04d}",
                    full_name=f"Extra {i}",
                    neighborhood="Centro",
                    role="participante",
                    is_active=True,
                )
                db.session.add(u)
            db.session.commit()

        r = client.get("/admin/users?page_size=2", headers=auth_header(coordenadora))
        assert r.status_code == 200
        body = r.get_json()
        assert len(body["items"]) <= 2
        assert body["pagination"]["page_size"] == 2


# ---------------------------------------------------------------------------
# PATCH /admin/users/<id>/role
# ---------------------------------------------------------------------------

class TestUpdateRole:

    # --- Controle de acesso ---

    def test_participante_recebe_403(self, client, participante, organizadora):
        r = client.patch(
            f"/admin/users/{organizadora.id}/role",
            json={"role": "coordenadora"},
            headers=auth_header(participante),
        )
        assert r.status_code == 403

    def test_organizadora_recebe_403(self, client, organizadora, participante):
        r = client.patch(
            f"/admin/users/{participante.id}/role",
            json={"role": "organizadora"},
            headers=auth_header(organizadora),
        )
        assert r.status_code == 403

    def test_sem_token_recebe_401(self, client, participante):
        r = client.patch(
            f"/admin/users/{participante.id}/role",
            json={"role": "organizadora"},
        )
        assert r.status_code == 401

    # --- Regras de negócio ---

    def test_auto_alteracao_retorna_400(self, client, coordenadora):
        r = client.patch(
            f"/admin/users/{coordenadora.id}/role",
            json={"role": "participante"},
            headers=auth_header(coordenadora),
        )
        assert r.status_code == 400
        assert "própria role" in r.get_json()["error"]

    def test_role_invalida_retorna_400(self, client, coordenadora, participante):
        r = client.patch(
            f"/admin/users/{participante.id}/role",
            json={"role": "superadmin"},
            headers=auth_header(coordenadora),
        )
        assert r.status_code == 400

    def test_role_identica_retorna_400(self, client, coordenadora, participante):
        r = client.patch(
            f"/admin/users/{participante.id}/role",
            json={"role": "participante"},
            headers=auth_header(coordenadora),
        )
        assert r.status_code == 400

    def test_usuario_inexistente_retorna_404(self, client, coordenadora):
        r = client.patch(
            f"/admin/users/{uuid.uuid4()}/role",
            json={"role": "organizadora"},
            headers=auth_header(coordenadora),
        )
        assert r.status_code == 404

    def test_body_ausente_retorna_400(self, client, coordenadora, participante):
        r = client.patch(
            f"/admin/users/{participante.id}/role",
            headers=auth_header(coordenadora),
        )
        assert r.status_code == 400

    # --- Promoções e rebaixamentos ---

    def test_coordenadora_promove_participante_para_organizadora(
        self, client, app, coordenadora, participante
    ):
        r = client.patch(
            f"/admin/users/{participante.id}/role",
            json={"role": "organizadora"},
            headers=auth_header(coordenadora),
        )
        assert r.status_code == 200
        assert r.get_json()["role"] == "organizadora"

        with app.app_context():
            user = db.session.get(User, participante.id)
            assert user.role == "organizadora"

    def test_coordenadora_promove_participante_para_coordenadora(
        self, client, app, coordenadora, participante
    ):
        r = client.patch(
            f"/admin/users/{participante.id}/role",
            json={"role": "coordenadora"},
            headers=auth_header(coordenadora),
        )
        assert r.status_code == 200
        assert r.get_json()["role"] == "coordenadora"

    def test_coordenadora_rebaixa_organizadora(
        self, client, app, coordenadora, organizadora
    ):
        r = client.patch(
            f"/admin/users/{organizadora.id}/role",
            json={"role": "participante"},
            headers=auth_header(coordenadora),
        )
        assert r.status_code == 200
        assert r.get_json()["role"] == "participante"

        with app.app_context():
            user = db.session.get(User, organizadora.id)
            assert user.role == "participante"

    def test_coordenadora_rebaixa_outra_coordenadora(
        self, client, app, coordenadora
    ):
        with app.app_context():
            outra = User(
                id=str(uuid.uuid4()),
                phone="+5511999990099",
                full_name="Outra Coordenadora",
                neighborhood="Centro",
                role="coordenadora",
                is_active=True,
            )
            db.session.add(outra)
            db.session.commit()
            outra_id = outra.id

        r = client.patch(
            f"/admin/users/{outra_id}/role",
            json={"role": "organizadora"},
            headers=auth_header(coordenadora),
        )
        assert r.status_code == 200
        assert r.get_json()["role"] == "organizadora"

    # --- Auditoria ---

    def test_auditoria_criada_com_dados_corretos(
        self, client, app, coordenadora, participante
    ):
        client.patch(
            f"/admin/users/{participante.id}/role",
            json={"role": "organizadora"},
            headers=auth_header(coordenadora),
        )

        with app.app_context():
            audit = (
                db.session.query(RoleChange)
                .filter_by(user_id=participante.id)
                .first()
            )
            assert audit is not None
            assert audit.changed_by == coordenadora.id
            assert audit.old_role == "participante"
            assert audit.new_role == "organizadora"
            assert audit.changed_at is not None

    def test_auditoria_nao_criada_quando_operacao_falha(
        self, client, app, coordenadora
    ):
        """Garante atomicidade: sem alteração, sem registro de auditoria."""
        id_inexistente = str(uuid.uuid4())
        client.patch(
            f"/admin/users/{id_inexistente}/role",
            json={"role": "organizadora"},
            headers=auth_header(coordenadora),
        )

        with app.app_context():
            count = (
                db.session.query(RoleChange)
                .filter_by(user_id=id_inexistente)
                .count()
            )
            assert count == 0

    # --- Reflexo imediato sem novo login ---

    def test_nova_role_reflete_em_chamadas_subsequentes_sem_novo_login(
        self, client, app, coordenadora, participante
    ):
        """
        Token emitido ANTES da promoção (com role='participante') ainda é válido.
        /api/me deve retornar a nova role lida do banco, não a do payload do JWT.
        """
        token_antigo = issue_tokens(str(participante.id), "participante")["access_token"]

        client.patch(
            f"/admin/users/{participante.id}/role",
            json={"role": "organizadora"},
            headers=auth_header(coordenadora),
        )

        r = client.get(
            "/api/me",
            headers={"Authorization": f"Bearer {token_antigo}"},
        )
        assert r.status_code == 200
        assert r.get_json()["role"] == "organizadora"