-- =============================================================================
-- migrations/20260610000003_fix_notifications_fk.sql
-- Corrige as FKs de notifications que foram criadas incorretamente pelo
-- db.create_all() do SQLAlchemy:
--   - sender_id aponta para sync_queue em vez de users
--   - event_id pode estar NOT NULL quando deveria ser nullable
-- =============================================================================

-- Remove constraints incorretos
ALTER TABLE public.notifications
  DROP CONSTRAINT IF EXISTS notifications_sender_id_fkey,
  DROP CONSTRAINT IF EXISTS notifications_event_id_fkey;

-- Garante que as colunas sejam nullable (notificações de sistema não têm evento/sender)
ALTER TABLE public.notifications
  ALTER COLUMN event_id  DROP NOT NULL,
  ALTER COLUMN sender_id DROP NOT NULL;

-- Recria as FKs apontando para as tabelas corretas
ALTER TABLE public.notifications
  ADD CONSTRAINT notifications_event_id_fkey
    FOREIGN KEY (event_id)  REFERENCES public.events(id) ON DELETE SET NULL,
  ADD CONSTRAINT notifications_sender_id_fkey
    FOREIGN KEY (sender_id) REFERENCES public.users(id)  ON DELETE SET NULL;