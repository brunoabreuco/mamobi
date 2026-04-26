-- =============================================================================
-- migrations/20250426000007_create_notifications.sql
-- =============================================================================

CREATE TABLE public.notifications (
  id           uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id     uuid         REFERENCES public.events(id) ON DELETE SET NULL,
  sender_id    uuid         REFERENCES public.users(id)  ON DELETE SET NULL,
  type         varchar(30)  NOT NULL
               CHECK (type IN ('reminder', 'broadcast', 'urgent', 'system')),
  title        varchar(150) NOT NULL,
  message      varchar(300) NOT NULL,
  target_role  varchar(20)  CHECK (target_role IN ('participante', 'organizadora', 'all')),
  scheduled_at timestamptz,
  sent_at      timestamptz,
  created_at   timestamptz  NOT NULL DEFAULT now()
);

CREATE INDEX idx_notifications_event_id     ON public.notifications(event_id);
CREATE INDEX idx_notifications_sender_id    ON public.notifications(sender_id);
CREATE INDEX idx_notifications_target_role  ON public.notifications(target_role);
-- Índice parcial para o cron job de lembretes (só pendentes)
CREATE INDEX idx_notifications_pending
  ON public.notifications(scheduled_at)
  WHERE sent_at IS NULL AND scheduled_at IS NOT NULL;