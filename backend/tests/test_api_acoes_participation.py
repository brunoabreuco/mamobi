import pytest
from datetime import datetime, timezone, timedelta
from mamobi.models import User, EventCategory, Event, EventParticipation, db
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

def test_list_acoes_participation_status(client, app):
    user = _create_user(app)
    
    with app.app_context():
        category = EventCategory(name="Saúde")
        db.session.add(category)
        db.session.commit()
        
        # Event 1: User IS participating
        e1 = Event(
            title="Event Participating",
            event_datetime=datetime.now(timezone.utc) + timedelta(days=1),
            location_name="Loc 1",
            category_id=category.id,
            organizer_id=user.id,
            status="active"
        )
        # Event 2: User IS NOT participating
        e2 = Event(
            title="Event Not Participating",
            event_datetime=datetime.now(timezone.utc) + timedelta(days=2),
            location_name="Loc 2",
            category_id=category.id,
            organizer_id=user.id,
            status="active"
        )
        db.session.add_all([e1, e2])
        db.session.commit()
        
        p1 = EventParticipation(event_id=e1.id, user_id=user.id, status="confirmed")
        db.session.add(p1)
        db.session.commit()
        
        e1_id = e1.id
        e2_id = e2.id

    # 1. Anonymous request
    response = client.get("/api/acoes")
    assert response.status_code == 200
    for item in response.json["data"]:
        assert item["is_participating"] is False

    # 2. Authenticated request
    headers = _auth_header(app, user)
    response = client.get("/api/acoes", headers=headers)
    assert response.status_code == 200
    
    data = response.json["data"]
    item1 = next(i for i in data if i["id"] == e1_id)
    item2 = next(i for i in data if i["id"] == e2_id)
    
    assert item1["is_participating"] is True
    assert item2["is_participating"] is False

def test_participate_event_success(client, app):
    user = _create_user(app)
    headers = _auth_header(app, user)
    
    with app.app_context():
        category = EventCategory(name="Saúde")
        db.session.add(category)
        db.session.commit()
        
        event = Event(
            title="Ação Teste",
            event_datetime=datetime.now(timezone.utc) + timedelta(days=1),
            location_name="Rua Teste",
            category_id=category.id,
            organizer_id=user.id,
            status="active"
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id

    response = client.post(f"/api/acoes/{event_id}/participate", headers=headers)
    assert response.status_code == 201
    assert response.json["message"] == "Participação confirmada com sucesso"
    
    with app.app_context():
        p = EventParticipation.query.filter_by(event_id=event_id, user_id=user.id).first()
        assert p is not None
        assert p.status == "confirmed"
        
        ev = db.session.get(Event, event_id)
        assert ev.participant_count == 1

def test_participate_event_already_confirmed(client, app):
    user = _create_user(app)
    headers = _auth_header(app, user)
    
    with app.app_context():
        category = EventCategory(name="Saúde")
        db.session.add(category)
        db.session.commit()
        
        event = Event(
            title="Ação Teste",
            event_datetime=datetime.now(timezone.utc) + timedelta(days=1),
            location_name="Rua Teste",
            category_id=category.id,
            organizer_id=user.id,
            status="active"
        )
        db.session.add(event)
        db.session.commit()
        
        p = EventParticipation(event_id=event.id, user_id=user.id, status="confirmed")
        db.session.add(p)
        db.session.commit()
        event_id = event.id

    response = client.post(f"/api/acoes/{event_id}/participate", headers=headers)
    assert response.status_code == 200
    assert response.json["message"] == "Você já está participando deste evento"

def test_participate_event_full(client, app):
    user1 = _create_user(app, phone="+5511999999991")
    user2 = _create_user(app, phone="+5511999999992")
    headers2 = _auth_header(app, user2)
    
    with app.app_context():
        category = EventCategory(name="Saúde")
        db.session.add(category)
        db.session.commit()
        
        event = Event(
            title="Ação Lotada",
            event_datetime=datetime.now(timezone.utc) + timedelta(days=1),
            location_name="Rua Teste",
            category_id=category.id,
            organizer_id=user1.id,
            status="active",
            max_participants=1
        )
        db.session.add(event)
        db.session.commit()
        
        # User 1 participates first
        p = EventParticipation(event_id=event.id, user_id=user1.id, status="confirmed")
        db.session.add(p)
        db.session.commit()
        event_id = event.id

    # User 2 tries to participate
    response = client.post(f"/api/acoes/{event_id}/participate", headers=headers2)
    assert response.status_code == 400
    assert response.json["error"] == "Este evento já atingiu o limite de participantes"

