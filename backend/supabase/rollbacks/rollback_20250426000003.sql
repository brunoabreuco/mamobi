DROP INDEX IF EXISTS idx_auth_otp_valid;
DROP INDEX IF EXISTS idx_auth_otp_expires_at;
DROP INDEX IF EXISTS idx_auth_otp_phone;
DROP TABLE IF EXISTS public.auth_otp;