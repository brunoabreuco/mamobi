-- =============================================================================
-- migrations/20260610000001_fix_users_role_constraint.sql
-- Adiciona 'coordenadora' ao CHECK constraint de users.role.
-- O role já é usado no código (api_routes.py) mas estava ausente no constraint.
-- =============================================================================

DO $$
DECLARE
  v_constraint text;
BEGIN
  SELECT conname INTO v_constraint
    FROM pg_constraint
   WHERE conrelid = 'public.users'::regclass
     AND contype  = 'c'
     AND pg_get_constraintdef(oid) LIKE '%participante%';

  IF v_constraint IS NOT NULL THEN
    EXECUTE 'ALTER TABLE public.users DROP CONSTRAINT ' || quote_ident(v_constraint);
  END IF;
END $$;

ALTER TABLE public.users
  ADD CONSTRAINT users_role_check
  CHECK (role IN ('participante', 'organizadora', 'coordenadora'));