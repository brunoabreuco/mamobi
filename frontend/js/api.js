// ============================================================
// GERENCIAMENTO DE TOKENS
// ============================================================
const tokenStorage = {
  salvar(data) {
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
  },
  getAccess() {
    return localStorage.getItem('access_token');
  },
};

// ============================================================
// SERVIÇO DE API
// ============================================================

async function apiRequest(method, path, body, query_params) {
  let append = '';
  if (query_params !== undefined) {
    append = '?' + new URLSearchParams(query_params).toString();
  }
  let headers = {};
  const token = tokenStorage.getAccess();
  if (token) {
    headers['Authorization'] = `Bearer ${tokenStorage.getAccess()}`;
  }
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }
  let requestOptions = {
    method: method,
    headers: headers,
  };
  if (body !== undefined) {
    requestOptions.body = JSON.stringify(body);
  }
  const res = await fetch(`${path}${append}`, requestOptions);
  
  // 🔹 Verifica se a resposta tem conteúdo antes de parsear JSON
  const contentLength = res.headers.get('content-length');
  let data = null;
  if (contentLength && parseInt(contentLength) > 0) {
    data = await res.json();
  } else {
    // Para respostas sem corpo (ex: 204 No Content), apenas define data como null
    data = null;
  }
  
  // 🔹 Passa os dados para o tratador de erro (que agora deve lidar com null)
  lidarComErro(res, data);
  return data;
}

async function lidarComErro(res, data) {
  if (!res.ok) {
    let erro = 'Erro desconhecido';
    if (data && data.error) {
      erro = data.error;
    } else if (data && data.errors) {
      erro = '';
      for (let e of data.errors) {
        erro += e;
        erro += ';';
      }
    }
    const err = new Error(erro);
    err.status = res.status;
    err.code = erro;
    throw err;
  }
}

async function apiPost(path, body) {
  return apiRequest('POST', path, body, undefined);
}

async function apiPatch(path, body) {
  return apiRequest('PATCH', path, body, undefined);
}

async function apiGet(path, query_params) {
  return apiRequest('GET', path, undefined, query_params);
}

async function apiDelete(path, query_params) {
  return apiRequest('DELETE', path, undefined, query_params);
}

function dateTimeParseUTC(isoString) {
  const utcString = isoString.endsWith('Z') ? isoString : `${isoString}Z`;
  const date = new Date(utcString);
  return date;
}

// Função única para formatar data/hora completa em pt-BR (24h)
function formatToLocalDateTime(isoString) {
  const date = dateTimeParseUTC(isoString);
  return new Intl.DateTimeFormat('pt-BR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: false,
  }).format(date);
}

// Função para formatar apenas a data (curta) em pt-BR
function formatToLocalDate(isoString) {
  const date = dateTimeParseUTC(isoString);
  return new Intl.DateTimeFormat('pt-BR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  }).format(date);
}

// ============================================================
// UTILITÁRIOS DE UI
// ============================================================

// criar mensagem de erro (overlay fixo)
function mostrar_msg_erro(a, b) {
  // Remove qualquer erro anterior
  const anterior = document.getElementById('tela_escura_erro');
  if (anterior) anterior.remove();

  // Impede rolagem da página
  document.body.style.overflow = 'hidden';

  const fundo = document.createElement('div');
  fundo.id = 'tela_escura_erro';
  fundo.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background-color: rgba(0, 0, 0, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 99999;
    padding: 20px;
    box-sizing: border-box;
  `;

  fundo.innerHTML = `
    <div id="caixa_erro" style="
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      align-items: center;
      background-color: #f5ede9;
      width: 90%;
      max-width: 800px;
      padding: 40px 20px 30px 20px;
      border-radius: 30px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.3);
      max-height: 90vh;
      overflow-y: auto;
    ">
      <span class="texto_erro" style="
        font-size: 28px;
        font-weight: 600;
        font-family: 'Inter', sans-serif;
        text-align: center;
        word-break: break-word;
      ">${a}</span>
      <span class="texto_erro" style="
        font-size: 20px;
        font-weight: 400;
        font-family: 'Inter', sans-serif;
        text-align: center;
        color: #555;
        margin-top: 8px;
        word-break: break-word;
      ">${b}</span>
      <button id="botao_erro_ok" style="
        background-color: #00636A;
        margin-top: 30px;
        border: none;
        border-radius: 20px;
        width: 140px;
        height: 56px;
        font-size: 20px;
        font-weight: 700;
        font-family: 'Inter', sans-serif;
        color: #FFFFFF;
        cursor: pointer;
        transition: transform 0.2s ease;
      "
      onmouseover="this.style.transform='scale(1.05)'"
      onmouseout="this.style.transform='scale(1)'"
      >OK</button>
    </div>
  `;

  document.body.appendChild(fundo);

  const botao_ok = document.getElementById('botao_erro_ok');
  botao_ok.addEventListener('click', () => {
    fundo.remove();
    // Restaura a rolagem
    document.body.style.overflow = '';
  });

  // Fechar ao clicar fora da caixa (opcional)
  fundo.addEventListener('click', (e) => {
    if (e.target === fundo) {
      fundo.remove();
      document.body.style.overflow = '';
    }
  });
}