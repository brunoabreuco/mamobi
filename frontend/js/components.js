/**
 * Biblioteca de Componentes Simples
 * 
 * Esta biblioteca permite carregar componentes HTML dinamicamente e injetar dados (props) neles.
 * 
 * Funcionamento base:
 * 1. Componentes são arquivos .html separados.
 * 2. `data-prop="nome"`: Define que o innerText do elemento será substituído pelo valor de props['nome'].
 * 3. `data-attr-X="nome"`: Define que o atributo 'X' do elemento será substituído pelo valor de props['nome'].
 * 4. `data-spec="nome-do-componente"`: No HTML principal, identifica onde um componente deve ser renderizado.
 * 5. `data-prop-nome="valor"`: Passa propriedades diretamente pelo HTML.
 *
 * Dentro de código javascript, use a função `make` para renderizar componentes.
 */

/**
 * Carrega o conteúdo HTML de um arquivo externo e o encapsula em uma div.
 * 
 * @param {string} htmlUrl - A URL ou caminho para o arquivo .html do componente.
 * @returns {Promise<HTMLElement>} Uma promessa que resolve para o elemento div contendo o HTML.
 */
async function loadComponent(htmlUrl) {
  const htmlResponse = await fetch(htmlUrl);
  const html = await htmlResponse.text();
  const element = document.createElement('div');
  element.innerHTML = html;
  return element;
}

/**
 * Aplica as propriedades (props) aos elementos internos de um componente.
 * Procura por atributos 'data-prop' para texto e 'data-attr-*' para atributos.
 * 
 * @param {HTMLElement} element - O elemento raiz do componente.
 * @param {Object} props - Objeto contendo as chaves e valores a serem injetados.
 */
function setProps(element, props) {
  const it = element.querySelectorAll('*');

  for (let el of it) {
    // Define o conteúdo de texto baseado em data-prop
    if (el.hasAttribute('data-prop')) {
      let propName = el.getAttribute('data-prop');
      el.innerText = props[propName];
    }

    // Define atributos baseados em data-attr-
    for (let attr of el.attributes) {
      if (attr.name.startsWith('data-attr-')) {
        let attrName = attr.name.replace('data-attr-', '');
        let propName = attr.value;
        el.setAttribute(attrName, props[propName]);
      }
    }
  }

  // CONTROLE DE VISIBILIDADE POR TELA

  const barraPesquisa = element.querySelector('.barra_pesquisa');
  const filtros = element.querySelector('.filtros');
  const naoLidos = element.querySelector('.nao_lidos');

  const pagina = window.location.pathname;

  // tela_avisos.html
  if (pagina.includes('tela_avisos')) {
    if (barraPesquisa) barraPesquisa.style.display = 'none';
    if (filtros) filtros.style.display = 'none';
  }

  // tela_meu_perfil.html e tela_calendario.html
  if (
    pagina.includes('tela_meu_perfil') ||
    pagina.includes('tela_calendario')
  ) {
    if (barraPesquisa) barraPesquisa.style.display = 'none';
    if (filtros) filtros.style.display = 'none';
    if (naoLidos) naoLidos.style.display = 'none';
  }

  // tela_acoes_comunitarias.html
  if (pagina.includes('tela_acoes_comunitarias')) {
    if (naoLidos) naoLidos.style.display = 'none';
  }
}
/**
 * Cria uma instância de um componente, carrega seu HTML e aplica as propriedades.
 * 
 * @param {string} spec - O nome do arquivo do componente (sem a extensão .html).
 * @param {Object} props - As propriedades a serem aplicadas ao componente.
 * @returns {Promise<HTMLElement>} O elemento do componente pronto para ser inserido no DOM.
 */
async function make(spec, props) {
  const htmlUrl = './' + spec + '.html';
  const element = await loadComponent(htmlUrl);
  element.classList.add('c-' + spec);
  setProps(element, props);

    if (spec === 'componenteCadastroAvisosEventos') {

    controlarCadastroAvisosEventos(element);

  }

  return element;
}

/**
 * Percorre o DOM em busca de elementos com o atributo 'data-spec' e os inicializa automaticamente.
 * Também extrai atributos 'data-prop-*' do elemento container para passar como props.
 */
