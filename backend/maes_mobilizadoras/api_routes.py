import hashlib
from flask import Blueprint, g, jsonify, request, current_app
from pydantic import ValidationError

from maes_mobilizadoras.limiter import limiter
from maes_mobilizadoras.models import Event, User, db
from maes_mobilizadoras.schemas import (
    AcaoData,
    AcaoMetadata,
    AcaoResponse,
    PhoneConfirmRequest,
    UserResponse,
    UserUpdateRequest,
)
from maes_mobilizadoras.auth import (
    decode_token,
    get_or_create_profile,
    issue_tokens,
    request_otp,
    require_auth,
    verify_otp,
    verify_supabase_token,
)

api = Blueprint("api", __name__, url_prefix="/api")
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _pydantic_errors_to_dict(exc: ValidationError) -> dict:
    errors = {}
    for err in exc.errors():
        field = str(err["loc"][-1]) if err["loc"] else "geral"
        errors[field] = err["msg"]
    return errors

def _get_user_or_404(user_id: str):
    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        return None
    return user

def _anonymize(user: User) -> None:
    """Substitui dados pessoais por valores anonimos. phone e full_name sao NOT NULL."""
    user.full_name = "Removido"
    user.neighborhood = user.neighborhood or "Removido"
    user.avatar_url = None
    user.pending_phone = None
    # Hash do telefone garante unicidade sem expor o original (cabe em varchar(20))
    user.phone = "del_" + hashlib.sha256(user.phone.encode()).hexdigest()[:15]
    user.is_active = False


# =============================================================================
# ENDPOINT DE AÇÕES COMUNITÁRIAS
# =============================================================================

@api.route("/acoes", methods=["POST"])
@limiter.limit("10 per minute")
def create_acao():
    req_data = request.get_json(silent=True)
    if not req_data:
        return jsonify({"error": "Body deve ser JSON válido"}), 400

    try:
        acao_data = AcaoData(**req_data)
    except ValidationError as e:
        current_app.logger.exception(e)
        return jsonify({"errors": _pydantic_errors_to_dict(e)}), 400

    try:
        new_event = Event(**acao_data.model_dump())
        db.session.add(new_event)
        db.session.commit()
        db.session.refresh(new_event)
    except Exception as e:
        current_app.logger.exception(e)
        db.session.rollback()
        return jsonify({"error": "Failed to reach database"}), 500

    response_model = AcaoResponse(
        data=AcaoData.model_validate(new_event),
        metadata=AcaoMetadata.model_validate(new_event),
    )

    return jsonify(response_model.model_dump(mode="json")), 201

# =============================================================================
# ENDPOINT DE PERFIL
# =============================================================================
@api.get("/me")
@require_auth
def get_me():
    user = _get_user_or_404(g.current_user_id)
    if not user:
        return jsonify({"error": "Usuária não encontrada"}), 404
    return jsonify(UserResponse.model_validate(user).model_dump()), 200


@api.patch("/me")
@require_auth
def update_me():
    body = request.get_json(silent=True) or {}
    if not body:
        return jsonify({"error": "Body deve ser JSON válido"}), 400

    try:
        payload = UserUpdateRequest(**body)
    except ValidationError as e:
        return jsonify({"errors": _pydantic_errors_to_dict(e)}), 400

    user = _get_user_or_404(g.current_user_id)
    if not user:
        return jsonify({"error": "Usuária não encontrada"}), 404

    phone_change_pending = False

    if payload.full_name is not None:
        user.full_name = payload.full_name

    if payload.avatar_url is not None:
        user.avatar_url = payload.avatar_url

    if payload.phone is not None and payload.phone != user.phone:
        try:
            supabase = current_app.extensions["supabase"]
            supabase.auth.sign_in_with_otp({"phone": payload.phone})
        except Exception as e:
            current_app.logger.exception(e)
            return jsonify({"error": "Falha ao enviar OTP para o novo telefone"}), 502

        user.pending_phone = payload.phone
        phone_change_pending = True

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.exception(e)
        db.session.rollback()
        return jsonify({"error": "Falha ao salvar alterações"}), 500

    status = 202 if phone_change_pending else 200
    return jsonify({
        "profile": UserResponse.model_validate(user).model_dump(),
        "phone_change_pending": phone_change_pending,
    }), status


