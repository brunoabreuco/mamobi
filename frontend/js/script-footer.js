function configurarFooter() {
    var nav = document.querySelector('.c-footer nav');
    if (!nav) {
        document.addEventListener('componentsReady', function handler() {
            document.removeEventListener('componentsReady', handler);
            configurarFooter();
        });
        return;
    }

    var mapaIndice = {
        'tela_acoes_comunitarias.html': 0,
        'tela_calendario.html':         1,
        'tela_avisos.html':             2,
        'tela_meu_perfil.html':         3
    };

    var paginaAtual = window.location.pathname.split('/').pop();
    var indice = mapaIndice[paginaAtual];
    if (indice === undefined) {
        console.warn('Página não mapeada:', paginaAtual);
        return;
    }

    var links = nav.querySelectorAll('a');

    links.forEach(function(link, i) {
        link.classList.toggle('nav-active', i === indice);
    });

    var oldPill = nav.querySelector('.nav-pill');
    if (oldPill) oldPill.remove();

    var pill = document.createElement('div');
    pill.className = 'nav-pill';
    pill.setAttribute('aria-hidden', 'true');
    nav.insertAdjacentElement('afterbegin', pill);

    // 🔹 DELAY DE 100ms PARA GARANTIR LAYOUT ESTÁVEL
    setTimeout(function() {
        requestAnimationFrame(function() {
            var navRect  = nav.getBoundingClientRect();
            var linkRect = links[indice].getBoundingClientRect();
            var larguraPill = linkRect.width + 20;
            var xAtual = linkRect.left - navRect.left - 10;
            var xAnterior = parseFloat(sessionStorage.getItem('footer-pill-x'));

            pill.style.width = larguraPill + 'px';
            pill.style.transitionDuration = '0s';
            pill.style.transform = 'translateX(' + (isNaN(xAnterior) ? xAtual : xAnterior) + 'px)';

            void pill.offsetHeight;

            requestAnimationFrame(function() {
                pill.style.transitionDuration = '';
                pill.style.transform = 'translateX(' + xAtual + 'px)';
                sessionStorage.setItem('footer-pill-x', String(xAtual));
            });
        });
    }, 100);
}

document.addEventListener('DOMContentLoaded', configurarFooter);
document.addEventListener('componentsReady', configurarFooter);