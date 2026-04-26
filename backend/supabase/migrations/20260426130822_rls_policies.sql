-- =============================================================================
-- migrations/20250426000011_rls_policies.sql
-- =============================================================================

-- -----------------------------------------------------------------------
-- users
-- -----------------------------------------------------------------------
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_select_own"
  ON public.users FOR SELECT
  TO authenticated
  USING (auth.uid() = id);

-- Organizadora precisa ver perfis de participantes dos seus eventos
CREATE POLICY "users_select_as_organizer"
  ON public.users FOR SELECT
  TO authenticated
  USING (public.get_user_role() = 'organizadora');

CREATE POLICY "users_update_own"
  ON public.users FOR UPDATE
  TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- INSERT via service_role apenas (trigger pós-signup de auth)

-- -----------------------------------------------------------------------
-- auth_otp -- sem exposição ao cliente; service_role only
-- -----------------------------------------------------------------------
ALTER TABLE public.auth_otp ENABLE ROW LEVEL SECURITY;
-- Sem policies: bloqueia tudo para anon e authenticated; service_role bypassa RLS

-- -----------------------------------------------------------------------
-- event_categories -- leitura pública já definida na migration 000004
-- -----------------------------------------------------------------------

-- -----------------------------------------------------------------------
-- events
-- -----------------------------------------------------------------------
ALTER TABLE public.events ENABLE ROW LEVEL SECURITY;

-- Todas as usuárias autenticadas leem eventos publicados/em andamento
CREATE POLICY "events_select_visible"
  ON public.events FOR SELECT
  TO authenticated
  USING (
    status IN ('scheduled', 'ongoing', 'completed')
    OR organizer_id = auth.uid()   -- organizadora vê seus próprios rascunhos
  );

-- Apenas organizadoras criam eventos e apenas como organizadora_id = si mesmas
CREATE POLICY "events_insert_organizer"
  ON public.events FOR INSERT
  TO authenticated
  WITH CHECK (
    public.get_user_role() = 'organizadora'
    AND organizer_id = auth.uid()
  );

-- Organizadora atualiza apenas seus eventos
CREATE POLICY "events_update_own"
  ON public.events FOR UPDATE
  TO authenticated
  USING (organizer_id = auth.uid())
  WITH CHECK (organizer_id = auth.uid());

-- Organizadora deleta apenas seus eventos (somente status draft/cancelled)
CREATE POLICY "events_delete_own"
  ON public.events FOR DELETE
  TO authenticated
  USING (
    organizer_id = auth.uid()
    AND status IN ('draft', 'cancelled')
  );

-- -----------------------------------------------------------------------
-- event_participations
-- -----------------------------------------------------------------------
ALTER TABLE public.event_participations ENABLE ROW LEVEL SECURITY;

-- Participante lê apenas as próprias participações
CREATE POLICY "participations_select_own"
  ON public.event_participations FOR SELECT
  TO authenticated
  USING (user_id = auth.uid());

-- Organizadora lê participações de eventos que ela criou
CREATE POLICY "participations_select_organizer"
  ON public.event_participations FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.events e
       WHERE e.id = event_id
         AND e.organizer_id = auth.uid()
    )
  );

-- Usuária insere apenas a própria participação
CREATE POLICY "participations_insert_own"
  ON public.event_participations FOR INSERT
  TO authenticated
  WITH CHECK (user_id = auth.uid());

-- Usuária atualiza apenas a própria participação (ex.: cancelar)
CREATE POLICY "participations_update_own"
  ON public.event_participations FOR UPDATE
  TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "participations_delete_own"
  ON public.event_participations FOR DELETE
  TO authenticated
  USING (user_id = auth.uid());

-- -----------------------------------------------------------------------
-- notifications
-- -----------------------------------------------------------------------
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;

-- Usuária lê notificações do seu role ou para todas
CREATE POLICY "notifications_select_by_role"
  ON public.notifications FOR SELECT
  TO authenticated
  USING (
    target_role = 'all'
    OR target_role = public.get_user_role()
  );

-- Apenas organizadoras criam notificações
CREATE POLICY "notifications_insert_organizer"
  ON public.notifications FOR INSERT
  TO authenticated
  WITH CHECK (
    public.get_user_role() = 'organizadora'
    AND sender_id = auth.uid()
  );

-- -----------------------------------------------------------------------
-- notification_reads
-- -----------------------------------------------------------------------
ALTER TABLE public.notification_reads ENABLE ROW LEVEL SECURITY;

CREATE POLICY "notification_reads_select_own"
  ON public.notification_reads FOR SELECT
  TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "notification_reads_insert_own"
  ON public.notification_reads FOR INSERT
  TO authenticated
  WITH CHECK (user_id = auth.uid());

-- -----------------------------------------------------------------------
-- fcm_tokens
-- -----------------------------------------------------------------------
ALTER TABLE public.fcm_tokens ENABLE ROW LEVEL SECURITY;

CREATE POLICY "fcm_tokens_select_own"
  ON public.fcm_tokens FOR SELECT
  TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "fcm_tokens_insert_own"
  ON public.fcm_tokens FOR INSERT
  TO authenticated
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "fcm_tokens_update_own"
  ON public.fcm_tokens FOR UPDATE
  TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "fcm_tokens_delete_own"
  ON public.fcm_tokens FOR DELETE
  TO authenticated
  USING (user_id = auth.uid());

-- -----------------------------------------------------------------------
-- sync_queue
-- -----------------------------------------------------------------------
ALTER TABLE public.sync_queue ENABLE ROW LEVEL SECURITY;

CREATE POLICY "sync_queue_select_own"
  ON public.sync_queue FOR SELECT
  TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "sync_queue_insert_own"
  ON public.sync_queue FOR INSERT
  TO authenticated
  WITH CHECK (user_id = auth.uid());

-- Atualização de status (pending -> processed/error) via service_role apenas