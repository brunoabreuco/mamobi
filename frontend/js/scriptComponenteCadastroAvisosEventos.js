async function reqCriarEvento(evento) {
  try {
    await apiPost('/api/acoes', evento);
    if (typeof carregarEventos === 'function') {
      await carregarEventos();
    }
  } catch (err) {
    console.error('Erro ao criar evento:', err);
    mostrar_msg_erro('Erro ao criar evento', "" + err);
  }
}

function combineDateAndTime(dateString, timeString) {
  if (!dateString || !timeString) {
    throw new Error('Preencha a data e o horário corretamente.');
  }
  const [year, month, day] = dateString.split('-').map(Number);
  const [hours, minutes] = timeString.split(':').map(Number);
  if (isNaN(year) || isNaN(month) || isNaN(day) || isNaN(hours) || isNaN(minutes)) {
    throw new Error('Data ou horário inválidos.');
  }
  const date = new Date(year, month - 1, day, hours, minutes);
  if (isNaN(date.getTime())) {
    throw new Error('Data ou horário inválidos.');
  }
  const now = new Date();
  now.setSeconds(0, 0);
  if (date < now) {
    throw new Error('A data e horário devem ser no futuro.');
  }
  return date;
}

async function controlarCadastroAvisosEventos(element) {
  const usuarioAtual = await apiGet('/api/me', undefined);

  window.ccaeAbrirModal = async function(tipo, evento) {
    await abrirModal(tipo, evento);
  };

  const container = document.getElementById("container-principal");
  const confirmacaoDelete = document.getElementById('confirmacao-delete');

  const criarEvento = element.querySelector('#criar-evento');
  const criarAviso = element.querySelector('#criar-aviso');
  const adicionarMobilizadora = element.querySelector('#adicionar-mobilizadora');
  const detalhesEvento = element.querySelector('#detalhes-do-evento');
  const detalhesAviso = element.querySelector('#detalhes-aviso');

  const botaoFechar = element.querySelector('#fechar-modal');
  const botaoDeletar = element.querySelector('#deletar-evento');
  const tituloModal = element.querySelector('.header h2');
  const botaoAviso = element.querySelector('#botao-aviso');
  const botaoFooter = element.querySelector('#confirmar-presenca');
  const hrFooter = document.getElementById('hr-footer');

  const cancelarDelete = document.getElementById('cancelar-delete');
  const confirmarDelete = document.getElementById('confirmar-delete');
  const msgDelete = document.getElementById('confirmacao-delete-msg');

  container.style.display = 'none';
  if (confirmacaoDelete) confirmacaoDelete.style.display = 'none';

  criarEvento.style.display = 'none';
  criarAviso.style.display = 'none';
  adicionarMobilizadora.style.display = 'none';
  detalhesEvento.style.display = 'none';
  if (detalhesAviso) detalhesAviso.style.display = 'none';
  if (botaoDeletar) botaoDeletar.style.display = 'none';

  window.MEModal = {
    tipo: null,
    evento: null
  };

  async function abrirModal(tipo, evento) {
    window.MEModal.tipo = tipo;
    window.MEModal.evento = evento || null;

    container.style.display = 'flex';
    if (confirmacaoDelete) confirmacaoDelete.style.display = 'none';

    criarEvento.style.display = 'none';
    criarAviso.style.display = 'none';
    adicionarMobilizadora.style.display = 'none';
    detalhesEvento.style.display = 'none';
    if (detalhesAviso) detalhesAviso.style.display = 'none';
    if (botaoDeletar) botaoDeletar.style.display = 'none';

    document.body.style.overflow = 'hidden';

    if (tituloModal) {
      if (tipo === 'detalhes-evento') tituloModal.innerText = 'Detalhes do Evento';
      else if (tipo === 'detalhes-aviso') tituloModal.innerText = 'Detalhes do Aviso';
      else if (tipo === 'criar-evento') tituloModal.innerText = 'Criar Evento';
      else if (tipo === 'criar-aviso') tituloModal.innerText = 'Criar Aviso';
      else if (tipo === 'adicionar-mobilizadora') tituloModal.innerText = 'Adicionar Mobilizadora';
    }

    if (botaoFooter) {
      if (tipo === 'criar-evento') {
        botaoFooter.innerText = 'Criar Evento';
        botaoFooter.style.display = 'block';
      } else if (tipo === 'criar-aviso') {
        botaoFooter.innerText = 'Enviar Aviso';
        botaoFooter.style.display = 'block';
      } else if (tipo === 'adicionar-mobilizadora') {
        botaoFooter.innerText = 'Adicionar Mobilizadora';
        botaoFooter.style.display = 'block';
      } else if (tipo === 'detalhes-aviso') {
        botaoFooter.style.display = 'none';
        if (hrFooter) hrFooter.style.display = 'none';
      } else if (tipo === 'detalhes-evento') {
        botaoFooter.style.display = 'block';
        if (hrFooter) hrFooter.style.display = 'block';
        if (botaoDeletar) {
          const evt = window.MEModal.evento;
          if (evt) {
            const isOrganizer = evt.organizer_id === usuarioAtual.id;
            const isCoordinator = usuarioAtual.role === 'coordenadora';
            if (isOrganizer || isCoordinator) {
              botaoDeletar.style.display = 'block';
            } else {
              botaoDeletar.style.display = 'none';
            }
          }
        }
      }
    }

    if (tipo === 'criar-evento') criarEvento.style.display = 'block';
    else if (tipo === 'criar-aviso') criarAviso.style.display = 'block';
    else if (tipo === 'adicionar-mobilizadora') adicionarMobilizadora.style.display = 'block';
    else if (tipo === 'detalhes-evento') detalhesEvento.style.display = 'block';
    else if (tipo === 'detalhes-aviso' && detalhesAviso) detalhesAviso.style.display = 'block';

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
        const dataFmt = new Intl.DateTimeFormat('pt-BR', {
          day: 'numeric',
          month: 'long',
          year: 'numeric',
        });
        const horaFmt = new Intl.DateTimeFormat('pt-BR', {
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

    if (tipo === 'detalhes-aviso' && detalhesAviso) {
      try {
        const aviso = window.MEModal.evento;
        document.getElementById("det-aviso-titulo").innerText = aviso.titulo || 'Sem título';
        document.getElementById("det-aviso-mensagem").innerText = aviso.mensagem || '';
        const dataFormatada = aviso.quando || (aviso.sent_at ? formatToLocalDate(aviso.sent_at) : '');
        document.getElementById("det-aviso-data").innerText = dataFormatada || 'Data não disponível';
        document.getElementById("det-aviso-remetente").innerText = 'Administração';
      } catch (error) {
        console.log(error);
        mostrar_msg_erro('Não foi possível carregar detalhes do aviso', '' + error);
        fecharModal();
      }
    }
  }

  function fecharModal() {
    console.log('fecharModal chamado');
    container.style.display = 'none';
    if (confirmacaoDelete) confirmacaoDelete.style.display = 'none';
    criarEvento.style.display = 'none';
    criarAviso.style.display = 'none';
    adicionarMobilizadora.style.display = 'none';
    detalhesEvento.style.display = 'none';
    if (detalhesAviso) detalhesAviso.style.display = 'none';
    if (hrFooter) hrFooter.style.display = 'block';
    if (botaoDeletar) botaoDeletar.style.display = 'none';

    document.body.style.overflow = 'auto';
    window.MEModal.tipo = null;
    window.MEModal.evento = null;
  }

  function abrirConfirmacao() {
    const evt = window.MEModal.evento;
    if (!evt) return;
    msgDelete.innerText = `Tem certeza que deseja deletar o evento "${evt.title}"? Esta ação não pode ser desfeita.`;
    if (confirmacaoDelete) {
      confirmacaoDelete.style.display = 'flex';
    }
  }

  function fecharConfirmacao() {
    console.log('fecharConfirmacao chamado');
    if (confirmacaoDelete) {
      confirmacaoDelete.style.display = 'none';
    }
  }

  // 🔹 FUNÇÃO DE DELETAR CORRIGIDA
  async function executarDelete() {
    const evt = window.MEModal.evento;
    if (!evt) {
        console.warn('Nenhum evento para deletar');
        return;
    }
    try {
        console.log('Deletando evento:', evt.id);
        await apiDelete(`/api/acoes/${evt.id}`);
        console.log('Evento deletado com sucesso');
        
        // 🔹 Fecha todos os modais
        fecharModal();
        fecharConfirmacao();
        
        // 🔹 Aguarda 200ms para garantir que a UI atualizou, depois recarrega
        setTimeout(() => {
            console.log('Recarregando página...');
            window.location.reload();
        }, 200);
        
    } catch (error) {
        console.error('Erro ao deletar evento:', error);
        mostrar_msg_erro('Não foi possível deletar o evento', '' + error);
        fecharConfirmacao();
    }
  }

  if (botaoFechar) {
    botaoFechar.addEventListener('click', fecharModal);
  }

  if (botaoDeletar) {
    botaoDeletar.addEventListener('click', abrirConfirmacao);
  }

  if (cancelarDelete) {
    cancelarDelete.addEventListener('click', fecharConfirmacao);
  }

  if (confirmarDelete) {
    confirmarDelete.addEventListener('click', executarDelete);
  }

  if (confirmacaoDelete) {
    confirmacaoDelete.addEventListener('click', function(e) {
      if (e.target === this) {
        fecharConfirmacao();
      }
    });
  }

  if (botaoFooter) {
    botaoFooter.addEventListener('click', async () => {
      switch (window.MEModal.tipo) {
        case 'criar-evento': {
          const nome_evento = document.getElementById('nome-evento');
          const tipo_evento = document.getElementById('tipo-evento');
          const data_evento = document.getElementById('data');
          const horario_evento = document.getElementById('horario');
          const local_evento = document.getElementById('local-evento');
          const descricao_evento = document.getElementById('descricao-novo-evento');

          if (!nome_evento.value || !tipo_evento.value || !data_evento.value || !horario_evento.value || !local_evento.value) {
            mostrar_msg_erro('Preencha todos os campos obrigatórios (Nome, Tipo, Data, Horário e Local).', '');
            return;
          }

          try {
            const dataCombinada = combineDateAndTime(data_evento.value, horario_evento.value);
            const novo_evento = {
              title: nome_evento.value,
              event_datetime: dataCombinada.toISOString(),
              location_name: local_evento.value,
              description: descricao_evento.value || '',
              organizer_id: usuarioAtual.id,
              status: 'active',
              category_id: tipo_evento.value
            };
            await reqCriarEvento(novo_evento);
            window.location.reload();
          } catch (error) {
            console.error(error);
            mostrar_msg_erro('Erro ao criar evento', error.message || 'Verifique a data e horário.');
          }
          break;
        }

        case 'criar-aviso': {
          const evento_escolhido = document.getElementById('tipo-evento-ja-existente');
          const titulo_aviso = document.getElementById('titulo-novo-aviso');
          const mensagem_aviso = document.getElementById('descricao-novo-aviso');
          if (!evento_escolhido.value || !titulo_aviso.value || !mensagem_aviso.value) {
            mostrar_msg_erro('Preencha todos os campos do aviso.', '');
            return;
          }
          try {
            await apiPost(`/api/acoes/${evento_escolhido.value}/notify`, {
              title: titulo_aviso.value,
              message: mensagem_aviso.value
            });
            mostrar_msg_erro('Aviso enviado com sucesso!', '');
          } catch (error) {
            console.error(error);
            mostrar_msg_erro('Não foi possível criar o aviso', '' + error);
          }
          break;
        }

        case 'adicionar-mobilizadora': {
          const telefone = document.getElementById('telefone-mobilizadora');
          const phoneValue = telefone.value.trim();
          if (!phoneValue) {
              mostrar_msg_erro('Erro', 'Por favor, informe o telefone da mobilizadora.');
              return;
          }

          try {
              const searchResult = await apiGet('/admin/users', { phone: phoneValue });
              const users = searchResult.items || [];

              if (users.length === 0) {
                  mostrar_msg_erro('Erro', 'Nenhuma usuária encontrada com este telefone.');
                  return;
              }

              const userToPromote = users[0];
              
              if (userToPromote.role === 'organizadora' || userToPromote.role === 'coordenadora') {
                  mostrar_msg_erro('Aviso', 'Esta usuária já é mobilizadora (ou coordenadora).');
                  return;
              }

              const confirmacao = confirm(`Deseja promover "${userToPromote.full_name}" (${userToPromote.phone}) a mobilizadora?`);
              if (!confirmacao) return;

              await apiPatch(`/admin/users/${userToPromote.id}/role`, { role: 'organizadora' });
              mostrar_msg_erro('Sucesso', 'Mobilizadora adicionada com sucesso!');
              setTimeout(() => window.location.reload(), 500);
          } catch (error) {
              console.error('Erro ao adicionar mobilizadora:', error);
              mostrar_msg_erro('Erro', 'Não foi possível adicionar mobilizadora: ' + error.message);
          }
          break;
        }

        case 'detalhes-evento': {
          const evt = window.MEModal.evento;
          try {
            await apiPost(`/api/acoes/${evt.id}/participate`, {});
            window.location.reload();
          } catch (error) {
            console.error(error);
            mostrar_msg_erro('Não foi possível confirmar a presença', '' + error);
          }
          break;
        }

        default:
          break;
      }
      fecharModal();
    });
  }

  (async function carregarCategorias() {
    const tipo_evento = document.getElementById('tipo-evento');
    if (!tipo_evento) return;
    try {
      const res = await apiGet("/api/categories");
      const categorias = res.data || [];
      tipo_evento.innerHTML = '';
      for (let cat of categorias) {
        const opt = document.createElement('option');
        opt.setAttribute('value', cat.id);
        opt.innerText = cat.name;
        tipo_evento.appendChild(opt);
      }
    } catch (err) {
      console.error('Erro ao carregar categorias:', err);
    }
  })();

  const pagina = window.location.pathname;
  if (pagina.includes('tela_meu_perfil')) {
    if (botaoAviso) {
      botaoAviso.style.display = 'none';
    }
  }

  window.ccaeAbrirModal = abrirModal;
}