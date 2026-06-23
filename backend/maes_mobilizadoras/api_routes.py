from datetime import datetime, timezone
import hashlib
from flask import Blueprint, g, jsonify, request, current_app
from pydantic import ValidationError
import os
from datetime import datetime
from sqlalchemy.orm import joinedload

from maes_mobilizadoras.limiter import limiter
from maes_mobilizadoras.models import (
    Event,
    User,
    db,
    FCMToken,
    EventParticipation,
    Notification,
    NotificationRead,
    EventCategory,
)
from maes_mobilizadoras.schemas import (
    AcaoData,
    AcaoMetadata,
    AcaoPatchRequest,
    AcaoResponse,
    AcaoListItem,
    AcaoListResponse,
    ActiveFilters,
    CAMPOS_BLOQUEADOS_PATCH,
    FCMTokenRegister,
    PhoneConfirmRequest,
    UserResponse,
    UserUpdateRequest,
    CustomNotificationRequest,
    NotificationListItem,
    NotificationListResponse,
    CategoryListResponse,
    CategoryListItem,
)
from maes_mobilizadoras.auth import (
    decode_token,
    get_or_create_profile,
    issue_tokens,
    request_otp,
    require_auth,
    require_minimum_role,
    verify_otp,
    verify_supabase_token,
)
from maes_mobilizadoras.notifications import send_to_user, FIREBASE_CONF
from maes_mobilizadoras.acoes_filter import build_event_filters

api = Blueprint("api", __name__, url_prefix="/api")
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _pydantic_errors_to_dict(exc: ValidationError) -> dict:
    errors = {}
    for err in exc.errors():
        field = str(err["loc"][-1]) if err["loc"] else "geral"
        errors[field] = err["msg"]
    return errors


def _get_user_or_404(user_id: str):
    if not user_id:
        return None
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


# ---------------------------------------------------------------------------
# Helpers privados de acoes_filter
# ---------------------------------------------------------------------------


def _parse_date_param(value: str | None) -> datetime | None:
    """Converte string YYYY-MM-DD em datetime. Retorna None se vazio."""
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d")
    except ValueError:
        return None  # sinaliza erro para a rota tratar


def _event_to_dict(ev) -> dict:
    """Serializa um Event ORM (com category e organizer carregados) para dict."""
    return {
        "id": ev.id,
        "title": ev.title,
        "description": ev.description,
        "event_datetime": ev.event_datetime,
        "location_name": ev.location_name,
        "category_id": ev.category_id,
        "category_name": ev.category.name if ev.category else None,
        "organizer_id": ev.organizer_id,
        "organizer_name": ev.organizer.full_name if ev.organizer else None,
        "status": ev.status,
        "participant_count": ev.participant_count,
        "cover_image_url": ev.cover_image_url,
    }


# =============================================================================
# ENDPOINTS DE AÇÕES COMUNITÁRIAS
# =============================================================================


@api.route("/acoes", methods=["POST"])
@limiter.limit("10 per minute")
@require_minimum_role("organizadora")
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


@api.route("/acoes/<event_id>", methods=["GET"])
@require_auth
def get_acao(event_id):
    event = db.session.get(Event, event_id)
    if event is None:
        return jsonify({"error": "Ação não encontrada"}), 404

    response_model = AcaoResponse(
        data=AcaoData.model_validate(event),
        metadata=AcaoMetadata.model_validate(event),
    )
    return jsonify(response_model.model_dump(mode="json")), 200


