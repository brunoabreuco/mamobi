from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from flask import Blueprint, jsonify

from maes_mobilizadoras.app_factory import create_app
from maes_mobilizadoras.models import AuthOTP, User, db

_TEST_ENV = {
    "SUPABASE_URL": "https://fake.supabase.co",
    "SUPABASE_SERVICE_ROLE_KEY": "fake-service-role-key",
    "SECRET_KEY": "test-secret-key-32chars-padding!!",
    "SUPABASE_JWT_SECRET": "fake-supabase-jwt-secret-paddin!!",
    "TWILIO_ACCOUNT_SID": "ACfakeaccountsid000000000000000000",
    "TWILIO_AUTH_TOKEN": "faketwilioauthtoken0000000000000",
    "TWILIO_PHONE_NUMBER": "+15550000000",
}

_TEST_APP_CONFIG = {
    "TESTING": True,
    "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    "SECRET_KEY": "test-secret-key-32chars-padding!!",
    "RATELIMIT_ENABLED": False,
}


def _register_test_routes(app) -> None:
    from maes_mobilizadoras.auth import require_auth, require_role

    bp = Blueprint("test_helpers", __name__)

    @bp.post("/test/organizadora-only")
    @require_role("organizadora")
    def _org_only():
        return jsonify({"ok": True})

    @bp.get("/test/auth-required")
    @require_auth
    def _auth_required():
        return jsonify({"ok": True})

    app.register_blueprint(bp)


@pytest.fixture(scope="function")
def app():
    with patch.dict(os.environ, _TEST_ENV):
        with patch("maes_mobilizadoras.app_factory.create_client") as mock_supabase:
            mock_supabase.return_value = MagicMock()
            application = create_app(test_config=_TEST_APP_CONFIG)

        _register_test_routes(application)

        with application.app_context():
            db.create_all()
            yield application        
            db.session.remove()
            db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def participante(app):
    with app.app_context():
        user = User(
            id=str(uuid.uuid4()),
            phone="+5511999990001",
            full_name="Participante Teste",
            neighborhood="Parelheiros",
            role="participante",
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


@pytest.fixture
def organizadora(app):
    with app.app_context():
        user = User(
            id=str(uuid.uuid4()),
            phone="+5511999990002",
            full_name="Organizadora Teste",
            neighborhood="Parelheiros",
            role="organizadora",
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


def make_otp(app, phone: str, code: str, expired: bool = False) -> AuthOTP:
    from maes_mobilizadoras.auth import _OTP_TTL

    delta = -timedelta(minutes=1) if expired else _OTP_TTL
    with app.app_context():
        otp = AuthOTP(
            id=str(uuid.uuid4()),
            phone=phone,
            code=code,
            expires_at=datetime.now(timezone.utc) + delta,
            attempts=0,
        )
        db.session.add(otp)
        db.session.commit()
        return otp