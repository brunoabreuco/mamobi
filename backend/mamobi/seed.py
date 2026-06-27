import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from mamobi.models import db, EventCategory, User, Event, EventParticipation, Notification

# Root of the project (one level up from backend/)
BASE_DIR = Path(__file__).parent.parent.parent
IMAGES_DIR = BASE_DIR / "frontend" / "images"

DEFAULT_CATEGORIES = [
    {
        "name": "Saúde e Bem-Estar Integral",
        "color": "#E91E63",
        "filename": "cat_saude.svg",
        "svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.42 4.58a5.4 5.4 0 0 0-7.65 0l-.77.78-.77-.78a5.4 5.4 0 0 0-7.65 0C1.46 6.7 1.33 10.28 4 13l8 8 8-8c2.67-2.72 2.54-6.3.42-8.42z"/></svg>'
    },
    {
        "name": "Educação e Formação Cidadã",
        "color": "#2196F3",
        "filename": "cat_educacao.svg",
        "svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c0 2 2 3 6 3s6-1 6-3v-5"/></svg>'
    },
    {
        "name": "Poesia, Literatura e Sarau",
        "color": "#9C27B0",
        "filename": "cat_poesia.svg",
        "svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>'
    },
    {
        "name": "Meio Ambiente e Agricultura Familiar",
        "color": "#4CAF50",
        "filename": "cat_ambiente.svg",
        "svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 20a7 7 0 0 1-7-7c0-2.3 1.1-4.3 2.8-5.6l1.3-1a7 7 0 0 1 9.8 0l1.3 1c1.7 1.3 2.8 3.3 2.8 5.6a7 7 0 0 1-7 7h-4z"/><path d="M12 20v-8m0 0l-3 3m3-3l3 3"/></svg>'
    },
    {
        "name": "Geração de Renda e Empreendedorismo Materno",
        "color": "#FF9800",
        "filename": "cat_renda.svg",
        "svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>'
    },
    {
        "name": "Infância e Recreação",
        "color": "#FFC107",
        "filename": "cat_infancia.svg",
        "svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>'
    },
    {
        "name": "Assistência Social e Acolhimento",
        "color": "#00BCD4",
        "filename": "cat_assistencia.svg",
        "svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>'
    },
    {
        "name": "Memória, Ancestralidade e Território",
        "color": "#795548",
        "filename": "cat_memoria.svg",
        "svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/><path d="M12 2a14.5 14.5 0 0 1 0 20 14.5 14.5 0 0 1 0-20"/></svg>'
    }
]

DEFAULT_USERS = [
    {
        "id": "00000000-0000-0000-0000-000000000001",
        "phone": "+5511999990001",
        "full_name": "Ana Coordenadora",
        "neighborhood": "Parelheiros",
        "role": "coordenadora"
    },
    {
        "id": "00000000-0000-0000-0000-000000000002",
        "phone": "+5511999990002",
        "full_name": "Maria Organizadora",
        "neighborhood": "Grajaú",
        "role": "organizadora"
    },
    {
        "id": "00000000-0000-0000-0000-000000000003",
        "phone": "+5511999990003",
        "full_name": "Carla Participante",
        "neighborhood": "Marsilac",
        "role": "participante"
    }
]

DEFAULT_EVENTS = [
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "title": "Roda de Conversa: Saúde Materna",
        "description": "Encontro para discutir saúde e bem-estar das mães da comunidade.",
        "category_name": "Saúde e Bem-Estar Integral",
        "organizer_phone": "+5511999990002",
        "location_name": "Posto de Saúde Local",
        "days_offset": 5,
        "status": "active"
    },
    {
        "id": "22222222-2222-2222-2222-222222222222",
        "title": "Oficina de Escrita Criativa",
        "description": "Expressão através da poesia e literatura.",
        "category_name": "Poesia, Literatura e Sarau",
        "organizer_phone": "+5511999990002",
        "location_name": "Biblioteca Comunitária",
        "days_offset": 10,
        "status": "active"
    }
]