@api.route("/acoes/<event_id>", methods=["PATCH"])
@require_minimum_role("organizadora")
def update_acao(event_id):
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Body deve ser JSON válido"}), 400

    # Verifica campos proibidos antes do Pydantic para retornar erro por campo.
    campos_proibidos = CAMPOS_BLOQUEADOS_PATCH & set(body.keys())
    if campos_proibidos:
        errors = {campo: "Campo não pode ser alterado" for campo in campos_proibidos}
        return jsonify({"errors": errors}), 400

    try:
        patch_data = AcaoPatchRequest(**body)
    except ValidationError as e:
        return jsonify({"errors": _pydantic_errors_to_dict(e)}), 400

    event = db.session.get(Event, event_id)
    if event is None:
        return jsonify({"error": "Ação não encontrada"}), 404

    if (
        g.current_user.role != "coordenadora"
        and event.organizer_id != g.current_user_id
    ):
        return jsonify({"error": "Sem permissão para editar esta ação"}), 403

    # exclude_unset=True garante que apenas os campos enviados na requisição
    # são aplicados; campos omitidos não sobrescrevem valores existentes.
    updates = patch_data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(event, field, value)

    try:
        db.session.commit()
        db.session.refresh(event)
    except Exception as e:
        current_app.logger.exception(e)
        db.session.rollback()
        return jsonify({"error": "Failed to reach database"}), 500

    response_model = AcaoResponse(
        data=AcaoData.model_validate(event),
        metadata=AcaoMetadata.model_validate(event),
    )
    return jsonify(response_model.model_dump(mode="json")), 200


@api.route("/acoes/<event_id>", methods=["DELETE"])
@require_minimum_role("organizadora")
def delete_acao(event_id):
    event = db.session.get(Event, event_id)
    if event is None:
        return jsonify({"error": "Ação não encontrada"}), 404

    if (
        g.current_user.role != "coordenadora"
        and event.organizer_id != g.current_user_id
    ):
        return jsonify({"error": "Sem permissão para remover esta ação"}), 403

    try:
        # 🔹 1. Busca todas as notificações associadas ao evento
        notifications = Notification.query.filter_by(event_id=event_id).all()
        for notif in notifications:
            # 🔹 2. Deleta os registros de leitura de cada notificação
            NotificationRead.query.filter_by(notification_id=notif.id).delete()
            # 🔹 3. Deleta a notificação
            db.session.delete(notif)

        # 🔹 4. Deleta as participações do evento
        EventParticipation.query.filter_by(event_id=event_id).delete()

        # 🔹 5. Deleta o evento
        db.session.delete(event)
        db.session.commit()

    except Exception as e:
        current_app.logger.exception(e)
        db.session.rollback()
        return jsonify({"error": "Falha ao deletar evento: " + str(e)}), 500

    return "", 204


@api.post("/acoes/<string:event_id>/participate")
@require_auth
def participate_event(event_id):
    # Faz TOGGLE no estado de participação do usuário no evento.
    user_id = g.current_user_id

    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({"error": "Ação não encontrada"}), 404

    # Check if user is already participating
    participation = EventParticipation.query.filter_by(
        event_id=event_id, user_id=user_id
    ).first()

    if participation:
        if participation.status == "confirmed":
            participation.status = "cancelled"
            participation.registered_at = datetime.now(timezone.utc)
        else:
            # If it was cancelled, re-confirm
            participation.status = "confirmed"
            participation.registered_at = datetime.now(timezone.utc)
    else:
        # Check if event is full
        if event.max_participants and event.participant_count >= event.max_participants:
            return jsonify(
                {"error": "Este evento já atingiu o limite de participantes"}
            ), 400

        # Create new participation
        participation = EventParticipation(
            event_id=event_id, user_id=user_id, status="confirmed"
        )
        db.session.add(participation)

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.exception(e)
        db.session.rollback()
        return jsonify({"error": "Falha ao registrar participação"}), 500

    return jsonify({"message": "Participação confirmada com sucesso"}), 201