function loadAllComponents() {
  const it = document.querySelectorAll('*');
  for (let element of it) {
    if (element.hasAttribute('data-spec')) {
      const spec = element.getAttribute('data-spec');
      let props = {};
      // Extrai propriedades definidas como data-prop-nome="valor"
      for (let attr of element.attributes) {
        if (attr.name.startsWith('data-prop-')) {
          props[attr.name.replace('data-prop-', '')] = attr.value;
        }
      }
      // Renderiza o componente e substitui o conteúdo do elemento
      make(spec, props).then(el => {
        element.innerHTML = '';
        element.appendChild(el);

        if (spec === 'footer') {
          const icone_inicio = document.querySelector('.inicio');
          const icone_calendario = document.querySelector('.calendario');
          const icone_avisos = document.querySelector('.avisos');
          const icone_perfil = document.querySelector('.perfil');

          const tela = window.location.pathname;
          console.log(window.location.pathname);

          switch (tela) {
              case '/frontend/tela_acoes_comunitarias.html':
                  icone_inicio.setAttribute('src', './images/footer-icone-inicio-active.svg')
                  icone_calendario.setAttribute('src', './images/footer-icone-calendario.svg')
                  icone_avisos.setAttribute('src', './images/footer-icone-avisos.svg')
                  icone_perfil.setAttribute('src', './images/footer-icone-perfil.svg')

                  break;

              case '/frontend/tela_calendario.html':
                  icone_inicio.setAttribute('src', './images/footer-icone-inicio.svg')
                  icone_calendario.setAttribute('src', './images/footer-icone-calendario-active.svg')
                  icone_avisos.setAttribute('src', './images/footer-icone-avisos.svg')
                  icone_perfil.setAttribute('src', './images/footer-icone-perfil.svg')

                  break;

              case '/frontend/tela_avisos.html':
                  icone_inicio.setAttribute('src', './images/footer-icone-inicio.svg')
                  icone_calendario.setAttribute('src', './images/footer-icone-calendario.svg')
                  icone_avisos.setAttribute('src', './images/footer-icone-avisos-active.svg')
                  icone_perfil.setAttribute('src', './images/footer-icone-perfil.svg')

                  break;

              case '/frontend/tela_meu_perfil.html':
                  icone_inicio.setAttribute('src', './images/footer-icone-inicio.svg')
                  icone_calendario.setAttribute('src', './images/footer-icone-calendario.svg')
                  icone_avisos.setAttribute('src', './images/footer-icone-avisos.svg')
                  icone_perfil.setAttribute('src', './images/footer-icone-perfil-active.svg')
                  
                  break;

              default:
                  break;

          }
        }
      });
    }
  }
}

// Inicializa o carregamento automático de componentes ao carregar o script
loadAllComponents();

function controlarCadastroAvisosEventos(element) {

  const container = element.querySelector('#container-principal');

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

  let modalAtual = null;

  function abrirModal(tipo) {
  modalAtual = tipo;

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
    if (tipo === 'detalhes-evento') botaoFooter.innerText = 'Confirmar Presença';
  }

  // mostrar seção certa
  if (tipo === 'criar-evento') criarEvento.style.display = 'block';
  if (tipo === 'criar-aviso') criarAviso.style.display = 'block';
  if (tipo === 'adicionar-mobilizadora') adicionarMobilizadora.style.display = 'block';
  if (tipo === 'detalhes-evento') detalhesEvento.style.display = 'block';
}

  // para criar um novo evento (página de ações comunitárias)
const nome_evento = element.querySelector('#nome-evento')
const tipo_evento = element.querySelector('#tipo-evento')
const data_evento = element.querySelector('#data')
const horario_evento = element.querySelector('#horario')
const local_evento = element.querySelector('#local-evento')
const descricao_evento = element.querySelector('#descricao-novo-evento')

// para criar novo aviso (página de perfil)
const evento_escolhido = element.querySelector('#tipo-evento-ja-existente')
const mensagem_aviso_novo = element.querySelector('#descricao-novo-aviso')

// para adicionar mobilizadora (página de perfil)
const telefone_mobilizadora = element.querySelector('#telefone-mobilizadora')


// vamos usar o botaoFooter, declarado no começo do documento.

botaoFooter.addEventListener('click', () => {
  
  switch (modalAtual) {
              case 'criar-evento':
                  const novo_evento = {
                    nome_evento_value: nome_evento.value,
                    tipo_evento_value: tipo_evento.value,
                    data_evento_value: data_evento.value,
                    horario_evento_value: horario_evento.value,
                    local_evento_value: local_evento.value,
                    descricao_evento_value: descricao_evento.value
                  }

                  break;

              case 'criar-aviso':
                  const novo_aviso = {
                    evento_escolhido_value: evento_escolhido.value,
                    mensagem_aviso_novo_value: mensagem_aviso_novo.value
                  }

                  break;

              case 'adicionar-mobilizadora':
                  const telefone_mobilizadora_value = telefone_mobilizadora.value
                  
                  break;

              default:
                  break;
  }
})

  function fecharModal() {
    container.style.display = 'none';

    criarEvento.style.display = 'none';
    criarAviso.style.display = 'none';
    adicionarMobilizadora.style.display = 'none';
    detalhesEvento.style.display = 'none';

    document.body.style.overflow = 'auto';
  }


  // BOTÃO X
  if (botaoFechar) {
    botaoFechar.addEventListener('click', fecharModal);
  }


  // BOTÃO AZUL
  const botaoAzul = document.getElementById('botao_azul');
  if (botaoAzul) {
    botaoAzul.addEventListener('click', () => abrirModal('criar-aviso'));
  }

  // BOTÃO VERMELHO
  const botaoVermelho = document.getElementById('botao_vermelho');
  if (botaoVermelho) {
    botaoVermelho.addEventListener('click', () => abrirModal('adicionar-mobilizadora'));
  }

  // BOTÃO +
  // ⚠️ IMPORTANTE: está fora do componente, então usamos document
  const botaoAdicionarEvento = document.querySelector('[style*="icone-adicionar-evento"]') 
    || document.querySelector('button img[src*="icone-adicionar-evento"]')?.parentElement;

  if (botaoAdicionarEvento) {
    botaoAdicionarEvento.addEventListener('click', () => abrirModal('criar-evento'));
  }


  const pagina = window.location.pathname;
  // ESCONDE O BOTÃO DE AVISO NO MODAL NA TELA DE PERFIL
if (pagina.includes('tela_meu_perfil')) {
  if (botaoAviso) {
    botaoAviso.style.display = 'none';
  }
}

document.addEventListener('click', (e) => {
  const evento = e.target.closest('.conteudo');

  if (!evento) return;

  // evita clicar em botões internos
  if (e.target.closest('button')) return;

  abrirModal('detalhes-evento');
});

}


