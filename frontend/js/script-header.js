function configurarHeader(element) {

  const barraPesquisa = element.querySelector('.barra_pesquisa');
  const filtros = element.querySelector('.filtros');
  const naoLidos = element.querySelector('.nao_lidos');

  const pagina = window.location.pathname;

  if (pagina.includes('tela_avisos')) {
    if (barraPesquisa) barraPesquisa.style.display = 'none';
    if (filtros) filtros.style.display = 'none';
  }

  if (
    pagina.includes('tela_meu_perfil') ||
    pagina.includes('tela_calendario')
  ) {
    if (barraPesquisa) barraPesquisa.style.display = 'none';
    if (filtros) filtros.style.display = 'none';
    if (naoLidos) naoLidos.style.display = 'none';
  }

  if (pagina.includes('tela_acoes_comunitarias')) {
    if (naoLidos) naoLidos.style.display = 'none';
  }
}