-- =============================================================================
-- rollback_20260619000000.sql
-- =============================================================================

-- 2. Remove email
DROP INDEX IF EXISTS idx_users_email;

ALTER TABLE public.users
  DROP COLUMN IF EXISTS email;

-- 1. Restaura NOT NULL em phone
ALTER TABLE public.users
  ALTER COLUMN phone SET NOT NULL;

-- 4. Restaura o trigger para a versão anterior (20260610000002)
CREATE OR REPLACE FUNCTION public.handle_new_user_sync_auth()
RETURNS TRIGGER AS $$
DECLARE
  existing_id uuid;
BEGIN
  SELECT id INTO existing_id
    FROM auth.users
   WHERE phone = NEW.phone
   LIMIT 1;

  IF existing_id IS NOT NULL THEN
    NEW.id := existing_id::text;
  ELSE
    INSERT INTO auth.users (
      id,
      phone,
      aud,
      role,
      phone_confirmed_at,
      raw_app_meta_data,
      raw_user_meta_data,
      created_at,
      updated_at
    )
    VALUES (
      NEW.id::uuid,
      NEW.phone,
      'authenticated',
      'authenticated',
      now(),
      '{"provider":"phone","providers":["phone"]}',
      jsonb_build_object('full_name', NEW.full_name),
      now(),
      now()
    );
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;