@api.post("/acoes/<string:event_id>/notify")
@require_auth
@limiter.limit("10 per minute")
def notify_event_participants(event_id):
    req_data = request.get_json(silent=True)
    if not req_data:
        return jsonify({"error": "Body deve ser JSON válido"}), 400

    try:
        payload = CustomNotificationRequest(**req_data)
    except ValidationError as e:
        return jsonify({"errors": _pydantic_errors_to_dict(e)}), 400

    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({"error": "Evento não encontrado"}), 404

    # Verify that the current user is the event's organizer
    if event.organizer_id != g.current_user_id:
        return jsonify(
            {
                "error": "Acesso negado: apenas o organizador do evento pode enviar notificações"
            }
        ), 403

    # Fetch all participants of the event who are not cancelled
    participations = EventParticipation.query.filter(
        EventParticipation.event_id == event_id,
        EventParticipation.status != "cancelled",
    ).all()

    # Create the Notification record
    try:
        new_notification = Notification(
            event_id=event.id,
            sender_id=g.current_user_id,
            type="broadcast",
            title=payload.title,
            message=payload.message,
            target_role="participante",
            sent_at=datetime.now(timezone.utc),
        )
        db.session.add(new_notification)
        db.session.commit()
    except Exception as e:
        current_app.logger.exception(e)
        db.session.rollback()
        return jsonify({"error": "Falha ao registrar notificação"}), 500

    # Send push notifications using firebase messaging
    success_count = 0
    for participation in participations:
        success_count += send_to_user(
            user_id=participation.user_id,
            title=payload.title,
            body=payload.message,
            data={
                "event_id": str(event.id),
                "notification_id": str(new_notification.id),
            },
        )

    return jsonify(
        {
            "message": "Notificações enviadas com sucesso",
            "notification_id": str(new_notification.id),
            "recipients_count": len(participations),
            "successful_sends": success_count,
        }
    ), 201


# =============================================================================
# ENDPOINT DE PERFIL
# =============================================================================
@api.get("/me")
@require_auth
def get_me():
    user = _get_user_or_404(g.current_user_id)
    if not user:
        return jsonify({"error": "Usuária não encontrada"}), 404

    # Calculate counts
    created_count = Event.query.filter_by(organizer_id=user.id).count()
    participated_count = EventParticipation.query.filter_by(
        user_id=user.id, status="confirmed"
    ).count()

    response_data = UserResponse.model_validate(user).model_dump(mode="json")
    response_data["created_events_count"] = created_count
    response_data["participated_events_count"] = participated_count

    return jsonify(response_data), 200


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
        # Se o usuário NÃO possui telefone e POSSUI email (usuário Google),
        # salva o telefone diretamente, sem OTP (primeiro cadastro).
        if user.phone is None and user.email is not None:
            user.phone = payload.phone
            # Não define pending_phone, não envia OTP
        else:
            # Fluxo normal: troca de telefone (usuário já tem telefone)
            # ou usuário OTP (sempre tem telefone) – exige confirmação via OTP
            try:
                supabase = current_app.extensions["supabase"]
                supabase.auth.sign_in_with_otp({"phone": payload.phone})
            except Exception as e:
                current_app.logger.exception(e)
                return jsonify({"error": "Falha ao enviar OTP para o novo telefone"}), 502

            user.pending_phone = payload.phone
            phone_change_pending = True

    if payload.neighborhood is not None:
        user.neighborhood = payload.neighborhood

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.exception(e)
        db.session.rollback()
        return jsonify({"error": "Falha ao salvar alterações"}), 500

    status = 202 if phone_change_pending else 200
    return jsonify(
        {
            "profile": UserResponse.model_validate(user).model_dump(mode="json"),
            "phone_change_pending": phone_change_pending,
        }
    ), status


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
        supabase.auth.verify_otp(
            {
                "phone": user.pending_phone,
                "token": payload.token,
                "type": "sms",
            }
        )
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

    return jsonify(UserResponse.model_validate(user).model_dump(mode="json")), 200


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


@api.post("/me/fcm-token")
@require_auth
def register_fcm_token():
    body = request.get_json(silent=True) or {}
    try:
        payload = FCMTokenRegister(**body)
    except ValidationError as e:
        return jsonify({"errors": _pydantic_errors_to_dict(e)}), 400

    # Upsert token
    fcm_token = FCMToken.query.filter_by(token=payload.token).first()
    if fcm_token:
        fcm_token.user_id = g.current_user_id
        fcm_token.device_type = payload.device_type
        fcm_token.is_active = True
        fcm_token.last_used_at = db.func.now()
    else:
        fcm_token = FCMToken(
            user_id=g.current_user_id,
            token=payload.token,
            device_type=payload.device_type,
            last_used_at=db.func.now(),
        )
        db.session.add(fcm_token)

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.exception(e)
        db.session.rollback()
        return jsonify({"error": "token_save_failure"}), 500

    return jsonify({"message": "token_registered"}), 200


