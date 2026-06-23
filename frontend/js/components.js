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

  if (spec === 'header' && typeof configurarHeader === 'function') {
    configurarHeader(element);
  }

  if (spec === 'componenteCadastroAvisosEventos' && typeof controlarCadastroAvisosEventos === 'function') {
    controlarCadastroAvisosEventos(element);
  }

  return element;
}

/**
 * Percorre o DOM em busca de elementos com o atributo 'data-spec' e os inicializa automaticamente.
 * Também extrai atributos 'data-prop-*' do elemento container para passar como props.
 */
async function loadAllComponents() {
  const elements = document.querySelectorAll('[data-spec]');
  const promises = [];

  for (let element of elements) {
    const spec = element.getAttribute('data-spec');
    let props = {};
    for (let attr of element.attributes) {
      if (attr.name.startsWith('data-prop-')) {
        props[attr.name.replace('data-prop-', '')] = attr.value;
      }
    }
    const p = make(spec, props).then(el => {
      element.innerHTML = '';
      element.appendChild(el);

      if (spec === 'footer' && typeof configurarFooter === 'function') {
        configurarFooter();
      }
    });

    promises.push(p);
  }

  await Promise.all(promises);
  document.dispatchEvent(new Event('componentsReady'));
}

document.addEventListener('DOMContentLoaded', loadAllComponents);