DEFAULT_PARTICIPATIONS = [
    {
        "event_id": "11111111-1111-1111-1111-111111111111",
        "user_id": "00000000-0000-0000-0000-000000000003",
        "status": "confirmed"
    }
]

DEFAULT_NOTIFICATIONS = [
    {
        "type": "broadcast",
        "title": "Bem-vinda!",
        "message": "Obrigada por se juntar às Mães Mobilizadoras.",
        "target_role": "all",
        "sent_at_offset": -1
    },
    {
        "type": "broadcast",
        "title": "Nova Ação!",
        "message": "Confira a nova Roda de Conversa sobre Saúde Materna.",
        "event_id": "11111111-1111-1111-1111-111111111111",
        "sender_id": "00000000-0000-0000-0000-000000000002",
        "sent_at_offset": 0
    }
]

def seed_categories():
    """Seeds default event categories and writes SVG files if missing."""
    os.makedirs(IMAGES_DIR, exist_ok=True)

    try:
        for cat_data in DEFAULT_CATEGORIES:
            # 1. Write SVG file
            svg_path = IMAGES_DIR / cat_data["filename"]
            if not svg_path.exists():
                svg_path.write_text(cat_data["svg"])

            # 2. Seed DB
            icon_url = f"/images/{cat_data['filename']}"
            existing = db.session.execute(
                db.select(EventCategory).where(EventCategory.name == cat_data["name"])
            ).scalar()
            
            if not existing:
                new_cat = EventCategory(
                    name=cat_data["name"],
                    color=cat_data["color"],
                    icon=icon_url
                )
                db.session.add(new_cat)
            elif existing.icon != icon_url:
                existing.icon = icon_url
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        if "no such table" in str(e).lower():
            return
        raise

def seed_users():
    """Seeds default users."""
    try:
        for user_data in DEFAULT_USERS:
            existing = db.session.get(User, user_data["id"])
            if not existing:
                new_user = User(**user_data)
                db.session.add(new_user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        if "no such table" in str(e).lower():
            return
        raise

def seed_events():
    """Seeds default events."""
    try:
        for event_data in DEFAULT_EVENTS:
            existing = db.session.get(Event, event_data["id"])
            if not existing:
                category = db.session.execute(
                    db.select(EventCategory).where(EventCategory.name == event_data["category_name"])
                ).scalar()
                
                organizer = db.session.execute(
                    db.select(User).where(User.phone == event_data["organizer_phone"])
                ).scalar()
                
                if category and organizer:
                    event_datetime = datetime.now(timezone.utc) + timedelta(days=event_data["days_offset"])
                    new_event = Event(
                        id=event_data["id"],
                        title=event_data["title"],
                        description=event_data["description"],
                        category_id=category.id,
                        organizer_id=organizer.id,
                        location_name=event_data["location_name"],
                        event_datetime=event_datetime,
                        status=event_data["status"]
                    )
                    db.session.add(new_event)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        if "no such table" in str(e).lower():
            return
        raise

def seed_participations():
    """Seeds default participations."""
    try:
        for part_data in DEFAULT_PARTICIPATIONS:
            existing = db.session.execute(
                db.select(EventParticipation).where(
                    EventParticipation.event_id == part_data["event_id"],
                    EventParticipation.user_id == part_data["user_id"]
                )
            ).scalar()
            
            if not existing:
                new_part = EventParticipation(**part_data)
                db.session.add(new_part)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        if "no such table" in str(e).lower():
            return
        raise

def seed_notifications():
    """Seeds default notifications."""
    try:
        for notif_data_orig in DEFAULT_NOTIFICATIONS:
            existing = db.session.execute(
                db.select(Notification).where(Notification.title == notif_data_orig["title"])
            ).scalar()
            
            if not existing:
                notif_data = notif_data_orig.copy()
                offset = notif_data.pop("sent_at_offset")
                sent_at = datetime.now(timezone.utc) + timedelta(hours=offset)
                new_notif = Notification(**notif_data, sent_at=sent_at)
                db.session.add(new_notif)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        if "no such table" in str(e).lower():
            return
        raise

def seed_all():
    """Seeds everything."""
    seed_categories()
    seed_users()
    seed_events()
    seed_participations()
    seed_notifications()
