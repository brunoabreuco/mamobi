from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, request, current_app
from pydantic import ValidationError
from sqlalchemy import or_

from mamobi.auth import require_role
from mamobi.models import RoleChange, User, db
from mamobi.schemas import RoleUpdateRequest, UserAdminResponse

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _pydantic_errors_to_dict(exc: ValidationError) -> dict:
    errors = {}
    for err in exc.errors():
        field = str(err["loc"][-1]) if err["loc"] else "geral"
        errors[field] = err["msg"]
    return errors


# =============================================================================
# LISTAGEM DE USUÁRIAS
# =============================================================================

@admin_bp.get("/users")
@require_role("coordenadora")
def list_users():
    """Lista todas as usuárias ativas com paginação e busca.

    Query params:
      page       int  (default 1)
      page_size  int  (default 20, max 100)
      role       str  filtra por role exata
      phone      str  busca por telefone exato (se fornecido)
      search     str  busca parcial em phone, full_name ou email
    """
    page = max(request.args.get("page", 1, type=int), 1)
    page_size = min(max(request.args.get("page_size", 20, type=int), 1), 100)
    role_filter = request.args.get("role")
    phone_exact = request.args.get("phone")
    search_term = request.args.get("search")

    query = db.session.query(User).filter(User.is_active.is_(True))

    if role_filter:
        query = query.filter(User.role == role_filter)

    if phone_exact:
        query = query.filter(User.phone == phone_exact)

    if search_term:
        search_pattern = f"%{search_term}%"
        query = query.filter(
            or_(
                User.phone.ilike(search_pattern),
                User.full_name.ilike(search_pattern),
                User.email.ilike(search_pattern),
            )
        )

    total = query.count()
    users = query.offset((page - 1) * page_size).limit(page_size).all()
    pages = -(-total // page_size) if total > 0 else 0

    items = [UserAdminResponse.model_validate(u).model_dump() for u in users]

    return jsonify({
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": pages,
        },
    }), 200


# =============================================================================
# ALTERAÇÃO DE ROLE
# =============================================================================

@admin_bp.patch("/users/<user_id>/role")
@require_role("coordenadora")
def update_user_role(user_id: str):
    """Promove ou rebaixa uma usuária. Registra auditoria em role_changes.

    Regras:
    - Apenas coordenadoras podem acessar este endpoint.
    - Coordenadora não pode alterar a própria role.
    - A nova role deve ser um valor válido: participante | organizadora | coordenadora.
    """
    if user_id == g.current_user_id:
        return jsonify({"error": "Coordenadora não pode alterar a própria role"}), 400

    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Body deve ser JSON válido"}), 400

    try:
        payload = RoleUpdateRequest(**body)
    except ValidationError as e:
        return jsonify({"errors": _pydantic_errors_to_dict(e)}), 400

    target = db.session.get(User, user_id)
    if target is None or not target.is_active:
        return jsonify({"error": "Usuária não encontrada"}), 404

    if target.role == payload.role:
        return jsonify({"error": "Usuária já possui esta role"}), 400

    old_role = target.role
    target.role = payload.role

    audit = RoleChange(
        user_id=user_id,
        changed_by=g.current_user_id,
        old_role=old_role,
        new_role=payload.role,
        changed_at=datetime.now(timezone.utc),
    )
    db.session.add(audit)

    try:
        db.session.commit()
        db.session.refresh(target)
    except Exception as e:
        current_app.logger.exception(e)
        db.session.rollback()
        return jsonify({"error": "Failed to reach database"}), 500

    return jsonify(UserAdminResponse.model_validate(target).model_dump()), 200