@api.get("/notifications")
@require_auth
def list_notifications():
    user_id = g.current_user_id
    user_role = g.current_user.role

    # Subquery for events the user is participating in
    participating_events_subquery = (
        db.select(EventParticipation.event_id).where(
            EventParticipation.user_id == user_id,
            EventParticipation.status != "cancelled",
        )
    ).scalar_subquery()

    # Query notifications
    # We join with NotificationRead to check if the notification has been read by the user
    query = (
        db.select(Notification, NotificationRead.id.is_not(None).label("is_read"))
        .outerjoin(
            NotificationRead,
            (NotificationRead.notification_id == Notification.id)
            & (NotificationRead.user_id == user_id),
        )
        .options(joinedload(Notification.event))
        .where(
            db.or_(
                # Event-specific notifications: user must be a participant or the sender
                db.and_(
                    Notification.event_id.is_not(None),
                    db.or_(
                        Notification.event_id.in_(participating_events_subquery),
                        Notification.sender_id == user_id,
                    ),
                ),
                # Global/Role notifications: no event_id, check role or if sender
                db.and_(
                    Notification.event_id.is_(None),
                    db.or_(
                        Notification.target_role == "all",
                        Notification.target_role == user_role,
                        Notification.target_role.is_(None),
                        Notification.sender_id == user_id,
                    ),
                ),
            )
        )
        .where(Notification.sent_at.is_not(None))
        .order_by(Notification.sent_at.desc())
    )

    try:
        results = db.session.execute(query).all()
    except Exception as e:
        current_app.logger.exception(e)
        return jsonify({"error": "Falha ao recuperar notificações"}), 500

    items = []
    for notification, is_read in results:
        item = NotificationListItem.model_validate(notification)
        item.is_read = is_read
        if notification.event:
            item.cover_image_url = notification.event.cover_image_url
        items.append(item)

    return jsonify(NotificationListResponse(data=items).model_dump(mode="json")), 200


@api.post("/notifications/<notification_id>/read")
@require_auth
def mark_notification_read(notification_id):
    user_id = g.current_user_id

    # Verify notification exists
    notification = db.session.get(Notification, notification_id)
    if not notification:
        return jsonify({"error": "Notificação não encontrada"}), 404

    # Check if already read
    existing = NotificationRead.query.filter_by(
        notification_id=notification_id, user_id=user_id
    ).first()

    if not existing:
        try:
            read_record = NotificationRead(
                notification_id=notification_id,
                user_id=user_id,
                read_at=datetime.now(timezone.utc),
            )
            db.session.add(read_record)
            db.session.commit()
        except Exception as e:
            current_app.logger.exception(e)
            db.session.rollback()
            return jsonify({"error": "Falha ao marcar como lida"}), 500

    return jsonify({"message": "Notificação marcada como lida"}), 200


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
    return jsonify(
        {
            **tokens,
            "user": {"id": str(user.id), "role": user.role},
        }
    ), 200


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
    email = payload.get("email") or None
    meta = payload.get("user_metadata") or {}
    full_name = meta.get("full_name") or meta.get("name") or ""

    user = get_or_create_profile(user_id, email=email, full_name=full_name)
    tokens = issue_tokens(str(user.id), user.role)
    return jsonify(
        {
            **tokens,
            "user": {"id": str(user.id), "role": user.role},
        }
    ), 200


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


# ---------------------------------------------------------------------------
# GET /api/acoes
# ---------------------------------------------------------------------------


@api.get("/categories")
def list_categories():
    categories = (
        db.session.execute(db.select(EventCategory).order_by(EventCategory.name))
        .scalars()
        .all()
    )

    data = [CategoryListItem.model_validate(c) for c in categories]
    return jsonify(CategoryListResponse(data=data).model_dump(mode="json")), 200


