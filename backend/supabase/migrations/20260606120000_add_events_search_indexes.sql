-- Migration: indices para filtros de busca de acoes
-- Prerequisito: extensao pg_trgm (ja criada na migration de extensions)

-- Indice trigram para busca textual ILIKE em title e description
-- pg_trgm permite que ILIKE '%termo%' use indice ao inves de seq scan
CREATE INDEX IF NOT EXISTS idx_events_title_trgm
    ON events USING gin (title gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_events_description_trgm
    ON events USING gin (description gin_trgm_ops);

-- Indice composto para filtros por categoria e data (ordem importa:
-- categoria tem cardinalidade baixa, event_datetime filtra o range)
CREATE INDEX IF NOT EXISTS idx_events_category_datetime
    ON events (category_id, event_datetime);

-- Indice para filtro por responsavel
CREATE INDEX IF NOT EXISTS idx_events_organizer_datetime
    ON events (organizer_id, event_datetime);

-- Indice simples em event_datetime para filtros apenas de periodo
CREATE INDEX IF NOT EXISTS idx_events_event_datetime
    ON events (event_datetime);