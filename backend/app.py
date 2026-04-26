from flask import Flask, request, jsonify
from maes_mobilizadoras.models import db, Event
from maes_mobilizadoras.schemas import AcaoData, AcaoResponse, AcaoMetadata
from pathlib import Path
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pydantic import ValidationError

BASE_DIR = Path(__file__).parent


def create_app():
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(
        BASE_DIR / "maes_mobilizadoras.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://",
    )

    @app.route("/")
    def hello():
        return "Hello, <b>World!</b> - Mães Mobilizadoras"

    @app.route("/api/acoes", methods=["POST"])
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

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
else:
    app = create_app()
