-- =============================================================================
-- migrations/20250426000003_create_auth_otp.sql
-- =============================================================================

-- Controla códigos SMS do fluxo de login customizado via Edge Function.
-- Cada tentativa de login gera um registro aqui com código, validade e
-- contador de tentativas. O backend invalida após N falhas ou expiração.
-- Acessada exclusivamente via service_role -- sem RLS necessário.

CREATE TABLE public.auth_otp (
  id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  phone      varchar(20) NOT NULL,
  code       char(6)     NOT NULL,
  expires_at timestamptz NOT NULL,
  used_at    timestamptz,
  attempts   integer     NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_auth_otp_phone      ON public.auth_otp(phone);
CREATE INDEX idx_auth_otp_expires_at ON public.auth_otp(expires_at);
-- Índice parcial para buscar apenas OTPs ainda válidos
CREATE INDEX idx_auth_otp_valid
  ON public.auth_otp(phone, expires_at)
  WHERE used_at IS NULL;