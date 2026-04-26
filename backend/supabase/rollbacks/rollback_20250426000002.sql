DROP FUNCTION IF EXISTS public.get_user_role();
DROP TRIGGER  IF EXISTS trg_users_updated_at ON public.users;
DROP INDEX IF EXISTS idx_users_role;
DROP INDEX IF EXISTS idx_users_phone;
DROP TABLE IF EXISTS public.users;