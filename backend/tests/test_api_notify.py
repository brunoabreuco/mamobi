import pytest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from maes_mobilizadoras.models import User, EventCategory, Event, EventParticipation, Notification, FCMToken, db
from maes_mobilizadoras.auth import issue_tokens

def _create_user(app, **kwargs) -> User:
    defaults = {
        "phone": "+5511999990000",
        "full_name": "User Test",
        "neighborhood": "Centro",
        "role": "participante",
        "is_active": True,
    }
    defaults.update(kwargs)
    with app.app_context():
        user = User(**defaults)
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user

def _auth_header(app, user: User) -> dict:
    with app.app_context():
        tokens = issue_tokens(str(user.id), user.role)
    return {"Authorization": f"Bearer {tokens['access_token']}"}

@pytest.fixture
def mock_messaging():
    from firebase_admin import messaging
    with patch('maes_mobilizadoras.notifications.messaging') as mock:
        mock.UnregisteredError = messaging.UnregisteredError
        yield mock

def test_notify_unauthenticated(client):
    response = client.post("/api/acoes/some-uuid/notify", json={"title": "Hello", "message": "World"})
    assert response.status_code == 401

def test_notify_event_not_found(client, app):
    organizer = _create_user(app, phone="+5511999991111", role="organizer")
    headers = _auth_header(app, organizer)
    
    response = client.post(
        "/api/acoes/00000000-0000-0000-0000-000000000000/notify",
        json={"title": "Hello", "message": "World"},
        headers=headers
    )
    assert response.status_code == 404
    assert response.json["error"] == "Evento não encontrado"

