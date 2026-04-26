-- =============================================================================
-- migrations/20250426000002_create_users.sql
-- =============================================================================

-- Tabela de perfil que estende auth.users do Supabase.
-- id é FK para auth.users, criado automaticamente via trigger de auth.

CREATE TABLE public.users (
  id           uuid         PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  phone        varchar(20)  NOT NULL,
  full_name    varchar(150) NOT NULL,
  neighborhood varchar(100),
  role         varchar(20)  NOT NULL DEFAULT 'participante'
                            CHECK (role IN ('participante', 'organizadora')),
  avatar_url   text,
  is_active    boolean      NOT NULL DEFAULT true,
  created_at   timestamptz  NOT NULL DEFAULT now(),
  updated_at   timestamptz  NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_users_phone ON public.users(phone);
CREATE INDEX        idx_users_role  ON public.users(role);

CREATE TRIGGER trg_users_updated_at
  BEFORE UPDATE ON public.users
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE OR REPLACE FUNCTION public.get_user_role()
  RETURNS text
  LANGUAGE sql
  SECURITY DEFINER
  STABLE
AS $$
  SELECT role FROM public.users WHERE id = auth.uid();
$$;