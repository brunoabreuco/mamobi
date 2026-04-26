-- =============================================================================
-- migrations/20250426000008_create_notification_reads.sql
-- =============================================================================

CREATE TABLE public.notification_reads (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  notification_id uuid        NOT NULL REFERENCES public.notifications(id) ON DELETE CASCADE,
  user_id         uuid        NOT NULL REFERENCES public.users(id)          ON DELETE CASCADE,
  read_at         timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT uq_notification_read_user UNIQUE (notification_id, user_id)
);

CREATE INDEX idx_notification_reads_user_id ON public.notification_reads(user_id);
CREATE INDEX idx_notification_reads_notif   ON public.notification_reads(notification_id);