-- =============================================================================
-- migrations/20250426000009_create_fcm_tokens.sql
-- =============================================================================

CREATE TABLE public.fcm_tokens (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      uuid        NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  token        text        NOT NULL,
  device_type  varchar(10) CHECK (device_type IN ('android', 'ios', 'web')),
  is_active    boolean     NOT NULL DEFAULT true,
  last_used_at timestamptz,
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_fcm_tokens_token        ON public.fcm_tokens(token);
CREATE INDEX        idx_fcm_tokens_user_id      ON public.fcm_tokens(user_id);
-- Índice parcial para o cron de push (só tokens ativos)
CREATE INDEX        idx_fcm_tokens_active_user
  ON public.fcm_tokens(user_id)
  WHERE is_active = true;