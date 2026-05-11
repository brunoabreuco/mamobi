from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest

from maes_mobilizadoras.auth import _OTP_TTL, issue_tokens
from maes_mobilizadoras.models import AuthOTP, User, db

from conftest import make_otp


def _auth_header(user: User) -> dict[str, str]:
    tokens = issue_tokens(str(user.id), user.role)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _expired_access_token(user_id: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now - timedelta(hours=1)).timestamp()),
    }
    return pyjwt.encode(payload, "test-secret-key-32chars-padding!!", algorithm="HS256")


# ---------------------------------------------------------------------------
# TDD-1: OTP inválido retorna 401
# ---------------------------------------------------------------------------

class TestOtpVerify:
    def test_otp_invalido_retorna_401(self, client, app):
        """Código errado deve retornar 401 com error=invalid_otp."""
        phone = "+5511900000001"
        make_otp(app, phone, "123456")

        resp = client.post("/auth/otp/verify", json={"phone": phone, "code": "000000"})

        assert resp.status_code == 401
        assert resp.get_json()["error"] == "invalid_otp"

    def test_otp_expirado_retorna_401(self, client, app):
        """OTP fora do prazo de validade deve retornar 401."""
        phone = "+5511900000002"
        make_otp(app, phone, "654321", expired=True)

        resp = client.post("/auth/otp/verify", json={"phone": phone, "code": "654321"})

        assert resp.status_code == 401
        assert resp.get_json()["error"] == "invalid_otp"

    def test_otp_ja_usado_retorna_401(self, client, app):
        """OTP já consumido não pode ser reutilizado."""
        phone = "+5511900000003"
        code = "555555"
        make_otp(app, phone, code)

        client.post("/auth/otp/verify", json={"phone": phone, "code": code})  # 1ª vez OK
        resp = client.post("/auth/otp/verify", json={"phone": phone, "code": code})

        assert resp.status_code == 401

    def test_otp_valido_retorna_200_com_tokens_e_perfil(self, client, app):
        """OTP correto deve retornar 200, tokens e criar perfil participante."""
        phone = "+5511900000004"
        make_otp(app, phone, "111111")

        resp = client.post("/auth/otp/verify", json={"phone": phone, "code": "111111"})

        assert resp.status_code == 200
        body = resp.get_json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["user"]["role"] == "participante"


# ---------------------------------------------------------------------------
# TDD-2: Token expirado retorna 401 em chamadas de API
# ---------------------------------------------------------------------------

class TestTokenExpiry:
    def test_token_expirado_retorna_401(self, client, participante):
        """Access token vencido deve ser rejeitado com 401."""
        token = _expired_access_token(str(participante.id), participante.role)

        resp = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 401
        assert resp.get_json()["error"] == "token_expired"

    def test_token_sem_bearer_retorna_401(self, client):
        resp = client.post("/auth/logout", headers={"Authorization": "token abc"})
        assert resp.status_code == 401

    def test_token_valido_aceito(self, client, participante):
        """Token válido deve ser aceito."""
        resp = client.post("/auth/logout", headers=_auth_header(participante))
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# TDD-3: Participante não acessa endpoints de organizadora → 403
# ---------------------------------------------------------------------------

class TestRoleEnforcement:
    def test_participante_bloqueado_em_endpoint_organizadora(self, client, participante):
        resp = client.post(
            "/test/organizadora-only",
            headers=_auth_header(participante),
        )
        assert resp.status_code == 403
        assert resp.get_json()["error"] == "forbidden"

    def test_organizadora_acessa_endpoint_organizadora(self, client, organizadora):
        resp = client.post(
            "/test/organizadora-only",
            headers=_auth_header(organizadora),
        )
        assert resp.status_code == 200

    def test_sem_token_retorna_401_nao_403(self, client):
        resp = client.post("/test/organizadora-only")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# TDD-4: Renovação de token funciona
# ---------------------------------------------------------------------------

class TestTokenRefresh:
    def test_refresh_retorna_novos_tokens(self, client, participante):
        tokens = issue_tokens(str(participante.id), participante.role)

        resp = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

        assert resp.status_code == 200
        body = resp.get_json()
        # Valida que novos tokens foram emitidos e são decodificáveis
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "Bearer"
        # Decodifica o novo access token para confirmar que é válido
        from maes_mobilizadoras.auth import decode_token
        payload = decode_token(body["access_token"], expected_type="access")
        assert payload["sub"] == str(participante.id)

    def test_access_token_nao_serve_como_refresh(self, client, participante):
        tokens = issue_tokens(str(participante.id), participante.role)

        resp = client.post("/auth/refresh", json={"refresh_token": tokens["access_token"]})

        assert resp.status_code == 401
        assert resp.get_json()["error"] == "wrong_token_type"

    def test_refresh_token_expirado_retorna_401(self, client, participante):
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(participante.id),
            "type": "refresh",
            "jti": "test-jti",
            "iat": int((now - timedelta(days=31)).timestamp()),
            "exp": int((now - timedelta(days=1)).timestamp()),
        }
        expired = pyjwt.encode(payload, "test-secret-key-32chars-padding!!", algorithm="HS256")

        resp = client.post("/auth/refresh", json={"refresh_token": expired})

        assert resp.status_code == 401
        assert resp.get_json()["error"] == "token_expired"


# ---------------------------------------------------------------------------
# Criação de perfil
# ---------------------------------------------------------------------------

class TestProfileCreation:
    def test_perfil_criado_com_role_participante_na_primeira_autenticacao(self, client, app):
        phone = "+5511900009999"
        make_otp(app, phone, "888888")

        client.post("/auth/otp/verify", json={"phone": phone, "code": "888888"})

        with app.app_context():
            user = db.session.query(User).filter_by(phone=phone).first()
            assert user is not None
            assert user.role == "participante"
            assert user.is_active is True

    def test_perfil_existente_nao_sobrescrito(self, client, app, participante):
        """Segundo login não deve alterar o perfil existente."""
        phone = participante.phone
        make_otp(app, phone, "999999")

        resp = client.post("/auth/otp/verify", json={"phone": phone, "code": "999999"})

        assert resp.status_code == 200
        with app.app_context():
            users = db.session.query(User).filter_by(phone=phone).all()
            assert len(users) == 1  # não duplicou


# ---------------------------------------------------------------------------
# OTP request / rate limit
# ---------------------------------------------------------------------------

class TestOtpRequest:
    @patch("maes_mobilizadoras.auth._get_twilio")
    def test_otp_request_chama_twilio(self, mock_twilio_factory, client):
        mock_twilio = MagicMock()
        mock_twilio_factory.return_value = mock_twilio

        resp = client.post("/auth/otp/request", json={"phone": "+5511911110001"})

        assert resp.status_code == 200
        mock_twilio.messages.create.assert_called_once()

    @patch("maes_mobilizadoras.auth._get_twilio")
    def test_rate_limit_bloqueia_segundo_request_imediato(self, mock_twilio_factory, client):
        mock_twilio_factory.return_value = MagicMock()
        phone = "+5511911110002"

        client.post("/auth/otp/request", json={"phone": phone})
        resp = client.post("/auth/otp/request", json={"phone": phone})

        assert resp.status_code == 429

    def test_phone_ausente_retorna_400(self, client):
        resp = client.post("/auth/otp/request", json={})
        assert resp.status_code == 400