def test_notify_not_organizer(client, app):
    organizer = _create_user(app, phone="+5511999991111", role="organizer")
    other_user = _create_user(app, phone="+5511999992222", role="organizer")
    
    with app.app_context():
        category = EventCategory(name="Educação")
        db.session.add(category)
        db.session.commit()
        db.session.refresh(category)
        
        event = Event(
            title="Ação Organizada",
            event_datetime=datetime.now(timezone.utc) + timedelta(days=2),
            location_name="Escola",
            category_id=category.id,
            organizer_id=organizer.id,
            status="active",
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id

    headers = _auth_header(app, other_user)
    response = client.post(
        f"/api/acoes/{event_id}/notify",
        json={"title": "Hello", "message": "World"},
        headers=headers
    )
    assert response.status_code == 403
    assert "Acesso negado" in response.json["error"]

def test_notify_invalid_payload(client, app):
    organizer = _create_user(app, phone="+5511999991111", role="organizer")
    
    with app.app_context():
        category = EventCategory(name="Saúde")
        db.session.add(category)
        db.session.commit()
        db.session.refresh(category)
        
        event = Event(
            title="Ação Organizada",
            event_datetime=datetime.now(timezone.utc) + timedelta(days=2),
            location_name="Escola",
            category_id=category.id,
            organizer_id=organizer.id,
            status="active",
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id

    headers = _auth_header(app, organizer)
    
    # Missing title
    response = client.post(
        f"/api/acoes/{event_id}/notify",
        json={"message": "World"},
        headers=headers
    )
    assert response.status_code == 400
    assert "title" in response.json["errors"]

    # Title empty
    response = client.post(
        f"/api/acoes/{event_id}/notify",
        json={"title": "", "message": "World"},
        headers=headers
    )
    assert response.status_code == 400

    # Message too long
    response = client.post(
        f"/api/acoes/{event_id}/notify",
        json={"title": "Hello", "message": "a" * 301},
        headers=headers
    )
    assert response.status_code == 400
    assert "message" in response.json["errors"]

def test_notify_success(client, app, mock_messaging):
    mock_messaging.send.return_value = "msg_id_123"
    
    organizer = _create_user(app, phone="+5511999991111", role="organizer")
    participant1 = _create_user(app, phone="+5511999993333", role="participante")
    participant2 = _create_user(app, phone="+5511999994444", role="participante")
    participant_cancelled = _create_user(app, phone="+5511999995555", role="participante")
    
    with app.app_context():
        category = EventCategory(name="Saúde")
        db.session.add(category)
        db.session.commit()
        db.session.refresh(category)
        
        event = Event(
            title="Ação Organizada",
            event_datetime=datetime.now(timezone.utc) + timedelta(days=2),
            location_name="Escola",
            category_id=category.id,
            organizer_id=organizer.id,
            status="active",
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id
        
        # Add FCM tokens for participants
        token1 = FCMToken(user_id=participant1.id, token="token-p1", is_active=True)
        token2 = FCMToken(user_id=participant2.id, token="token-p2", is_active=True)
        token_cancelled = FCMToken(user_id=participant_cancelled.id, token="token-pc", is_active=True)
        db.session.add_all([token1, token2, token_cancelled])
        
        # Add event participations
        p1 = EventParticipation(event_id=event_id, user_id=participant1.id, status="confirmed")
        p2 = EventParticipation(event_id=event_id, user_id=participant2.id, status="registered")
        p_cancelled = EventParticipation(event_id=event_id, user_id=participant_cancelled.id, status="cancelled")
        db.session.add_all([p1, p2, p_cancelled])
        
        db.session.commit()

    headers = _auth_header(app, organizer)
    response = client.post(
        f"/api/acoes/{event_id}/notify",
        json={"title": "Alerta Urgente", "message": "Por favor cheguem 10 minutos mais cedo!"},
        headers=headers
    )
    
    assert response.status_code == 201
    res_data = response.json
    assert res_data["message"] == "Notificações enviadas com sucesso"
    assert "notification_id" in res_data
    assert res_data["recipients_count"] == 2
    assert res_data["successful_sends"] == 2
    
    # Check messaging mocks were called twice
    assert mock_messaging.send.call_count == 2
    
    # Check Notification was saved in DB
    with app.app_context():
        notif = db.session.get(Notification, res_data["notification_id"])
        assert notif is not None
        assert notif.event_id == event_id
        assert notif.sender_id == organizer.id
        assert notif.title == "Alerta Urgente"
        assert notif.message == "Por favor cheguem 10 minutos mais cedo!"
        assert notif.type == "broadcast"
        assert notif.target_role == "participante"


def test_notify_no_participants(client, app, mock_messaging):
    organizer = _create_user(app, phone="+5511999991111", role="organizer")
    
    with app.app_context():
        category = EventCategory(name="Saúde")
        db.session.add(category)
        db.session.commit()
        db.session.refresh(category)
        
        event = Event(
            title="Ação Organizada",
            event_datetime=datetime.now(timezone.utc) + timedelta(days=2),
            location_name="Escola",
            category_id=category.id,
            organizer_id=organizer.id,
            status="active",
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id

    headers = _auth_header(app, organizer)
    response = client.post(
        f"/api/acoes/{event_id}/notify",
        json={"title": "Olá", "message": "Sem participantes ainda"},
        headers=headers
    )
    
    assert response.status_code == 201
    assert response.json["recipients_count"] == 0
    assert response.json["successful_sends"] == 0
    assert mock_messaging.send.call_count == 0


def test_notify_with_some_unregistered_tokens(client, app, mock_messaging):
    from firebase_admin import messaging
    from unittest.mock import MagicMock
    
    def mock_message_init(*args, **kwargs):
        m = MagicMock()
        for k, v in kwargs.items():
            setattr(m, k, v)
        return m
    mock_messaging.Message.side_effect = mock_message_init
    
    def mock_send(message):
        if getattr(message, "token", None) == "bad-token":
            raise messaging.UnregisteredError("Unregistered token")
        return "success-id"
        
    mock_messaging.send.side_effect = mock_send
    
    organizer = _create_user(app, phone="+5511999991111", role="organizer")
    p_bad = _create_user(app, phone="+5511999993333", role="participante")
    p_good = _create_user(app, phone="+5511999994444", role="participante")
    
    with app.app_context():
        category = EventCategory(name="Saúde")
        db.session.add(category)
        db.session.commit()
        db.session.refresh(category)
        
        event = Event(
            title="Ação Organizada",
            event_datetime=datetime.now(timezone.utc) + timedelta(days=2),
            location_name="Escola",
            category_id=category.id,
            organizer_id=organizer.id,
            status="active",
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id
        
        token_bad = FCMToken(user_id=p_bad.id, token="bad-token", is_active=True)
        token_good = FCMToken(user_id=p_good.id, token="good-token", is_active=True)
        db.session.add_all([token_bad, token_good])
        
        db.session.add_all([
            EventParticipation(event_id=event_id, user_id=p_bad.id, status="confirmed"),
            EventParticipation(event_id=event_id, user_id=p_good.id, status="confirmed")
        ])
        db.session.commit()

    headers = _auth_header(app, organizer)
    response = client.post(
        f"/api/acoes/{event_id}/notify",
        json={"title": "Atenção", "message": "Algum problema com token"},
        headers=headers
    )
    
    assert response.status_code == 201
    assert response.json["recipients_count"] == 2
    assert response.json["successful_sends"] == 1  # Only p_good is successful
    
    # Check that the bad token is now marked as inactive in database
    with app.app_context():
        t_bad = db.session.get(FCMToken, (p_bad.id, "bad-token"))
        assert t_bad.is_active is False
        
        t_good = db.session.get(FCMToken, (p_good.id, "good-token"))
        assert t_good.is_active is True


def test_notify_db_failure(client, app, mock_messaging):
    organizer = _create_user(app, phone="+5511999991111", role="organizer")
    
    with app.app_context():
        category = EventCategory(name="Saúde")
        db.session.add(category)
        db.session.commit()
        db.session.refresh(category)
        
        event = Event(
            title="Ação Organizada",
            event_datetime=datetime.now(timezone.utc) + timedelta(days=2),
            location_name="Escola",
            category_id=category.id,
            organizer_id=organizer.id,
            status="active",
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id

    headers = _auth_header(app, organizer)
    
    with patch("maes_mobilizadoras.models.db.session.commit", side_effect=Exception("Database error")):
        response = client.post(
            f"/api/acoes/{event_id}/notify",
            json={"title": "Erro", "message": "Falha de DB"},
            headers=headers
        )
        assert response.status_code == 500
        assert response.json["error"] == "Falha ao registrar notificação"
        
    assert mock_messaging.send.call_count == 0
