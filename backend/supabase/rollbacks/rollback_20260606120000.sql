-- Rollback: remove indices de busca de acoes
DROP INDEX IF EXISTS idx_events_title_trgm;
DROP INDEX IF EXISTS idx_events_description_trgm;
DROP INDEX IF EXISTS idx_events_category_datetime;
DROP INDEX IF EXISTS idx_events_organizer_datetime;
DROP INDEX IF EXISTS idx_events_event_datetime;