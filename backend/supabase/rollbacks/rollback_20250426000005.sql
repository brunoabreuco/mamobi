DROP TRIGGER  IF EXISTS trg_events_updated_at ON public.events;
DROP INDEX IF EXISTS idx_events_scheduled_feed;
DROP INDEX IF EXISTS idx_events_category_id;
DROP INDEX IF EXISTS idx_events_status;
DROP INDEX IF EXISTS idx_events_organizer_id;
DROP INDEX IF EXISTS idx_events_event_datetime;
DROP TABLE IF EXISTS public.events;