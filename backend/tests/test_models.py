import pytest
from flask import Flask
from datetime import datetime, timezone
from mamobi.models import db, User, EventCategory, Event, EventParticipation


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def session(app):
    return db.session


@pytest.fixture
def base_data(session):
    # Create test users
    organizer = User(
        phone="11999999991",
        full_name="Maria Organizadora",
        neighborhood="Centro",
        role="organizer",
    )
    participant = User(
        phone="11999999992",
        full_name="Joana Participante",
        neighborhood="Vila Nova",
        role="user",
    )

    # Create test category
    category = EventCategory(name="Saúde")

    session.add_all([organizer, participant, category])
    session.commit()

    return {"organizer": organizer, "participant": participant, "category": category}


def test_increment_participant_count(session, base_data):
    """Test if participant_count increases when an EventParticipation is added."""
    event = Event(
        title="Palestra sobre Saúde da Mulher",
        event_datetime=datetime.now(timezone.utc),
        location_name="Posto de Saúde",
        category_id=base_data["category"].id,
        organizer_id=base_data["organizer"].id,
        status="scheduled",
    )
    session.add(event)
    session.commit()

    assert event.participant_count == 0

    # Insert participation
    participation = EventParticipation(
        event_id=event.id, user_id=base_data["participant"].id, status="confirmed"
    )
    session.add(participation)
    session.commit()

    # Verify increment
    session.refresh(event)
    assert event.participant_count == 1


def test_decrement_participant_count(session, base_data):
    """Test if participant_count decreases when an EventParticipation is removed."""
    event = Event(
        title="Roda de Conversa",
        event_datetime=datetime.now(timezone.utc),
        location_name="Praça Central",
        category_id=base_data["category"].id,
        organizer_id=base_data["organizer"].id,
        status="scheduled",
    )
    session.add(event)
    session.commit()

    participation = EventParticipation(
        event_id=event.id, user_id=base_data["participant"].id, status="confirmed"
    )
    session.add(participation)
    session.commit()

    session.refresh(event)
    assert event.participant_count == 1

    # Delete participation
    session.delete(participation)
    session.commit()

    # Verify decrement
    session.refresh(event)
    assert event.participant_count == 0


def test_update_participant_count(session, base_data):
    """Test if participant_count updates correctly when an EventParticipation's event is changed."""
    event1 = Event(
        title="Evento 1",
        event_datetime=datetime.now(timezone.utc),
        location_name="Local 1",
        category_id=base_data["category"].id,
        organizer_id=base_data["organizer"].id,
        status="scheduled",
    )
    event2 = Event(
        title="Evento 2",
        event_datetime=datetime.now(timezone.utc),
        location_name="Local 2",
        category_id=base_data["category"].id,
        organizer_id=base_data["organizer"].id,
        status="scheduled",
    )
    session.add_all([event1, event2])
    session.commit()

    # Add participation to Event 1
    participation = EventParticipation(
        event_id=event1.id, user_id=base_data["participant"].id, status="confirmed"
    )
    session.add(participation)
    session.commit()

    session.refresh(event1)
    session.refresh(event2)
    assert event1.participant_count == 1
    assert event2.participant_count == 0

    # Change the event_id from Event 1 to Event 2
    participation.event_id = event2.id
    session.commit()

    # Verify count decremented on Event 1 and incremented on Event 2
    session.refresh(event1)
    session.refresh(event2)
    assert event1.participant_count == 0
    assert event2.participant_count == 1


def test_multiple_participations(session, base_data):
    """Test if participant_count handles multiple participations accurately."""
    event = Event(
        title="Mutirão",
        event_datetime=datetime.now(timezone.utc),
        location_name="Rua Principal",
        category_id=base_data["category"].id,
        organizer_id=base_data["organizer"].id,
        status="scheduled",
    )
    session.add(event)

    # Create extra users
    user2 = User(phone="333", full_name="User 3", neighborhood="Bairro", role="user")
    user3 = User(phone="444", full_name="User 4", neighborhood="Bairro", role="user")
    session.add_all([user2, user3])
    session.commit()

    # Add 3 participations
    p1 = EventParticipation(
        event_id=event.id, user_id=base_data["participant"].id, status="confirmed"
    )
    p2 = EventParticipation(event_id=event.id, user_id=user2.id, status="confirmed")
    p3 = EventParticipation(event_id=event.id, user_id=user3.id, status="confirmed")

    session.add_all([p1, p2, p3])
    session.commit()

    session.refresh(event)
    assert event.participant_count == 3

    # Remove 2 participations
    session.delete(p1)
    session.delete(p2)
    session.commit()

    session.refresh(event)
    assert event.participant_count == 1


def test_update_participation_status_no_count_change(session, base_data):
    """Test that modifying other fields (like status) does not trigger count changes."""
    event = Event(
        title="Palestra",
        event_datetime=datetime.now(timezone.utc),
        location_name="Escola",
        category_id=base_data["category"].id,
        organizer_id=base_data["organizer"].id,
        status="scheduled",
    )
    session.add(event)
    session.commit()

    participation = EventParticipation(
        event_id=event.id, user_id=base_data["participant"].id, status="registered"
    )
    session.add(participation)
    session.commit()

    session.refresh(event)
    assert event.participant_count == 1

    # Update status, NOT the event_id
    participation.status = "attended"
    session.commit()

    session.refresh(event)
    assert event.participant_count == 1  # Should remain 1


def test_update_via_relationship(session, base_data):
    """Test if participant_count updates correctly when modified via the ORM relationship."""
    event1 = Event(
        title="Event A",
        event_datetime=datetime.now(timezone.utc),
        location_name="Local A",
        category_id=base_data["category"].id,
        organizer_id=base_data["organizer"].id,
        status="scheduled",
    )
    event2 = Event(
        title="Event B",
        event_datetime=datetime.now(timezone.utc),
        location_name="Local B",
        category_id=base_data["category"].id,
        organizer_id=base_data["organizer"].id,
        status="scheduled",
    )
    session.add_all([event1, event2])
    session.commit()

    participation = EventParticipation(
        event=event1, user_id=base_data["participant"].id, status="confirmed"
    )
    session.add(participation)
    session.commit()

    session.refresh(event1)
    session.refresh(event2)
    assert event1.participant_count == 1
    assert event2.participant_count == 0

    # Reassign via ORM relationship
    participation.event = event2
    session.commit()

    session.refresh(event1)
    session.refresh(event2)
    assert event1.participant_count == 0
    assert event2.participant_count == 1
