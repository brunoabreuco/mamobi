-- =============================================================================
-- migrations/20250426000004_create_event_categories.sql
-- =============================================================================

CREATE TABLE public.event_categories (
  id    serial      PRIMARY KEY,
  name  varchar(80) NOT NULL,
  icon  varchar(50),
  color char(7)     CHECK (color ~ '^#[0-9A-Fa-f]{6}$')
);

CREATE UNIQUE INDEX idx_event_categories_name ON public.event_categories(name);

-- Leitura pública; escrita apenas via service_role (sem policy = bloqueado para clientes)
ALTER TABLE public.event_categories ENABLE ROW LEVEL SECURITY;

CREATE POLICY "categories_select_authenticated"
  ON public.event_categories FOR SELECT
  TO authenticated
  USING (true);

-- Seed de referência
INSERT INTO public.event_categories (name, icon, color) VALUES
  ('Saúde',         'heart',         '#E53E3E'),
  ('Educação',      'book-open',     '#3182CE'),
  ('Cultura',       'music',         '#805AD5'),
  ('Meio Ambiente', 'leaf',          '#38A169'),
  ('Assistência',   'hand',          '#DD6B20'),
  ('Reunião',       'users',         '#718096');