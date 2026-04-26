-- =============================================================================
-- migrations/20250426000010_create_sync_queue.sql
-- =============================================================================

-- Fila de operações offline. O cliente escreve aqui quando sem conexão;
-- o Service Worker processa e sincroniza com o servidor ao reconectar.

CREATE TABLE public.sync_queue (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       uuid        REFERENCES public.users(id) ON DELETE SET NULL,
  entity_type   varchar(50) NOT NULL,
  entity_id     uuid,
  operation     varchar(10) NOT NULL CHECK (operation IN ('insert', 'update', 'delete')),
  payload       jsonb       NOT NULL,
  status        varchar(20) NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'processed', 'error')),
  error_message text,
  created_at    timestamptz NOT NULL DEFAULT now(),
  processed_at  timestamptz
);

CREATE INDEX idx_sync_queue_user_id   ON public.sync_queue(user_id);
CREATE INDEX idx_sync_queue_created   ON public.sync_queue(created_at);
-- Índice parcial para processar apenas pendentes
CREATE INDEX idx_sync_queue_pending
  ON public.sync_queue(user_id, created_at)
  WHERE status = 'pending';