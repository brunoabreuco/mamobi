from __future__ import annotations

import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import TYPE_CHECKING

import jwt as pyjwt
from flask import g, jsonify, request
from supabase import Client, create_client
from twilio.rest import Client as TwilioClient

from .models import db
from .models import AuthOTP, User

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_ACCESS_TOKEN_TTL = timedelta(hours=1)
_REFRESH_TOKEN_TTL = timedelta(days=30)
_OTP_TTL = timedelta(minutes=5)
_OTP_MAX_ATTEMPTS = 5
_OTP_COOLDOWN = timedelta(seconds=60)
_DEFAULT_ROLE = "participante"
_ALGORITHM = "HS256"

# ---------------------------------------------------------------------------
# Factories de cliente
# ---------------------------------------------------------------------------

_supabase_client: Client | None = None


def get_supabase() -> Client:
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_ROLE_KEY"],
        )
    return _supabase_client


def _get_twilio() -> TwilioClient:
    return TwilioClient(
        os.environ["TWILIO_ACCOUNT_SID"],
        os.environ["TWILIO_AUTH_TOKEN"],
    )


# ---------------------------------------------------------------------------
# JWT — emissão e validação
# ---------------------------------------------------------------------------

def _secret() -> str:
    try:
        from flask import current_app
        return current_app.config["SECRET_KEY"]
    except RuntimeError:
        # fora de app context (scripts avulsos)
        return os.environ["SECRET_KEY"]

def issue_tokens(user_id: str, role: str) -> dict:
    """Emite par access + refresh token para o usuário."""
    now = datetime.now(timezone.utc)
    access_payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + _ACCESS_TOKEN_TTL).timestamp()),
    }
    refresh_payload = {
        "sub": user_id,
        "type": "refresh",
        "jti": secrets.token_hex(16),
        "iat": int(now.timestamp()),
        "exp": int((now + _REFRESH_TOKEN_TTL).timestamp()),
    }
    secret = _secret()
    return {
        "access_token": pyjwt.encode(access_payload, secret, algorithm=_ALGORITHM),
        "refresh_token": pyjwt.encode(refresh_payload, secret, algorithm=_ALGORITHM),
        "token_type": "Bearer",
        "expires_in": int(_ACCESS_TOKEN_TTL.total_seconds()),
    }


def decode_token(token: str, expected_type: str = "access") -> dict:
    """
    Decodifica e valida JWT emitido por esta aplicação.
    Lança ValueError em caso de falha.
    """
    try:
        payload = pyjwt.decode(token, _secret(), algorithms=[_ALGORITHM])
    except pyjwt.ExpiredSignatureError:
        raise ValueError("token_expired")
    except pyjwt.InvalidTokenError:
        raise ValueError("invalid_token")

    if payload.get("type") != expected_type:
        raise ValueError("wrong_token_type")
    return payload


def verify_supabase_token(supabase_token: str) -> dict:
    """
    Valida JWT emitido pelo Supabase Auth (Google OAuth).
    Usado no endpoint de exchange.
    """
    secret = os.environ["SUPABASE_JWT_SECRET"]
    try:
        return pyjwt.decode(
            supabase_token,
            secret,
            algorithms=[_ALGORITHM],
            audience="authenticated",
        )
    except pyjwt.ExpiredSignatureError:
        raise ValueError("token_expired")
    except pyjwt.InvalidTokenError:
        raise ValueError("invalid_token")


# ---------------------------------------------------------------------------
# Decorators de autenticação e autorização
# ---------------------------------------------------------------------------

def _load_user_from_request() -> User:
    """
    Extrai Bearer token, valida e carrega User em g.current_user.
    Lança ValueError em qualquer falha.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise ValueError("missing_token")

    token = auth_header.split(" ", 1)[1]
    payload = decode_token(token, expected_type="access")

    user: User | None = db.session.get(User, payload["sub"])
    if user is None:
        raise ValueError("user_not_found")

    g.current_user = user
    g.current_user_id = str(user.id)
    g.token_payload = payload
    return user


def require_auth(f):
    """Rejeita requisições sem token válido com 401."""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            _load_user_from_request()
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 401
        return f(*args, **kwargs)
    return decorated


def require_role(role: str):
    """
    Exige autenticação válida E role específica.
    Retorna 401 se não autenticado, 403 se role insuficiente.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            try:
                _load_user_from_request()
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 401
            if g.current_user.role != role:
                return jsonify({"error": "forbidden"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


# ---------------------------------------------------------------------------
# Gerenciamento de perfil
# ---------------------------------------------------------------------------

def get_or_create_profile(
   user_id: str,
    *,
    phone: str | None = None,
    full_name: str | None = None,
    neighborhood: str = "",
) -> User:
    """
    Retorna o perfil existente ou cria um novo com role=participante.
    Chamado após qualquer fluxo de autenticação bem-sucedido.
    """
    user = db.session.get(User, user_id)
    if user is None:
        user = User(
            id=user_id,
            phone=phone,
            full_name=full_name or "",
            neighborhood=neighborhood,
            role=_DEFAULT_ROLE,
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
    return user


# ---------------------------------------------------------------------------
# Serviço OTP
# ---------------------------------------------------------------------------

def _generate_otp() -> str:
    """Gera código OTP de 6 dígitos criptograficamente seguro."""
    return str(secrets.randbelow(1_000_000)).zfill(6)


def request_otp(phone: str) -> None:
    """
    Gera OTP, persiste em auth_otp e envia via Twilio.
    Lança ValueError("rate_limited") se dentro do cooldown.
    """
    now = datetime.now(timezone.utc)
    cooldown_cutoff = now - _OTP_COOLDOWN

    recent_pending = (
        db.session.query(AuthOTP)
        .filter(
            AuthOTP.phone == phone,
            AuthOTP.used_at.is_(None),
            AuthOTP.created_at >= cooldown_cutoff,
        )
        .first()
    )
    if recent_pending is not None:
        raise ValueError("rate_limited")

    code = _generate_otp()
    otp = AuthOTP(
        id=str(uuid.uuid4()),
        phone=phone,
        code=code,
        expires_at=now + _OTP_TTL,
        attempts=0,
    )
    db.session.add(otp)
    db.session.commit()

    _get_twilio().messages.create(
        to=phone,
        from_=os.environ["TWILIO_PHONE_NUMBER"],
        body=(
            f"Mães Mobilizadoras: seu código de acesso é {code}. "
            f"Válido por 5 minutos. Não compartilhe."
        ),
    )


def verify_otp(phone: str, code: str) -> User:
    """
    Valida OTP contra auth_otp, cria/retorna perfil.
    Lança ValueError em caso de código inválido, expirado ou esgotado.
    """
    now = datetime.now(timezone.utc)

    otp: AuthOTP | None = (
        db.session.query(AuthOTP)
        .filter(
            AuthOTP.phone == phone,
            AuthOTP.used_at.is_(None),
            AuthOTP.expires_at > now,
        )
        .order_by(AuthOTP.created_at.desc())
        .first()
    )

    if otp is None:
        raise ValueError("invalid_otp")

    otp.attempts += 1
    if otp.attempts > _OTP_MAX_ATTEMPTS:
        db.session.commit()
        raise ValueError("too_many_attempts")

    if otp.code != code:
        db.session.commit()
        raise ValueError("invalid_otp")

    otp.used_at = now
    db.session.commit()

    existing = db.session.query(User).filter(User.phone == phone).first()
    if existing:
        return existing

    return get_or_create_profile(str(uuid.uuid4()), phone=phone)