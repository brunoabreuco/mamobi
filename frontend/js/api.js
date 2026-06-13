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
  }
  if (body !== undefined) {
    requestOptions.body = JSON.stringify(body);
  }
  const res = await fetch(`${path}${append}`, requestOptions);
  const data = await res.json();
  lidarComErro(res, data);
  return data;
}

async function lidarComErro(res, data) {
  if (!res.ok) {
    let erro = 'Erro desconhecido';
    if (data.error) {
      erro = data.error;
    } else if (data.errors) {
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

function formatToLocalDate(isoString, locale = undefined) {
  const date = dateTimeParseUTC(isoString);
  return new Intl.DateTimeFormat(locale, {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  }).format(date);
}

function formatToLocalDateTime(isoString, locale = undefined) {
  const date = dateTimeParseUTC(isoString);
  return new Intl.DateTimeFormat(locale, {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit'
  }).format(date);
}
// ============================================================
// UTILITÁRIOS DE UI
// ============================================================

// criar mensagem de erro
function mostrar_msg_erro(a, b) {
  const fundo = document.createElement('div');

  fundo.innerHTML = `<div id="tela_escura_erro" style="display: flex; align-items: center; width: 100vw; height: 100vh; background-color: rgba(0, 0, 0, 0.6);">
  <div id="caixa_erro" style="margin: 0 auto; display: flex; flex-direction: column; align-items: center; background-color: #f5ede9; width: 800px; height: 250px; padding: 50px 10px 0px 10px; border-radius: 30px;">
      <span class="texto_erro" style="font-size: 35px; font-weight: 600; font-family: 'Inter', sans-serif">${a}</span>
      <span class="texto_erro" style="font-size: 35px; font-weight: 600; font-family: 'Inter', sans-serif">${b}</span>
      <button id="botao_erro_ok" style="background-color: #00636A; margin-top: 30px; border: none; border-radius: 20px; width: 160px; height: 80px; font-size: 25px; font-weight: 700; font-family: 'Inter', sans-serif; color: #FFFFFF">OK</button>
  </div>
  </div>`;

  document.body.appendChild(fundo);

  const botao_ok = document.getElementById('botao_erro_ok');

  botao_ok.addEventListener('click', () => {
    fundo.remove();
  });
}
