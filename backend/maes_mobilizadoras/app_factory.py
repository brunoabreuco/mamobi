from pathlib import Path
import os
import json

import firebase_admin
from firebase_admin import credentials
from dotenv import load_dotenv
from flask import Flask, Response
from supabase import create_client

from maes_mobilizadoras.models import db
from maes_mobilizadoras.limiter import limiter
from maes_mobilizadoras.notifications import FIREBASE_CONF

BASE_DIR = Path(__file__).parent.parent


def create_app(test_config: dict | None = None):
    load_dotenv()

    # Ativa modo debug do flask para ativar chave pública de testes
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app = Flask(
        __name__, static_folder=str(BASE_DIR.parent / "frontend"), static_url_path=""
    )
    app.config["DEBUG"] = debug_mode

    instance_path = Path(app.instance_path)
    instance_path.mkdir(exist_ok=True)
    db_path = instance_path / "app.db"

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", f"sqlite:///{db_path}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Usa a chave pública apenas no ambiente de testes.
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        if app.debug:
            secret = "dev-secret-key"
        else:
            raise RuntimeError("JWT_SECRET must be set in production")
    app.config["SECRET_KEY"] = secret

    if test_config is not None:
        app.config.from_mapping(test_config)

    db.init_app(app)
    limiter.init_app(app)

    # Guarda db.create_all() e seed_all() atrás de uma flag
    with app.app_context():
        if app.config.get("TESTING") or os.environ.get("AUTO_MIGRATE"):
            db.create_all()
            from maes_mobilizadoras.seed import seed_all

            seed_all()

    # Initialize Firebase
    if not firebase_admin._apps:
        service_account_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
        if service_account_json:
            try:
                cred = credentials.Certificate(json.loads(service_account_json))
                firebase_admin.initialize_app(cred)
            except Exception as e:
                app.logger.error(f"Failed to initialize Firebase with JSON: {e}")
        else:
            # Fallback to default credentials (e.g. GOOGLE_APPLICATION_CREDENTIALS env var)
            try:
                firebase_admin.initialize_app()
            except Exception as e:
                app.logger.warning(f"Firebase not initialized: {e}")

    # Supabase Client (Used for Auth only)
    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )
    app.extensions["supabase"] = supabase

    @app.get("/firebase-messaging-sw.js")
    def firebase_sw():
        content = (
            BASE_DIR.parent / "frontend" / "firebase-messaging-sw.js"
        ).read_text()
        content = content.replace("SERVER_SIDE_CONFIG", json.dumps(FIREBASE_CONF))
        return Response(content, mimetype="text/javascript")

    from maes_mobilizadoras.api_routes import api, auth_bp
    from maes_mobilizadoras.admin_routes import admin_bp

    app.register_blueprint(api)  # /api/*
    app.register_blueprint(auth_bp)  # /auth/*
    app.register_blueprint(admin_bp)  # /admin/*
    return app
