async function carregarPerfil() {
  try {
    const data = await apiGet('/api/me');
    document.getElementById('nome').textContent = data.full_name || 'Usuário';
    document.getElementById('subtitulo').textContent = data.role || 'Participante';
    document.getElementById('numero_eventos_criou').textContent = data.created_events_count || 0;
    document.getElementById('numero_eventos_participou').textContent = data.participated_events_count || 0;

    const isParticipante = data.role === 'participante';
    const isCoordenadora = data.role === 'coordenadora';

    // Oculta/mostra elementos com classe .participante-hide (para participantes)
    const elementosHide = document.querySelectorAll('.participante-hide');
    for (let el of elementosHide) {
      el.style.display = isParticipante ? 'none' : 'block';
    }

    // Botão "Adicionar Mobilizadora" só para coordenadoras
    const botaoMobilizadora = document.getElementById('botao_vermelho');
    if (botaoMobilizadora) {
      botaoMobilizadora.style.display = isCoordenadora ? 'flex' : 'none';
    }

    const botaoAvisos = document.getElementById('botao_azul');
    if(botaoAvisos) {
      botaoAvisos.style.display = isParticipante ? 'none' : 'flex';
    }

    // (Opcional) Botão "Enviar Avisos" pode ficar visível para organizadoras e coordenadoras
    // Mas se quiser esconder para participantes, já está tratado pela classe .participante-hide
    // Se quiser que apenas coordenadoras possam enviar avisos, pode adicionar lógica similar.
    // Por enquanto, deixamos como está (aparece para organizadoras e coordenadoras).

  } catch (err) {
    console.error('Erro ao carregar perfil:', err);
    mostrar_msg_erro('Erro ao carregar perfil', '' + err);
  } finally {
    ocultarLoading();
  }
}

function ocultarLoading() {
  const loadingScreen = document.getElementById('loading-screen');
  if (loadingScreen) {
    loadingScreen.style.opacity = '0';
    setTimeout(() => {
      loadingScreen.style.display = 'none';
    }, 500);
  }
}

function logout() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  window.location.href = 'tela-cadastro.html';
}

function abrirModalLogout() {
  const modal = document.getElementById('confirmacao-logout');
  if (modal) modal.style.display = 'flex';
}

function fecharModalLogout() {
  const modal = document.getElementById('confirmacao-logout');
  if (modal) modal.style.display = 'none';
}

function configurarBotoes() {
  // Botão "Enviar Avisos"
  const botaoAvisos = document.getElementById('botao_azul');
  if (botaoAvisos) {
    botaoAvisos.addEventListener('click', function() {
      if (window.ccaeAbrirModal) {
        window.ccaeAbrirModal('criar-aviso', null);
      } else {
        setTimeout(() => {
          if (window.ccaeAbrirModal) {
            window.ccaeAbrirModal('criar-aviso', null);
          } else {
            mostrar_msg_erro('Erro', 'Modal não disponível. Tente recarregar a página.');
          }
        }, 500);
      }
    });
  }

  // Botão "Adicionar Mobilizadora"
  const botaoMobilizadora = document.getElementById('botao_vermelho');
  if (botaoMobilizadora) {
    botaoMobilizadora.addEventListener('click', function() {
      if (window.ccaeAbrirModal) {
        window.ccaeAbrirModal('adicionar-mobilizadora', null);
      } else {
        setTimeout(() => {
          if (window.ccaeAbrirModal) {
            window.ccaeAbrirModal('adicionar-mobilizadora', null);
          } else {
            mostrar_msg_erro('Erro', 'Modal não disponível. Tente recarregar a página.');
          }
        }, 500);
      }
    });
  }

  // Botão "Sair" – evento no container inteiro (.icone_descricao:last-child)
  const containerSair = document.querySelector('.menu .icone_descricao:last-child');
  if (containerSair) {
    containerSair.addEventListener('click', function(e) {
      e.preventDefault();
      abrirModalLogout();
    });
  }

  // Modal de logout – botão Cancelar
  const cancelarBtn = document.getElementById('cancelar-logout');
  if (cancelarBtn) {
    cancelarBtn.addEventListener('click', fecharModalLogout);
  }

  // Modal de logout – botão Sair
  const confirmarBtn = document.getElementById('confirmar-logout');
  if (confirmarBtn) {
    confirmarBtn.addEventListener('click', function() {
      fecharModalLogout();
      logout();
    });
  }

  // Fechar modal ao clicar fora da caixa
  const modal = document.getElementById('confirmacao-logout');
  if (modal) {
    modal.addEventListener('click', function(e) {
      if (e.target === this) {
        fecharModalLogout();
      }
    });
  }
}

document.addEventListener('componentsReady', () => {
  carregarPerfil();
  configurarBotoes();
});