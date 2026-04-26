-- =============================================================================
-- migrations/20250426000006_create_event_participations.sql
-- =============================================================================

CREATE TABLE public.event_participations (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id      uuid        NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
  user_id       uuid        NOT NULL REFERENCES public.users(id)  ON DELETE CASCADE,
  status        varchar(20) NOT NULL DEFAULT 'confirmed'
                            CHECK (status IN ('confirmed', 'cancelled', 'waitlist')),
  registered_at timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT uq_participation_event_user UNIQUE (event_id, user_id)
);

CREATE INDEX idx_participations_event_id ON public.event_participations(event_id);
CREATE INDEX idx_participations_user_id  ON public.event_participations(user_id);

-- Mantém events.participant_count em sincronia.
-- Só conta registros com status = 'confirmed'.

CREATE OR REPLACE FUNCTION public.sync_participant_count()
  RETURNS trigger
  LANGUAGE plpgsql
AS $$
BEGIN
  IF TG_OP = 'INSERT' AND NEW.status = 'confirmed' THEN
    UPDATE public.events
       SET participant_count = participant_count + 1
     WHERE id = NEW.event_id;

  ELSIF TG_OP = 'DELETE' AND OLD.status = 'confirmed' THEN
    UPDATE public.events
       SET participant_count = GREATEST(participant_count - 1, 0)
     WHERE id = OLD.event_id;

  ELSIF TG_OP = 'UPDATE' AND OLD.status IS DISTINCT FROM NEW.status THEN
    IF NEW.status = 'confirmed' AND OLD.status <> 'confirmed' THEN
      UPDATE public.events
         SET participant_count = participant_count + 1
       WHERE id = NEW.event_id;
    ELSIF OLD.status = 'confirmed' AND NEW.status <> 'confirmed' THEN
      UPDATE public.events
         SET participant_count = GREATEST(participant_count - 1, 0)
       WHERE id = NEW.event_id;
    END IF;
  END IF;

  RETURN COALESCE(NEW, OLD);
END;
$$;

CREATE TRIGGER trg_sync_participant_count
  AFTER INSERT OR UPDATE OF status OR DELETE ON public.event_participations
  FOR EACH ROW EXECUTE FUNCTION public.sync_participant_count();