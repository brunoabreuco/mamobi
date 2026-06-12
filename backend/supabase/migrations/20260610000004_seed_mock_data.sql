-- =============================================================================
-- migrations/20260610000000_seed_mock_data.sql
-- Dados de teste: categorias, usuários, eventos, participações e notificações.
-- Todos os blocos são idempotentes (WHERE NOT EXISTS).
--
-- Contexto: tabelas criadas via db.create_all() do SQLAlchemy -- defaults de
-- id, created_at, updated_at e registered_at são Python-side, não existem
-- no banco. Todos os campos obrigatórios são passados explicitamente.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Categorias (id é serial, sem problema)
-- -----------------------------------------------------------------------------
INSERT INTO public.event_categories (name, icon, color) VALUES
  ('Saúde e Bem-Estar Integral',                  '/images/cat_saude.svg',       '#E91E63'),
  ('Educação e Formação Cidadã',                  '/images/cat_educacao.svg',    '#2196F3'),
  ('Poesia, Literatura e Sarau',                  '/images/cat_poesia.svg',      '#9C27B0'),
  ('Meio Ambiente e Agricultura Familiar',        '/images/cat_ambiente.svg',    '#4CAF50'),
  ('Geração de Renda e Empreendedorismo Materno', '/images/cat_renda.svg',       '#FF9800'),
  ('Infância e Recreação',                        '/images/cat_infancia.svg',    '#FFC107'),
  ('Assistência Social e Acolhimento',            '/images/cat_assistencia.svg', '#00BCD4'),
  ('Memória, Ancestralidade e Território',        '/images/cat_memoria.svg',     '#795548')
ON CONFLICT (name) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 2. Usuários
-- -----------------------------------------------------------------------------
ALTER TABLE public.users DISABLE TRIGGER trg_create_auth_user_before_profile;

INSERT INTO public.users (id, phone, full_name, neighborhood, role, created_at, updated_at)
SELECT '00000000-0000-0000-0000-000000000001', '+5511999990001', 'Ana Coordenadora', 'Parelheiros', 'coordenadora', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM public.users WHERE id = '00000000-0000-0000-0000-000000000001');

INSERT INTO public.users (id, phone, full_name, neighborhood, role, created_at, updated_at)
SELECT '00000000-0000-0000-0000-000000000002', '+5511999990002', 'Maria Organizadora', 'Grajaú', 'organizadora', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM public.users WHERE id = '00000000-0000-0000-0000-000000000002');

INSERT INTO public.users (id, phone, full_name, neighborhood, role, created_at, updated_at)
SELECT '00000000-0000-0000-0000-000000000003', '+5511999990003', 'Carla Participante', 'Marsilac', 'participante', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM public.users WHERE id = '00000000-0000-0000-0000-000000000003');

ALTER TABLE public.users ENABLE TRIGGER trg_create_auth_user_before_profile;

-- -----------------------------------------------------------------------------
-- 3. Eventos
-- -----------------------------------------------------------------------------
INSERT INTO public.events (id, title, description, category_id, organizer_id, location_name, event_datetime, status, created_at, updated_at)
SELECT
  '11111111-1111-1111-1111-111111111111',
  'Roda de Conversa: Saúde Materna',
  'Encontro para discutir saúde e bem-estar das mães da comunidade.',
  (SELECT id FROM public.event_categories WHERE name = 'Saúde e Bem-Estar Integral'),
  '00000000-0000-0000-0000-000000000002',
  'Posto de Saúde Local',
  NOW() + INTERVAL '5 days',
  'scheduled',
  NOW(),
  NOW()
WHERE NOT EXISTS (SELECT 1 FROM public.events WHERE id = '11111111-1111-1111-1111-111111111111');

INSERT INTO public.events (id, title, description, category_id, organizer_id, location_name, event_datetime, status, created_at, updated_at)
SELECT
  '22222222-2222-2222-2222-222222222222',
  'Oficina de Escrita Criativa',
  'Expressão através da poesia e literatura.',
  (SELECT id FROM public.event_categories WHERE name = 'Poesia, Literatura e Sarau'),
  '00000000-0000-0000-0000-000000000002',
  'Biblioteca Comunitária',
  NOW() + INTERVAL '10 days',
  'scheduled',
  NOW(),
  NOW()
WHERE NOT EXISTS (SELECT 1 FROM public.events WHERE id = '22222222-2222-2222-2222-222222222222');

-- -----------------------------------------------------------------------------
-- 4. Participações
-- -----------------------------------------------------------------------------
INSERT INTO public.event_participations (id, event_id, user_id, status, registered_at)
SELECT
  gen_random_uuid()::text,
  '11111111-1111-1111-1111-111111111111',
  '00000000-0000-0000-0000-000000000003',
  'confirmed',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.event_participations
   WHERE event_id = '11111111-1111-1111-1111-111111111111'
     AND user_id  = '00000000-0000-0000-0000-000000000003'
);

-- Notificações omitidas: a FK notifications_sender_id_fkey está apontando
-- para sync_queue em vez de users (schema corrompido pelo db.create_all()).
-- Corrija o constraint antes de inserir notificações -- veja rollback abaixo.