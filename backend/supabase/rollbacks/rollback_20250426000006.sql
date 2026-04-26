DROP TRIGGER  IF EXISTS trg_sync_participant_count ON public.event_participations;
DROP FUNCTION IF EXISTS public.sync_participant_count();
DROP INDEX IF EXISTS idx_participations_user_id;
DROP INDEX IF EXISTS idx_participations_event_id;
DROP TABLE IF EXISTS public.event_participations;