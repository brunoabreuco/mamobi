-- =============================================================================
-- migrations/20260619000000_add_google_oauth_support.sql
-- =============================================================================

-- 1. phone passa a ser nullable (usuários Google completam na etapa de perfil)
ALTER TABLE public.users
  ALTER COLUMN phone DROP NOT NULL;

-- 2. Adiciona email
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS email varchar(254);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON public.users(email)
  WHERE email IS NOT NULL;

-- 3. Corrige trigger: para usuários Google, auth.users já existe com o ID
--    correto; o trigger antigo buscava por phone (NULL) e tentava inserir
--    um novo auth.users com o mesmo UUID → colisão de PK.
CREATE OR REPLACE FUNCTION public.handle_new_user_sync_auth()
RETURNS TRIGGER AS $$
DECLARE
  existing_by_id    uuid;
  existing_by_phone uuid;
BEGIN
  SELECT id INTO existing_by_id
    FROM auth.users
   WHERE id = NEW.id::uuid
   LIMIT 1;

  IF existing_by_id IS NOT NULL THEN
    RETURN NEW;
  END IF;

  IF NEW.phone IS NOT NULL THEN
    SELECT id INTO existing_by_phone
      FROM auth.users
     WHERE phone = NEW.phone
     LIMIT 1;

    IF existing_by_phone IS NOT NULL THEN
      NEW.id := existing_by_phone::text;
    ELSE
      INSERT INTO auth.users (
        id, phone, aud, role, phone_confirmed_at,
        raw_app_meta_data, raw_user_meta_data, created_at, updated_at
      ) VALUES (
        NEW.id::uuid, NEW.phone, 'authenticated', 'authenticated', now(),
        '{"provider":"phone","providers":["phone"]}',
        jsonb_build_object('full_name', NEW.full_name),
        now(), now()
      );
    END IF;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;