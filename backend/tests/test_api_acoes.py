import os
import pytest
from datetime import datetime, timezone, timedelta
from maes_mobilizadoras.models import db, User, EventCategory, Event
import app as main_app


@pytest.fixture
def app():
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    app = main_app.create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TESTING"] = True

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


def test_create_acao_status_default_draft(client, base_data):
    """TESTE: status default deve ser draft"""
    payload = {
        "title": "Ação Comunitária",
        "event_datetime": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "location_name": "Praça Central",
        "category_id": base_data["category_id"],
        "organizer_id": base_data["organizer_id"],
    }

    response = client.post("/api/acoes", json=payload)

    assert response.status_code == 201
    assert response.get_json()["data"]["status"] == "draft"


def test_create_acao_no_title(client, base_data):
    """TESTE: sem título retorna 400 com erro no campo title"""
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
    assert "title" in data["errors"]


def test_create_acao_invalid_date(client, base_data):
    """TESTE: data inválida retorna 400 com erro no campo event_datetime"""
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
    assert "event_datetime" in data["errors"]


def test_create_acao_past_date(client, base_data):
    """TESTE: data no passado retorna 400"""
    payload = {
        "title": "Ação Comunitária",
        "event_datetime": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        "location_name": "Praça Central",
        "category_id": base_data["category_id"],
        "organizer_id": base_data["organizer_id"],
    }

    response = client.post("/api/acoes", json=payload)

    assert response.status_code == 400
    data = response.get_json()
    assert "errors" in data


def test_create_acao_invalid_status(client, base_data):
    """TESTE: status inválido retorna 400"""
    payload = {
        "title": "Ação Comunitária",
        "event_datetime": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "location_name": "Praça Central",
        "category_id": base_data["category_id"],
        "organizer_id": base_data["organizer_id"],
        "status": "invalido",
    }

    response = client.post("/api/acoes", json=payload)

    assert response.status_code == 400
    data = response.get_json()
    assert "errors" in data
    assert "status" in data["errors"]


def test_rate_limiting(client, base_data):
    """TESTE: 11ª requisição retorna 429"""
    payload = {
        "title": "Ação Comunitária",
        "event_datetime": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "location_name": "Praça Central",
        "category_id": base_data["category_id"],
        "organizer_id": base_data["organizer_id"],
    }

    for i in range(10):
        response = client.post("/api/acoes", json=payload)
        assert response.status_code == 201

    response_limited = client.post("/api/acoes", json=payload)
    assert response_limited.status_code == 429