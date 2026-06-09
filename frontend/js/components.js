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

  if (spec === 'header') {
    configurarHeader(element);
  }

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
          configurarFooter()
        }
      });
    }
  }
}

// Inicializa o carregamento automático de componentes ao carregar o script
loadAllComponents();


// tela de perfil
async function loadProfile() {
  const response = await fetch("http://localhost:5000/api/user/me");
  const data = await response.json();

  document.getElementById("nome").innerText = data.name;
  document.getElementById("numero_eventos_criou").innerText = data.usuaria_criou_n_eventos;
  document.getElementById("numero_eventos_participou").innerText = data.usuaria_participou_n_eventos;
}

loadProfile();
