import uuid
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    CheckConstraint,
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    JSON,
    event,
)

db = SQLAlchemy()


def generate_uuid():
    return str(uuid.uuid4())


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = (
        # Garante que todo usuário tenha ao menos uma identidade.
        # Usuários OTP têm phone; usuários Google têm email.
        CheckConstraint(
            "phone IS NOT NULL OR email IS NOT NULL",
            name="users_has_identity",
        ),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    phone = Column(String(20), unique=True, nullable=True)   # nullable: Google users não têm telefone
    email = Column(String(254), unique=True, nullable=True)  # nullable: OTP users podem não ter e-mail
    pending_phone = Column(String(20), nullable=True)
    full_name = Column(String(150), nullable=False)
    neighborhood = Column(String(100), nullable=True)
    role = Column(String(20), nullable=False)
    avatar_url = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    events_organized = db.relationship("Event", backref="organizer", lazy=True)
    participations = db.relationship("EventParticipation", backref="user", lazy=True)
    fcm_tokens = db.relationship("FCMToken", backref="user", lazy=True)
    sync_queue_items = db.relationship("SyncQueue", backref="user", lazy=True)
    notification_reads = db.relationship("NotificationRead", backref="user", lazy=True)
    notifications_sent = db.relationship("Notification", backref="sender", lazy=True)
    role_changes_received = db.relationship(
        "RoleChange",
        foreign_keys="RoleChange.user_id",
        backref="target_user",
        lazy=True,
    )
    role_changes_made = db.relationship(
        "RoleChange",
        foreign_keys="RoleChange.changed_by",
        backref="actor",
        lazy=True,
    )


class AuthOTP(db.Model):
    __tablename__ = "auth_otp"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    phone = Column(String(20), nullable=False)
    code = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EventCategory(db.Model):
    __tablename__ = "event_categories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(80), nullable=False)
    icon = Column(String(50), nullable=True)
    color = Column(String(7), nullable=True)

    events = db.relationship("Event", backref="category", lazy=True)


class Event(db.Model):
    __tablename__ = "events"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    event_datetime = Column(DateTime, nullable=False)
    location_name = Column(String(200), nullable=False)
    location_lat = Column(Numeric(9, 6), nullable=True)
    location_lng = Column(Numeric(9, 6), nullable=True)
    category_id = Column(Integer, ForeignKey("event_categories.id"), nullable=False)
    organizer_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    max_participants = Column(Integer, nullable=True)
    participant_count = Column(Integer, default=0)
    status = Column(String(20), nullable=False)
    cover_image_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    participations = db.relationship("EventParticipation", backref="event", lazy=True)
    notifications = db.relationship("Notification", backref="event", lazy=True)


class EventParticipation(db.Model):
    __tablename__ = "event_participations"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    event_id = Column(String(36), ForeignKey("events.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    status = Column(String(20), nullable=False)
    registered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SyncQueue(db.Model):
    __tablename__ = "sync_queue"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(36), nullable=False)
    operation = Column(String(10), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime, nullable=True)


class Notification(db.Model):
    __tablename__ = "notifications"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    event_id = Column(String(36), ForeignKey("events.id"), nullable=True)
    sender_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    type = Column(String(30), nullable=False)
    title = Column(String(150), nullable=False)
    message = Column(String(300), nullable=False)
    target_role = Column(String(20), nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    reads = db.relationship("NotificationRead", backref="notification", lazy=True)


class NotificationRead(db.Model):
    __tablename__ = "notification_reads"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    notification_id = Column(String(36), ForeignKey("notifications.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    read_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class FCMToken(db.Model):
    __tablename__ = "fcm_tokens"
    user_id = Column(String(36), ForeignKey("users.id"), primary_key=True)
    token = Column(Text, primary_key=True)
    device_type = Column(String(10), nullable=True)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class RoleChange(db.Model):
    """Auditoria imutável de alterações de role."""
    __tablename__ = "role_changes"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    changed_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    old_role = Column(String(20), nullable=False)
    new_role = Column(String(20), nullable=False)
    changed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


"""
O trigger PostgreSQL já filtra por status = 'confirmed' corretamente, é suficiente e é a camada certa para manter essa invariante.

# ---------------------------------------------------------------------------
# Triggers de participant_count
# ---------------------------------------------------------------------------

@event.listens_for(EventParticipation, "after_insert")
def increment_participant_count(mapper, connection, target):
    table = Event.__table__
    connection.execute(
        table.update()
        .where(table.c.id == target.event_id)
        .values(participant_count=table.c.participant_count + 1)
    )


@event.listens_for(EventParticipation, "after_delete")
def decrement_participant_count(mapper, connection, target):
    table = Event.__table__
    connection.execute(
        table.update()
        .where(table.c.id == target.event_id)
        .values(participant_count=table.c.participant_count - 1)
    )


@event.listens_for(EventParticipation, "before_update")
def update_participant_count(mapper, connection, target):
    state = db.inspect(target)
    history = state.get_history("event_id", True)

    if history.has_changes():
        table = Event.__table__

        old_event_id = history.deleted[0] if history.deleted else None

        if not old_event_id:
            part_table = EventParticipation.__table__
            row = connection.execute(
                db.select(part_table.c.event_id).where(part_table.c.id == target.id)
            ).first()
            if row:
                old_event_id = row[0]

        new_event_id = history.added[0] if history.added else None

        if old_event_id and old_event_id != new_event_id:
            connection.execute(
                table.update()
                .where(table.c.id == old_event_id)
                .values(participant_count=table.c.participant_count - 1)
            )
        if new_event_id and old_event_id != new_event_id:
            connection.execute(
                table.update()
                .where(table.c.id == new_event_id)
                .values(participant_count=table.c.participant_count + 1)
            )
"""