from datetime import datetime

from sqlalchemy import or_

from maes_mobilizadoras.models import Event, db


def build_event_filters(
    q: str | None = None,
    categoria: int | None = None,
    de: datetime | None = None,
    ate: datetime | None = None,
    responsavel: str | None = None,
) -> list:
    """
    Retorna lista de clausulas SQLAlchemy WHERE prontas para uso em
    db.select(Event).where(*filtros) ou db.select(func.count()).where(*filtros).

    Args:
        q:           Termo de busca textual (case-insensitive, title e description).
        categoria:   ID inteiro de event_categories.
        de:          Limite inferior de event_datetime (inclusivo).
        ate:         Limite superior de event_datetime (inclusivo, ate meia-noite do dia).
        responsavel: UUID do organizador (organizer_id).

    Returns:
        Lista de expressoes SQLAlchemy. Vazia se nenhum filtro ativo.
    """
    filters = []

    if q:
        term = f"%{q}%"
        filters.append(
            or_(
                Event.title.ilike(term),
                Event.description.ilike(term),
            )
        )

    if categoria is not None:
        filters.append(Event.category_id == categoria)

    if de is not None:
        filters.append(Event.event_datetime >= de)

    if ate is not None:
        # Inclui o dia inteiro: ate 23:59:59 do dia informado
        filters.append(Event.event_datetime <= ate.replace(hour=23, minute=59, second=59))

    if responsavel is not None:
        filters.append(Event.organizer_id == responsavel)

    return filters