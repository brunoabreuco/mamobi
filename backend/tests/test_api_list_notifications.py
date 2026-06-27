import pytest
from datetime import datetime, timezone, timedelta
from mamobi.models import User, EventCategory, Event, EventParticipation, Notification, NotificationRead, db
from mamobi.auth import issue_tokens

def _create_user(app, **kwargs) -> User:
    defaults = {
        "phone": f"+55119{datetime.now().microsecond:06d}",
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

def test_list_notifications_unauthenticated(client):
    response = client.get("/api/notifications")
    assert response.status_code == 401

def test_list_notifications_empty(client, app):
    user = _create_user(app)
    headers = _auth_header(app, user)
    
    response = client.get("/api/notifications", headers=headers)
    assert response.status_code == 200
    assert response.json["data"] == []

def test_list_notifications_filtering(client, app):
    user = _create_user(app, phone="+5511911111111", role="participante")
    other_user = _create_user(app, phone="+5511922222222", role="organizadora")
    
    with app.app_context():
        category = EventCategory(name="Saúde")
        db.session.add(category)
        db.session.commit()
        db.session.refresh(category)
        
        event = Event(
            title="Ação Comunitária",
            event_datetime=datetime.now(timezone.utc) + timedelta(days=2),
            location_name="Praça",
            category_id=category.id,
            organizer_id=other_user.id,
            status="active",
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id
        
        # 1. Global notification for all
        n1 = Notification(
            type="broadcast", title="Geral", message="Para todos",
            target_role="all", sent_at=datetime.now(timezone.utc)
        )
        # 2. Notification for participant role
        n2 = Notification(
            type="broadcast", title="Participantes", message="Para participantes",
            target_role="participante", sent_at=datetime.now(timezone.utc)
        )
        # 3. Notification for organizer role (should NOT see)
        n3 = Notification(
            type="broadcast", title="Organizadoras", message="Para organizadoras",
            target_role="organizadora", sent_at=datetime.now(timezone.utc)
        )
        # 4. Notification for event (user NOT participating yet - should NOT see)
        n4 = Notification(
            type="broadcast", title="Evento", message="Para o evento",
            event_id=event_id, sent_at=datetime.now(timezone.utc)
        )
        # 5. Not sent yet (should NOT see)
        n5 = Notification(
            type="broadcast", title="Não enviada", message="Aguardando",
            target_role="all", sent_at=None
        )
        
        db.session.add_all([n1, n2, n3, n4, n5])
        db.session.commit()

    headers = _auth_header(app, user)
    response = client.get("/api/notifications", headers=headers)
    assert response.status_code == 200
    
    titles = [n["title"] for n in response.json["data"]]
    assert "Geral" in titles
    assert "Participantes" in titles
    assert "Organizadoras" not in titles
    assert "Evento" not in titles
    assert "Não enviada" not in titles
    assert len(titles) == 2

    # Now participate in the event
    with app.app_context():
        participation = EventParticipation(event_id=event_id, user_id=user.id, status="confirmed")
        db.session.add(participation)
        db.session.commit()
        
    response = client.get("/api/notifications", headers=headers)
    titles = [n["title"] for n in response.json["data"]]
    assert "Evento" in titles
    assert len(titles) == 3

def test_list_notifications_read_status(client, app):
    user = _create_user(app)
    
    with app.app_context():
        n1 = Notification(
            type="broadcast", title="N1", message="M1",
            target_role="all", sent_at=datetime.now(timezone.utc)
        )
        n2 = Notification(
            type="broadcast", title="N2", message="M2",
            target_role="all", sent_at=datetime.now(timezone.utc)
        )
        db.session.add_all([n1, n2])
        db.session.commit()
        
        # Mark n1 as read
        read = NotificationRead(notification_id=n1.id, user_id=user.id)
        db.session.add(read)
        db.session.commit()
        
        n1_id = n1.id
        n2_id = n2.id

    headers = _auth_header(app, user)
    response = client.get("/api/notifications", headers=headers)
    assert response.status_code == 200
    
    data = response.json["data"]
    n1_item = next(n for n in data if n["id"] == n1_id)
    n2_item = next(n for n in data if n["id"] == n2_id)
    
    assert n1_item["is_read"] is True
    assert n2_item["is_read"] is False

def test_list_notifications_order(client, app):
    user = _create_user(app)
    now = datetime.now(timezone.utc)
    
    with app.app_context():
        n1 = Notification(
            type="broadcast", title="Old", message="Old",
            target_role="all", sent_at=now - timedelta(days=1)
        )
        n2 = Notification(
            type="broadcast", title="New", message="New",
            target_role="all", sent_at=now
        )
        db.session.add_all([n1, n2])
        db.session.commit()

    headers = _auth_header(app, user)
    response = client.get("/api/notifications", headers=headers)
    assert response.status_code == 200
    
    data = response.json["data"]
    assert data[0]["title"] == "New"
    assert data[1]["title"] == "Old"

def test_list_notifications_as_sender(client, app):
    # Organizer sends a notification to an event they organize
    # but they are NOT necessarily a 'participant' in the event_participations table.
    organizer = _create_user(app, phone="+5511933333333", role="organizadora")
    
    with app.app_context():
        category = EventCategory(name="Saúde")
        db.session.add(category)
        db.session.commit()
        db.session.refresh(category)
        
        event = Event(
            title="Ação do Organizador",
            event_datetime=datetime.now(timezone.utc) + timedelta(days=2),
            location_name="Rua",
            category_id=category.id,
            organizer_id=organizer.id,
            status="active",
        )
        db.session.add(event)
        db.session.commit()
        
        n1 = Notification(
            type="broadcast", title="Msg do Organizador", message="Olá participantes",
            event_id=event.id, sender_id=organizer.id, sent_at=datetime.now(timezone.utc)
        )
        db.session.add(n1)
        db.session.commit()
        
    headers = _auth_header(app, organizer)
    response = client.get("/api/notifications", headers=headers)
    assert response.status_code == 200
    
    titles = [n["title"] for n in response.json["data"]]
    assert "Msg do Organizador" in titles

def test_list_notifications_cover_image(client, app):
    user = _create_user(app)
    
    with app.app_context():
        category = EventCategory(name="Lazer")
        db.session.add(category)
        db.session.commit()
        
        event = Event(
            title="Evento com Imagem",
            event_datetime=datetime.now(timezone.utc) + timedelta(days=2),
            location_name="Clube",
            category_id=category.id,
            organizer_id=user.id,
            status="active",
            cover_image_url="http://example.com/image.jpg"
        )
        db.session.add(event)
        db.session.commit()
        
        event_id = event.id
        
        notification = Notification(
            type="broadcast", title="Notificação com Imagem", message="Veja a imagem",
            event_id=event_id, sent_at=datetime.now(timezone.utc)
        )
        db.session.add(notification)
        db.session.commit()
        
    # User must be participating or sender to see event-specific notification
    with app.app_context():
        participation = EventParticipation(event_id=event_id, user_id=user.id, status="confirmed")
        db.session.add(participation)
        db.session.commit()

    headers = _auth_header(app, user)
    response = client.get("/api/notifications", headers=headers)
    assert response.status_code == 200
    
    item = next(n for n in response.json["data"] if n["title"] == "Notificação com Imagem")
    assert item["cover_image_url"] == "http://example.com/image.jpg"

def test_mark_notification_read(client, app):
    user = _create_user(app)
    
    with app.app_context():
        notification = Notification(
            type="broadcast", title="Read Test", message="Test message",
            target_role="all", sent_at=datetime.now(timezone.utc)
        )
        db.session.add(notification)
        db.session.commit()
        notification_id = notification.id

    headers = _auth_header(app, user)
    
    # 1. Mark as read
    response = client.post(f"/api/notifications/{notification_id}/read", headers=headers)
    assert response.status_code == 200
    assert response.json["message"] == "Notificação marcada como lida"
    
    # Verify in DB
    with app.app_context():
        read = NotificationRead.query.filter_by(notification_id=notification_id, user_id=user.id).first()
        assert read is not None

    # 2. Mark as read again (idempotent)
    response = client.post(f"/api/notifications/{notification_id}/read", headers=headers)
    assert response.status_code == 200
    
    # 3. Notification not found
    response = client.post("/api/notifications/00000000-0000-0000-0000-000000000000/read", headers=headers)
    assert response.status_code == 404
