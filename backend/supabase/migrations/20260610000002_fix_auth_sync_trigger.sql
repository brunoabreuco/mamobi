-- =============================================================================
-- migrations/20260610000002_fix_auth_sync_trigger.sql
-- Corrige o trigger handle_new_user_sync_auth para lidar com a diferença de
-- tipos entre public.users.id (varchar) e auth.users.id (uuid).
-- =============================================================================

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
    -- Converte uuid -> text para atribuir ao campo varchar
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
      NEW.id::uuid,  -- cast varchar -> uuid para satisfazer o tipo de auth.users.id
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