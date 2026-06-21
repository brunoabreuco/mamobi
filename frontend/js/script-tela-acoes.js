// 1. BUSCAR EVENTOS DO BACKEND
async function carregarEventos(query) {
  let params = undefined;
  if (query !== undefined) {
    params = { q: query };
  }
  try {
    const resp = await apiGet('/api/acoes', params);
    renderizarEventos(resp.data || []);
  } catch (err) {
    console.error('Erro ao buscar eventos:', err);
    mostrar_msg_erro('Erro ao buscar eventos:', "" + err);
  }
}

// 2. RENDERIZAR COMPONENTES NA TELA
async function renderizarEventos(eventos) {
  const mount = document.getElementById('lista-acoes');

  mount.innerHTML = '';

  // FORÇA LOCALE PT-BR para o mês e dia (curtos)
  const mesFmt = new Intl.DateTimeFormat('pt-BR', {
    month: 'short',
  });
  const diaFmt = new Intl.DateTimeFormat('pt-BR', {
    day: 'numeric',
  });

  for (let evento of eventos) {
    const date = dateTimeParseUTC(evento.event_datetime);
    const el = await make('componenteEventoDetalhado', {
      mes: mesFmt.format(date).toUpperCase(),
      dia: diaFmt.format(date),
      titulo: evento.title,
      tipo: evento.category_name || '',
      // 🔹 Agora usa formatToLocalDateTime para exibir data/hora completa em pt-BR
      hora: formatToLocalDateTime(evento.event_datetime),
      local: evento.location_name,
      confirmados: "" + evento.participant_count,
      organizador: evento.organizer_name,
    });

    if (!evento.is_participating) {
      el.querySelector('.confirmado').style.display = 'none';
    }

    el.addEventListener('click', () => {
      window.ccaeAbrirModal('detalhes-evento', evento);
    })

    mount.appendChild(el);
  }
}

async function configurarElementos() {
  const botaoAdicionarEvento = document.getElementById('btn-add-acao');
  const data = await apiGet('/api/me', undefined);
  botaoAdicionarEvento.addEventListener('click', () => ccaeAbrirModal('criar-evento'));
  if (data.role !== 'participante') {
    botaoAdicionarEvento.style.display = "block";
  }

  const barraPesquisa = document.getElementById("input-pesquisa");
  let typingTimer;
  const doneTypingInterval = 1000;
  const handler = function (event) {
    clearTimeout(typingTimer);

    typingTimer = setTimeout(function () {
      carregarEventos(event.target.value.trim() || undefined);
    }, doneTypingInterval);
  };
  barraPesquisa.addEventListener('keyup', handler);
  barraPesquisa.addEventListener('input', handler);
}

// 4. INICIALIZAÇÃO DA PÁGINA
document.addEventListener('componentsReady', () => {
  carregarEventos();
  configurarElementos();
});