from pathlib import Path

from flask import Flask

from maes_mobilizadoras.models import db
from maes_mobilizadoras.limiter import limiter

BASE_DIR = Path(__file__).parent.parent


def create_app():
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(
        BASE_DIR / "maes_mobilizadoras.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    limiter.init_app(app)

    with app.app_context():
        db.create_all()

    from maes_mobilizadoras.api_routes import api

    app.register_blueprint(api)

    return app
