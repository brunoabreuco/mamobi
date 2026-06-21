(async () => {

  const REDIRECT_APOS_LOGIN = '/tela_acoes_comunitarias.html';

  // ============================================================
  // UTILITÁRIOS DE UI
  // ============================================================
  function mostrarErro(id, mensagem) {
    const el = document.getElementById(id);
    if (el) el.textContent = mensagem;
  }
  function limparErro(id) {
    const el = document.getElementById(id);
    if (el) el.textContent = '';
  }
  function toE164(phoneFormatado) {
    const digits = phoneFormatado.replace(/\D/g, '');
    return '+55' + digits;
  }
  function formatarTelefone(value) {
    let v = value.replace(/\D/g, '').slice(0, 11);
    if (v.length > 0) v = '(' + v;
    if (v.length > 3) v = v.slice(0, 3) + ') ' + v.slice(3);
    if (v.length > 10) v = v.slice(0, 10) + '-' + v.slice(10);
    return v;
  }

  // ============================================================
  // NAVEGAÇÃO ENTRE ETAPAS
  // ============================================================
  const etapas = document.querySelectorAll('section');
  let etapaAtual = 0;
  function mostrarEtapa(index) {
    etapas.forEach((etapa, i) => {
      etapa.style.display = i === index ? 'block' : 'none';
    });
  }
  mostrarEtapa(etapaAtual);

  // ============================================================
  // ESTADO
  // ============================================================
  let telefoneE164 = '';
  // 'otp' | 'google' — determina qual campo extra mostrar na etapa de perfil
  let loginProvider = 'otp';

  // ============================================================
  // ETAPA DE PERFIL: decide qual campo extra exibir
  // ============================================================
  function configurarEtapaPerfil() {
    const campoTelefone = document.getElementById('campo-telefone-extra');
    const campoEmail    = document.getElementById('campo-email-extra');
    if (loginProvider === 'google') {
      campoTelefone.style.display = 'block';
      campoEmail.style.display    = 'none';
    } else {
      campoEmail.style.display    = 'block';
      campoTelefone.style.display = 'none';
    }

    // Máscara no campo de telefone extra
    const inputTelExtra = document.getElementById('phone-extra');
    inputTelExtra.addEventListener('input', () => {
      inputTelExtra.value = formatarTelefone(inputTelExtra.value);
      limparErro('erro-perfil');
    });
  }

  // ============================================================
  // GOOGLE OAUTH VIA SUPABASE
  // ============================================================
  let supabaseClient = null;

async function inicializarSupabase() {
  try {
    const config = await apiGet('/api/config');
    if (!config.supabase_url || !config.supabase_anon_key) return;
    supabaseClient = window.supabase.createClient(config.supabase_url, config.supabase_anon_key);
  } catch (e) { console.error('inicializarSupabase falhou:', e); }
}

  await inicializarSupabase();

  // Trata retorno do redirect OAuth.
  // getSession() não troca o code PKCE automaticamente; onAuthStateChange
  // dispara com a sessão completa após o SDK concluir a troca internamente.
  if (supabaseClient) {
    const GOOGLE_SVG = `
      <span class="botao-google-icon">
        <svg width="16" height="16" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
          <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z" fill="#4285F4"/>
          <path d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.258c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332C2.438 15.983 5.482 18 9 18z" fill="#34A853"/>
          <path d="M3.964 10.707c-.18-.54-.282-1.117-.282-1.707s.102-1.167.282-1.707V4.961H.957C.347 6.175 0 7.548 0 9s.348 2.825.957 4.039l3.007-2.332z" fill="#FBBC05"/>
          <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0 5.482 0 2.438 2.017.957 4.961L3.964 6.293C4.672 4.166 6.656 3.58 9 3.58z" fill="#EA4335"/>
        </svg>
      </span>
      Entrar com Google`;

    // Captura antes do SDK limpar a URL — Supabase v2 PKCE usa ?code=,
    // implicit flow usa #access_token= no hash
    const isOAuthCallback = new URLSearchParams(window.location.search).has('code')
                         || window.location.hash.includes('access_token');

    supabaseClient.auth.onAuthStateChange(async (event, session) => {
      if (!isOAuthCallback) return;
      if (event !== 'SIGNED_IN' || !session?.access_token) return;

      const btnGoogle = document.getElementById('btn-google');
      if (btnGoogle) { btnGoogle.disabled = true; btnGoogle.textContent = 'Autenticando...'; }

      try {
        const data = await apiPost('/auth/google/exchange', { supabase_token: session.access_token });
        tokenStorage.salvar(data);

        const perfil = await apiGet('/api/me');
        if (perfil.full_name && perfil.full_name.trim() !== '' && perfil.phone) {
          window.location.href = REDIRECT_APOS_LOGIN;
          return;
        }
        loginProvider = 'google';
        configurarEtapaPerfil();
        etapaAtual = 2;
        mostrarEtapa(etapaAtual);
      } catch (err) {
        mostrarErro('erro-google', '' + err);
        if (btnGoogle) { btnGoogle.disabled = false; btnGoogle.innerHTML = GOOGLE_SVG; }
        history.replaceState(null, '', window.location.pathname);
      }
    });
  }

  const btnGoogle = document.getElementById('btn-google');
  if (btnGoogle) {
    btnGoogle.addEventListener('click', async () => {
      if (!supabaseClient) {
        mostrarErro('erro-google', 'Login com Google não disponível no momento.');
        return;
      }
      limparErro('erro-google');
      btnGoogle.disabled = true;
      btnGoogle.textContent = 'Redirecionando...';
      const { error } = await supabaseClient.auth.signInWithOAuth({
        provider: 'google',
        options: { redirectTo: window.location.origin + '/tela-cadastro.html' },
      });
      if (error) {
        mostrarErro('erro-google', 'Não foi possível iniciar o login com Google.');
        btnGoogle.disabled = false;
        btnGoogle.textContent = 'Entrar com Google';
      }
    });
  }

  // ============================================================
  // ETAPA 1 — TELEFONE
  // ============================================================
  const inputTelefone = document.getElementById('phone');
  const botaoTelefone = document.getElementById('btn-continuar');

  botaoTelefone.disabled = true;

  inputTelefone.addEventListener('input', () => {
    inputTelefone.value = formatarTelefone(inputTelefone.value);
    limparErro('erro-telefone');
    const numeros = inputTelefone.value.replace(/\D/g, '');
    botaoTelefone.disabled = !(numeros.length === 10 || numeros.length === 11);
  });

  botaoTelefone.addEventListener('click', async () => {
    limparErro('erro-telefone');
    telefoneE164 = toE164(inputTelefone.value);
    const textoOriginal = botaoTelefone.textContent;
    botaoTelefone.disabled = true;
    botaoTelefone.textContent = 'Aguarde...';
    try {
      await apiPost('/auth/otp/request', { phone: telefoneE164 });
      document.getElementById('telefone-display').textContent = inputTelefone.value;
      etapaAtual = 1;
      mostrarEtapa(etapaAtual);
      iniciarCooldownReenviar();
    } catch (err) {
      mostrarErro('erro-telefone', '' + err);
      const numeros = inputTelefone.value.replace(/\D/g, '');
      botaoTelefone.disabled = !(numeros.length === 10 || numeros.length === 11);
      botaoTelefone.textContent = textoOriginal;
    }
  });

  // ============================================================
  // ETAPA 2 — CÓDIGO SMS
  // ============================================================
  const inputsCodigo = document.querySelectorAll('.input-codigo');
  const botaoReenviar = document.querySelector('.botao-reenviar');
  let verificandoCodigo = false;
  let timerCooldown = null;

  function codigoCompleto() { return Array.from(inputsCodigo).every(i => i.value.trim().length === 1); }
  function getCodigo() { return Array.from(inputsCodigo).map(i => i.value.trim()).join(''); }
  function limparInputsCodigo() { inputsCodigo.forEach(i => (i.value = '')); inputsCodigo[0].focus(); }
  function bloquearInputsCodigo(b) { inputsCodigo.forEach(i => (i.disabled = b)); }

  inputsCodigo.forEach((input, index) => {
    input.addEventListener('input', async () => {
      input.value = input.value.replace(/\D/g, '').slice(0, 1);
      if (input.value.length === 1 && inputsCodigo[index + 1]) inputsCodigo[index + 1].focus();
      if (!codigoCompleto() || verificandoCodigo) return;

      limparErro('erro-codigo');
      verificandoCodigo = true;
      bloquearInputsCodigo(true);
      await new Promise(resolve => setTimeout(resolve, 300));

      try {
        const data = await apiPost('/auth/otp/verify', { phone: telefoneE164, code: getCodigo() });
        tokenStorage.salvar(data);

        const perfil = await apiGet('/api/me');
        if (perfil.full_name && perfil.full_name.trim() !== '' && perfil.email) {
          window.location.href = REDIRECT_APOS_LOGIN;
          return;
        }
        // Perfil incompleto: pede e-mail
        loginProvider = 'otp';
        configurarEtapaPerfil();
        etapaAtual = 2;
        mostrarEtapa(etapaAtual);
      } catch (err) {
        mostrarErro('erro-codigo', '' + err);
        limparInputsCodigo();
        bloquearInputsCodigo(false);
        verificandoCodigo = false;
      }
    });

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Backspace' && !input.value && inputsCodigo[index - 1]) inputsCodigo[index - 1].focus();
    });

    input.addEventListener('paste', (e) => {
      e.preventDefault();
      const colado = (e.clipboardData || window.clipboardData).getData('text').replace(/\D/g, '');
      [...colado].slice(0, inputsCodigo.length - index).forEach((digit, i) => {
        if (inputsCodigo[index + i]) inputsCodigo[index + i].value = digit;
      });
      const proximoVazio = [...inputsCodigo].find(i => !i.value);
      if (proximoVazio) proximoVazio.focus();
      else inputsCodigo[inputsCodigo.length - 1].focus();
      inputsCodigo[index].dispatchEvent(new Event('input'));
    });
  });

  function iniciarCooldownReenviar() {
    const COOLDOWN_S = 60;
    let restante = COOLDOWN_S;
    clearInterval(timerCooldown);
    botaoReenviar.disabled = true;
    botaoReenviar.textContent = `Reenviar código (${restante}s)`;
    timerCooldown = setInterval(() => {
      restante -= 1;
      botaoReenviar.textContent = `Reenviar código (${restante}s)`;
      if (restante <= 0) {
        clearInterval(timerCooldown);
        botaoReenviar.disabled = false;
        botaoReenviar.textContent = 'Reenviar código';
      }
    }, 1000);
  }

  botaoReenviar.addEventListener('click', async () => {
    limparErro('erro-codigo');
    const textoOriginal = botaoReenviar.textContent;
    botaoReenviar.disabled = true;
    botaoReenviar.textContent = 'Enviando...';
    try {
      await apiPost('/auth/otp/request', { phone: telefoneE164 });
      limparInputsCodigo();
      verificandoCodigo = false;
      iniciarCooldownReenviar();
    } catch (err) {
      mostrarErro('erro-codigo', '' + err);
      botaoReenviar.disabled = false;
      botaoReenviar.textContent = textoOriginal;
    }
  });

  // ============================================================
  // ETAPA 3 — NOME, CAMPO EXTRA E BAIRRO
  // ============================================================
  const botaoFinal = document.querySelector('.etapa04-nome-bairro a');
  const inputNome  = document.getElementById('name');
  const selectBairro = document.querySelector('.etapa04-nome-bairro select');
  let enviandoPerfil = false;

  botaoFinal.addEventListener('click', async (e) => {
    e.preventDefault();
    if (enviandoPerfil) return;
    limparErro('erro-perfil');

    const nome   = inputNome.value.trim();
    const bairro = selectBairro.value;

    if (!nome) { mostrarErro('erro-perfil', 'Informe seu nome para continuar.'); return; }

    const payload = { full_name: nome, neighborhood: bairro };

    if (loginProvider === 'google') {
      const phoneExtra = document.getElementById('phone-extra').value;
      const numeros = phoneExtra.replace(/\D/g, '');
      if (numeros.length < 10) { mostrarErro('erro-perfil', 'Informe um número de celular válido.'); return; }
      payload.phone = toE164(phoneExtra);
    } else {
      const emailExtra = document.getElementById('email-extra').value.trim();
      if (!emailExtra || !emailExtra.includes('@')) { mostrarErro('erro-perfil', 'Informe um e-mail válido.'); return; }
      payload.email = emailExtra;
    }

    enviandoPerfil = true;
    const textoOriginal = botaoFinal.textContent;
    botaoFinal.textContent = 'Aguarde...';
    botaoFinal.style.pointerEvents = 'none';

    try {
      await apiPatch('/api/me', payload);
      window.location.href = REDIRECT_APOS_LOGIN;
    } catch (err) {
      // 409 = telefone ou e-mail já pertence a outra conta
      const msg = String(err).includes('409') || String(err).toLowerCase().includes('conflict')
        ? loginProvider === 'google'
          ? 'Este telefone já está cadastrado. Entre pelo número de celular.'
          : 'Este e-mail já está cadastrado. Entre pelo Google com este endereço.'
        : '' + err;
      mostrarErro('erro-perfil', msg);
      botaoFinal.textContent = textoOriginal;
      botaoFinal.style.pointerEvents = '';
      enviandoPerfil = false;
    }
  });

})();