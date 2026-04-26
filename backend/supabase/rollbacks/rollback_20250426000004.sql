DROP POLICY IF EXISTS "categories_select_authenticated" ON public.event_categories;
DROP INDEX IF EXISTS idx_event_categories_name;
DROP TABLE IF EXISTS public.event_categories;