@api.route("/acoes", methods=["GET"])
def list_acoes():
    # --- parse e validacao dos query params ---
    q = request.args.get("q", "").strip() or None

    categoria_raw = request.args.get("categoria")
    categoria = None
    if categoria_raw:
        try:
            categoria = int(categoria_raw)
        except ValueError:
            return jsonify({"error": "categoria deve ser um numero inteiro"}), 400

    de_raw = request.args.get("de") or None
    ate_raw = request.args.get("ate") or None

    de = _parse_date_param(de_raw)
    ate = _parse_date_param(ate_raw)

    if de_raw and de is None:
        return jsonify({"error": "de deve estar no formato YYYY-MM-DD"}), 400
    if ate_raw and ate is None:
        return jsonify({"error": "ate deve estar no formato YYYY-MM-DD"}), 400

    responsavel = request.args.get("responsavel") or None

    # Parâmetro para filtrar apenas eventos em que o usuário participa
    participating_param = request.args.get("participating", "").lower()
    participating_only = participating_param in ("true", "1", "yes")

    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(100, max(1, int(request.args.get("per_page", 20))))
    except ValueError:
        return jsonify({"error": "page e per_page devem ser inteiros positivos"}), 400

    # --- query ---
    from sqlalchemy.orm import joinedload

    filters = build_event_filters(
        q=q,
        categoria=categoria,
        de=de,
        ate=ate,
        responsavel=responsavel,
    )

    # Obtém user_id do token
    user_id = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            from maes_mobilizadoras.auth import decode_token
            token = auth_header.split(" ", 1)[1]
            payload = decode_token(token)
            user_id = payload.get("sub")
        except Exception as e:
            current_app.logger.warning(f"Falha ao decodificar token: {e}")

    # Se for solicitado apenas eventos participados, exigimos autenticação
    if participating_only:
        if not user_id:
            return jsonify({"error": "Autenticação necessária para filtrar eventos participados"}), 401
        # Subconsulta para obter IDs dos eventos onde o usuário tem participação confirmada
        subquery = db.select(EventParticipation.event_id).where(
            EventParticipation.user_id == user_id,
            EventParticipation.status == "confirmed"
        ).scalar_subquery()
        filters.append(Event.id.in_(subquery))

    try:
        total = db.session.execute(
            db.select(db.func.count(Event.id)).where(*filters)
        ).scalar()

        events = (
            db.session.execute(
                db.select(Event)
                .where(*filters)
                .options(
                    joinedload(Event.category),
                    joinedload(Event.organizer),
                )
                .order_by(Event.event_datetime)
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
            .unique()
            .scalars()
            .all()
        )

    except Exception as e:
        current_app.logger.exception(e)
        return jsonify({"error": "Falha ao consultar acoes"}), 500

    # --- Verifica participação para cada evento (já existente) ---
    participating_ids = set()
    if user_id and events:
        event_ids = [ev.id for ev in events]
        participations = (
            db.session.execute(
                db.select(EventParticipation.event_id).where(
                    EventParticipation.user_id == user_id,
                    EventParticipation.event_id.in_(event_ids),
                    EventParticipation.status != "cancelled",
                )
            )
            .scalars()
            .all()
        )
        participating_ids = set(participations)

    items = []
    for ev in events:
        d = _event_to_dict(ev)
        d["is_participating"] = d["id"] in participating_ids
        items.append(AcaoListItem(**d))

    response = AcaoListResponse(
        data=items,
        total=total,
        page=page,
        per_page=per_page,
        filters=ActiveFilters(
            q=q,
            categoria=categoria,
            de=de_raw,
            ate=ate_raw,
            responsavel=responsavel,
        ),
    )

    return jsonify(response.model_dump(mode="json")), 200


# =============================================================================
# INJEÇÃO DO ENV NO FRONTEND
# =============================================================================
@api.get("/config")
def frontend_config():
    return jsonify(
        {
            "api_base": os.environ.get("API_BASE", ""),
            "firebase": FIREBASE_CONF,
            "supabase_url": os.environ.get("SUPABASE_URL", ""),
            "supabase_anon_key": os.environ.get("SUPABASE_ANON_KEY", ""),
        }
    )