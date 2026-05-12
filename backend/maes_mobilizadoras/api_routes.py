from flask import Blueprint, jsonify, request, current_app
from pydantic import ValidationError

from maes_mobilizadoras.limiter import limiter
from maes_mobilizadoras.models import Event, db
from maes_mobilizadoras.schemas import AcaoData, AcaoMetadata, AcaoResponse

api = Blueprint("api", __name__, url_prefix="/api")


def _pydantic_errors_to_dict(exc: ValidationError) -> dict:
    errors = {}
    for err in exc.errors():
        field = str(err["loc"][-1]) if err["loc"] else "geral"
        errors[field] = err["msg"]
    return errors


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