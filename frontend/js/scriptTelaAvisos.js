async function carregarAvisos() {
  let resp = null;
  try {
    resp = await apiGet('/api/notifications');
  } catch (error) {
    mostrar_msg_erro('Erro ao carregar os avisos', '' + error);
    ocultarLoading();
    return;
  }
  let avisos = [];
  for (let dat of resp.data) {
    avisos.push({
      id: dat.id,
      lido: dat.is_read,
      titulo: dat.title,
      mensagem: dat.message,
      imagem: dat.cover_image_url || '/images/icone-mensagem-fundo-verde.png',
      quando: dat.sent_at ? formatToLocalDate(dat.sent_at) : '',
      sent_at: dat.sent_at // manter para o modal
    });
  }
  const mount = document.getElementById('lista-avisos');
  mount.innerHTML = "";
  for (let aviso of avisos) {
    const comp = await make('componenteAviso', aviso);
    if (aviso.lido) {
      const bolinha = comp.querySelector('img.novo');
      if (bolinha) bolinha.style.display = 'none';
    }
    comp.addEventListener('click', function () {
      // Marca como lido se não estiver
      if (!aviso.lido) {
        apiPost(`/api/notifications/${aviso.id}/read`, {})
          .then(() => {
            const bolinha = comp.querySelector('img.novo');
            if (bolinha) bolinha.style.display = 'none';
            aviso.lido = true;
          })
          .catch(err => console.error('Erro ao marcar como lido:', err));
      }
      // Abre o modal com os detalhes do aviso
      if (window.ccaeAbrirModal) {
        window.ccaeAbrirModal('detalhes-aviso', aviso);
      } else {
        console.warn('Modal não disponível');
      }
    });
    mount.appendChild(comp);
  }
  // 🔹 OCULTA LOADING APÓS RENDERIZAR
  ocultarLoading();
}

// 🔹 FUNÇÃO PARA OCULTAR LOADING
function ocultarLoading() {
  const loadingScreen = document.getElementById('loading-screen');
  if (loadingScreen) {
    loadingScreen.style.opacity = '0';
    setTimeout(() => {
      loadingScreen.style.display = 'none';
    }, 500);
  }
}

carregarAvisos();