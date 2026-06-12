-- =============================================================================
-- rollback_20260610000001.sql
-- Desfaz a migration 20260610000001_fix_users_role_constraint.sql
-- =============================================================================

ALTER TABLE public.users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE public.users
  ADD CONSTRAINT users_role_check
  CHECK (role IN ('participante', 'organizadora'));