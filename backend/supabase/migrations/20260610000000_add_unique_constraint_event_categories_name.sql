-- migrations/20260611000000_add_unique_constraint_event_categories_name.sql
ALTER TABLE public.event_categories 
ADD CONSTRAINT event_categories_name_unique UNIQUE (name);