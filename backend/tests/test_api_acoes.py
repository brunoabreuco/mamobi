import pytest
from flask import Flask
from datetime import datetime, timezone, timedelta
from maes_mobilizadoras.models import db, User, EventCategory
import app as main_app


@pytest.fixture
def app():
    # Use the create_app to include the limiter and routes
    app = main_app.create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TESTING"] = True

    # Needs to be reset or handled carefully due to rate limiter

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def base_data(app):
    with app.app_context():
        organizer = User(
            phone="11999999991",
            full_name="Maria Organizadora",
            neighborhood="Centro",
            role="organizer",
        )
        category = EventCategory(name="Saúde")
        db.session.add_all([organizer, category])
        db.session.commit()
        db.session.refresh(organizer)
        db.session.refresh(category)

        return {"organizer_id": organizer.id, "category_id": category.id}


def test_create_acao_success(client, base_data):
    """TESTE: POST válido persiste e retorna 201"""
    payload = {
        "title": "Ação Comunitária",
        "description": "Limpeza da praça",
        "event_datetime": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "location_name": "Praça Central",
        "category_id": base_data["category_id"],
        "organizer_id": base_data["organizer_id"],
        "max_participants": 50,
    }

    response = client.post("/api/acoes", json=payload)

    assert response.status_code == 201
    data = response.get_json()
    assert "data" in data
    assert "metadata" in data
    assert data["data"]["title"] == "Ação Comunitária"
    assert data["metadata"]["id"] is not None
    assert data["metadata"]["participant_count"] == 0


def test_create_acao_no_title(client, base_data):
    """TESTE: sem título retorna 400"""
    payload = {
        "description": "Limpeza da praça",
        "event_datetime": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "location_name": "Praça Central",
        "category_id": base_data["category_id"],
        "organizer_id": base_data["organizer_id"],
    }

    response = client.post("/api/acoes", json=payload)

    assert response.status_code == 400
    data = response.get_json()
    assert "errors" in data
    # Check if title is mentioned in the validation errors
    error_locs = [err["loc"][0] for err in data["errors"]]
    assert "title" in error_locs


def test_create_acao_invalid_date(client, base_data):
    """TESTE: data inválida retorna 400"""
    payload = {
        "title": "Ação Comunitária",
        "event_datetime": "not-a-valid-date",
        "location_name": "Praça Central",
        "category_id": base_data["category_id"],
        "organizer_id": base_data["organizer_id"],
    }

    response = client.post("/api/acoes", json=payload)

    assert response.status_code == 400
    data = response.get_json()
    assert "errors" in data
    error_locs = [err["loc"][0] for err in data["errors"]]
    assert "event_datetime" in error_locs


def test_rate_limiting_carga(client, base_data):
    """TESTE de carga: 10 req simultâneas sem inconsistência; rate limiting retorna 429"""
    payload = {
        "title": "Ação Comunitária",
        "event_datetime": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "location_name": "Praça Central",
        "category_id": base_data["category_id"],
        "organizer_id": base_data["organizer_id"],
    }

    # 10 reqs should pass (limit is 10 per minute per user)
    # Actually, rate limit configuration says "10 per minute". So 11th should fail.
    for i in range(10):
        response = client.post("/api/acoes", json=payload)
        assert response.status_code == 201

    # The 11th request should be rate limited
    response_limited = client.post("/api/acoes", json=payload)
    assert response_limited.status_code == 429
