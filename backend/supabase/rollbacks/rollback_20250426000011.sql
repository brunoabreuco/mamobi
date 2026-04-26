DROP POLICY IF EXISTS "sync_queue_insert_own"            ON public.sync_queue;
DROP POLICY IF EXISTS "sync_queue_select_own"            ON public.sync_queue;
ALTER TABLE public.sync_queue            DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "fcm_tokens_delete_own"            ON public.fcm_tokens;
DROP POLICY IF EXISTS "fcm_tokens_update_own"            ON public.fcm_tokens;
DROP POLICY IF EXISTS "fcm_tokens_insert_own"            ON public.fcm_tokens;
DROP POLICY IF EXISTS "fcm_tokens_select_own"            ON public.fcm_tokens;
ALTER TABLE public.fcm_tokens            DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "notification_reads_insert_own"    ON public.notification_reads;
DROP POLICY IF EXISTS "notification_reads_select_own"    ON public.notification_reads;
ALTER TABLE public.notification_reads    DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "notifications_insert_organizer"   ON public.notifications;
DROP POLICY IF EXISTS "notifications_select_by_role"     ON public.notifications;
ALTER TABLE public.notifications         DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "participations_delete_own"        ON public.event_participations;
DROP POLICY IF EXISTS "participations_update_own"        ON public.event_participations;
DROP POLICY IF EXISTS "participations_insert_own"        ON public.event_participations;
DROP POLICY IF EXISTS "participations_select_organizer"  ON public.event_participations;
DROP POLICY IF EXISTS "participations_select_own"        ON public.event_participations;
ALTER TABLE public.event_participations  DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "events_delete_own"                ON public.events;
DROP POLICY IF EXISTS "events_update_own"                ON public.events;
DROP POLICY IF EXISTS "events_insert_organizer"          ON public.events;
DROP POLICY IF EXISTS "events_select_visible"            ON public.events;
ALTER TABLE public.events                DISABLE ROW LEVEL SECURITY;

ALTER TABLE public.auth_otp              DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "users_update_own"                 ON public.users;
DROP POLICY IF EXISTS "users_select_as_organizer"        ON public.users;
DROP POLICY IF EXISTS "users_select_own"                 ON public.users;
ALTER TABLE public.users                 DISABLE ROW LEVEL SECURITY;