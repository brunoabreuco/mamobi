-- =============================================================================
-- rollback_20260610000003.sql
-- =============================================================================

ALTER TABLE public.notifications
  DROP CONSTRAINT IF EXISTS notifications_event_id_fkey,
  DROP CONSTRAINT IF EXISTS notifications_sender_id_fkey;