async function reqCriarEvento(evento) {
  try {
    await apiPost('/api/acoes', evento);

    await carregarEventos(); // atualiza tela
  } catch (err) {
    console.error('Erro ao criar evento:', err);
    mostrar_msg_erro('Erro ao criar evento', "" + err);
  }
}

function combineDateAndTime(dateString, timeString) {
  const [year, month, day] = dateString.split('-').map(Number);
  const [hours, minutes] = timeString.split(':').map(Number);

  return new Date(year, month - 1, day, hours, minutes);
}

async function controlarCadastroAvisosEventos(element) {
  // TODO: algum tipo de cache para /api/me seria interessante
  const usuarioAtual = await apiGet('/api/me', undefined);

  const container = document.getElementById("container-principal");

  const criarEvento = element.querySelector('#criar-evento');
  const criarAviso = element.querySelector('#criar-aviso');
  const adicionarMobilizadora = element.querySelector('#adicionar-mobilizadora');
  const detalhesEvento = element.querySelector('#detalhes-do-evento');

  const botaoFechar = element.querySelector('#header-botoes button:last-child');
  const tituloModal = element.querySelector('.header h2');
  const botaoAviso = element.querySelector('#botao-aviso');
  const botaoFooter = element.querySelector('#confirmar-presenca');



  // começa tudo fechado
  container.style.display = 'none';

  criarEvento.style.display = 'none';
  criarAviso.style.display = 'none';
  adicionarMobilizadora.style.display = 'none';
  detalhesEvento.style.display = 'none';

  window.MEModal = {
    tipo: null,
    evento: null
  };

  async function abrirModal(tipo, evento) {
    window.MEModal.tipo = tipo;
    window.MEModal.evento = evento || null;

    container.style.display = 'flex';

    criarEvento.style.display = 'none';
    criarAviso.style.display = 'none';
    adicionarMobilizadora.style.display = 'none';
    detalhesEvento.style.display = 'none';

    document.body.style.overflow = 'hidden';

    // título
    if (tituloModal) {
      if (tipo === 'detalhes-evento') tituloModal.innerText = 'Detalhes do Evento';
      if (tipo === 'criar-evento') tituloModal.innerText = 'Criar Evento';
      if (tipo === 'criar-aviso') tituloModal.innerText = 'Criar Aviso';
      if (tipo === 'adicionar-mobilizadora') tituloModal.innerText = 'Adicionar Mobilizadora';
    }

    // footer button text
    if (botaoFooter) {
      if (tipo === 'criar-evento') botaoFooter.innerText = 'Criar Evento';
      if (tipo === 'criar-aviso') botaoFooter.innerText = 'Enviar Aviso';
      if (tipo === 'adicionar-mobilizadora') botaoFooter.innerText = 'Adicionar Mobilizadora';
    }

    // mostrar seção certa
    if (tipo === 'criar-evento') criarEvento.style.display = 'block';
    if (tipo === 'criar-aviso') criarAviso.style.display = 'block';
    if (tipo === 'adicionar-mobilizadora') adicionarMobilizadora.style.display = 'block';
    if (tipo === 'detalhes-evento') detalhesEvento.style.display = 'block';

    if (tipo === 'criar-aviso') {
      const resp = await apiGet('/api/acoes', { responsavel: usuarioAtual.id });
      const sel = document.getElementById("tipo-evento-ja-existente");
      sel.innerHTML = '';
      for (let ac of resp.data) {
        const opt = document.createElement("option");
        opt.setAttribute('value', ac.id);
        opt.innerText = ac.title;
        sel.appendChild(opt);
      }
    }

    if (tipo === 'detalhes-evento') {
      try {
        const evt = window.MEModal.evento;
        const dataFmt = new Intl.DateTimeFormat(undefined, {
          day: 'numeric',
          month: 'long',
          year: 'numeric',
        });
        const horaFmt = new Intl.DateTimeFormat(undefined, {
          hour: 'numeric',
          minute: '2-digit'
        });
        const eData = dateTimeParseUTC(evt.event_datetime);
        if (evt.is_participating) {
          botaoFooter.innerText = 'Cancelar Participação';
        } else {
          botaoFooter.innerText = 'Confirmar Presença';
        }

        document.getElementById("det-tipo-evento").innerText = evt.category_name || '';
        document.getElementById("det-titulo-evento").innerText = evt.title;
        document.getElementById("det-descricao-evento").innerText = evt.description || '';
        document.getElementById("det-data-evento").innerText = dataFmt.format(eData);
        document.getElementById("det-horario-evento").innerText = horaFmt.format(eData);
        document.getElementById("det-endereco-evento").innerText = evt.location_name;
        document.getElementById("det-organizadora").innerText = evt.organizer_name || '<desconhecido>';
        document.getElementById("det-numero-pessoas-confirmadas").innerText = evt.participant_count;
      } catch (error) {
        console.log(error);
        mostrar_msg_erro('Não foi possível carregar mais detalhes do evento', '' + error);
        fecharModal();
      }
    }
  }

  // para criar um novo evento (página de ações comunitárias)
  const nome_evento = element.querySelector('#nome-evento');
  const tipo_evento = element.querySelector('#tipo-evento');
  const data_evento = element.querySelector('#data');
  const horario_evento = element.querySelector('#horario');
  const local_evento = element.querySelector('#local-evento');
  const descricao_evento = element.querySelector('#descricao-novo-evento');

  // para criar novo aviso (página de perfil)
  const evento_escolhido = element.querySelector('#tipo-evento-ja-existente');
  const titulo_aviso_novo = element.querySelector('#titulo-novo-aviso');
  const mensagem_aviso_novo = element.querySelector('#descricao-novo-aviso');

  // para adicionar mobilizadora (página de perfil)
  const telefone_mobilizadora = element.querySelector('#telefone-mobilizadora');


  tipo_evento.innerHTML = '';
  const res = await apiGet("/api/categories", undefined);
  console.log(res);
  const categorias = res.data;
  for (let cat of categorias) {
    const opt = document.createElement('option');
    opt.setAttribute('value', cat.id);
    opt.innerText = cat.name;
    tipo_evento.appendChild(opt);
  }


  // vamos usar o botaoFooter, declarado no começo do documento.
  botaoFooter.addEventListener('click', async () => {

    switch (window.MEModal.tipo) {
      case 'criar-evento':
        const novo_evento = {
          title: nome_evento.value,
          tipo: tipo_evento.value,
          event_datetime: combineDateAndTime(data_evento.value, horario_evento.value).toISOString(),
          location_name: local_evento.value,
          description: descricao_evento.value,
          organizer_id: usuarioAtual.id,
          status: 'active',
          category_id: tipo_evento.value
        }
        await reqCriarEvento(novo_evento);
        window.location.reload();
        break;

      case 'criar-aviso':
        try {
          await apiPost(`/api/acoes/${evento_escolhido.value}/notify`, {
            title: titulo_aviso_novo.value,
            message: mensagem_aviso_novo.value
          });
        } catch (error) {
          console.log(error);
          mostrar_msg_erro('Não foi possível criar o aviso', '' + error);
        }

        break;

      case 'adicionar-mobilizadora':
        const telefone_mobilizadora_value = telefone_mobilizadora.value
        break;

      case 'detalhes-evento':
        try {
          await apiPost(`/api/acoes/${window.MEModal.evento.id}/participate`, {});
          window.location.reload();
        } catch (error) {
          console.log(error);
          mostrar_msg_erro('Não foi possível confirmar a presença', '' + error);
        }

      default:
        break;
    }
    fecharModal();
  })

  function fecharModal() {
    container.style.display = 'none';

    criarEvento.style.display = 'none';
    criarAviso.style.display = 'none';
    adicionarMobilizadora.style.display = 'none';
    detalhesEvento.style.display = 'none';

    document.body.style.overflow = 'auto';
    window.MEModal.tipo = null;
    window.MEModal.evento = null;
  }


  // BOTÃO X
  if (botaoFechar) {
    botaoFechar.addEventListener('click', fecharModal);
  }




  const pagina = window.location.pathname;
  // ESCONDE O BOTÃO DE AVISO NO MODAL NA TELA DE PERFIL
  if (pagina.includes('tela_meu_perfil')) {
    if (botaoAviso) {
      botaoAviso.style.display = 'none';
    }
  }

  window.ccaeAbrirModal = abrirModal;

}

