-- =============================================================================
-- migrations/20250426000005_create_events.sql
-- =============================================================================

-- participant_count é cache desnormalizado de COUNT(event_participations).
-- Mantido consistente via trigger na migration 000006.

CREATE TABLE public.events (
  id                uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
  title             varchar(200) NOT NULL,
  description       text,
  event_datetime    timestamptz  NOT NULL,
  location_name     varchar(200) NOT NULL,
  location_lat      decimal(9,6),
  location_lng      decimal(9,6),
  category_id       integer      REFERENCES public.event_categories(id) ON DELETE SET NULL,
  organizer_id      uuid         NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
  max_participants  integer      CHECK (max_participants > 0),
  participant_count integer      NOT NULL DEFAULT 0 CHECK (participant_count >= 0),
  status            varchar(20)  NOT NULL DEFAULT 'draft'
                                 CHECK (status IN ('draft', 'scheduled', 'ongoing', 'completed', 'cancelled')),
  cover_image_url   text,
  created_at        timestamptz  NOT NULL DEFAULT now(),
  updated_at        timestamptz  NOT NULL DEFAULT now()
);

CREATE INDEX idx_events_event_datetime ON public.events(event_datetime);
CREATE INDEX idx_events_organizer_id   ON public.events(organizer_id);
CREATE INDEX idx_events_status         ON public.events(status);
CREATE INDEX idx_events_category_id    ON public.events(category_id);
-- Índice parcial para listagem do feed (caso mais comum)
CREATE INDEX idx_events_scheduled_feed
  ON public.events(event_datetime)
  WHERE status IN ('scheduled', 'ongoing');

CREATE TRIGGER trg_events_updated_at
  BEFORE UPDATE ON public.events
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();