@api.post("/me/phone/confirm")
@require_auth
def confirm_phone():
    body = request.get_json(silent=True) or {}

    try:
        payload = PhoneConfirmRequest(**body)
    except ValidationError as e:
        return jsonify({"errors": _pydantic_errors_to_dict(e)}), 400

    user = _get_user_or_404(g.current_user_id)
    if not user:
        return jsonify({"error": "Usuária não encontrada"}), 404

    if not user.pending_phone:
        return jsonify({"error": "Nenhuma troca de telefone pendente"}), 400

    try:
        supabase = current_app.extensions["supabase"]
        supabase.auth.verify_otp({
            "phone": user.pending_phone,
            "token": payload.token,
            "type": "sms",
        })
    except Exception:
        return jsonify({"error": "OTP inválido ou expirado"}), 401

    user.phone = user.pending_phone
    user.pending_phone = None

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.exception(e)
        db.session.rollback()
        return jsonify({"error": "Falha ao salvar novo telefone"}), 500

    return jsonify(UserResponse.model_validate(user).model_dump()), 200


@api.delete("/me")
@require_auth
def delete_me():
    user = _get_user_or_404(g.current_user_id)
    if not user:
        return jsonify({"error": "Usuária não encontrada"}), 404

    _anonymize(user)

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.exception(e)
        db.session.rollback()
        return jsonify({"error": "Falha ao processar exclusão"}), 500

    # Remove do Supabase Auth -- impede qualquer login futuro
    try:
        supabase = current_app.extensions["supabase"]
        supabase.auth.admin.delete_user(g.current_user_id)
    except Exception as e:
        # Nao reverte: dados ja foram anonimizados localmente
        current_app.logger.exception(e)

    return "", 204

# =============================================================================
# ENDPOINT DE AUTENTICAÇÃO OTP E GOOGLE
# =============================================================================

@auth_bp.post("/otp/request")
def otp_request():
    data = request.get_json(silent=True) or {}
    phone = str(data.get("phone", "")).strip()
    if not phone:
        return jsonify({"error": "phone_required"}), 400

    try:
        request_otp(phone)
    except ValueError as exc:
        status = 429 if str(exc) == "rate_limited" else 400
        return jsonify({"error": str(exc)}), status

    return jsonify({"message": "otp_sent"}), 200


@auth_bp.post("/otp/verify")
def otp_verify():
    data = request.get_json(silent=True) or {}
    phone = str(data.get("phone", "")).strip()
    code = str(data.get("code", "")).strip()

    if not phone or not code:
        return jsonify({"error": "phone_and_code_required"}), 400

    try:
        user = verify_otp(phone, code)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 401

    tokens = issue_tokens(str(user.id), user.role)
    return jsonify({
        **tokens,
        "user": {"id": str(user.id), "role": user.role},
    }), 200


@auth_bp.post("/google/exchange")
def google_exchange():
    """
    Recebe o access_token do Supabase Auth (pós-Google OAuth no cliente),
    valida, cria perfil se necessário, devolve tokens da aplicação.
    """
    data = request.get_json(silent=True) or {}
    supabase_token = str(data.get("supabase_token", "")).strip()
    if not supabase_token:
        return jsonify({"error": "supabase_token_required"}), 400

    try:
        payload = verify_supabase_token(supabase_token)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 401

    user_id = payload["sub"]
    meta = payload.get("user_metadata") or {}
    full_name = meta.get("full_name") or meta.get("name") or ""

    user = get_or_create_profile(user_id, full_name=full_name)
    tokens = issue_tokens(str(user.id), user.role)
    return jsonify({
        **tokens,
        "user": {"id": str(user.id), "role": user.role},
    }), 200


@auth_bp.post("/refresh")
def token_refresh():
    data = request.get_json(silent=True) or {}
    refresh_token = str(data.get("refresh_token", "")).strip()
    if not refresh_token:
        return jsonify({"error": "refresh_token_required"}), 400

    try:
        payload = decode_token(refresh_token, expected_type="refresh")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 401

    user = db.session.get(User, payload["sub"])
    if user is None or not user.is_active:
        return jsonify({"error": "user_not_found"}), 401

    tokens = issue_tokens(str(user.id), user.role)
    return jsonify(tokens), 200


@auth_bp.post("/logout")
@require_auth
def logout():
    # JWT stateless: logout é do lado do cliente (descarte do token).
    # Revogação server-side (denylist) fica fora do escopo desta task.
    return jsonify({"message": "logged_out"}), 200