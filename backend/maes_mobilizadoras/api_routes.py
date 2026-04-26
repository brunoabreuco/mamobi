from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from maes_mobilizadoras.limiter import limiter
from maes_mobilizadoras.models import Event, db
from maes_mobilizadoras.schemas import AcaoData, AcaoMetadata, AcaoResponse

api = Blueprint("api", __name__, url_prefix="/api")


@api.route("/acoes", methods=["POST"])
@limiter.limit("10 per minute")
def create_acao():
    try:
        req_data = request.get_json()
        if not req_data:
            return jsonify({"error": "No input data provided"}), 400

        acao_data = AcaoData(**req_data)
    except ValidationError as e:
        return jsonify({"errors": e.errors()}), 400

    new_event = Event(**acao_data.model_dump())

    db.session.add(new_event)
    db.session.commit()
    db.session.refresh(new_event)

    response_model = AcaoResponse(
        data=AcaoData.model_validate(new_event),
        metadata=AcaoMetadata.model_validate(new_event),
    )

    return jsonify(response_model.model_dump(mode="json")), 201
