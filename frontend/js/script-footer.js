function configurarFooter() {
    var nav = document.querySelector('.c-footer nav');
    if (!nav) return;

    var mapaIndice = {
        'tela_acoes_comunitarias.html': 0,
        'tela_calendario.html':         1,
        'tela_avisos.html':             2,
        'tela_meu_perfil.html':         3
    };

    var paginaAtual = window.location.pathname.split('/').pop();
    var indice = mapaIndice[paginaAtual];
    if (indice === undefined) return;

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

    requestAnimationFrame(function() {
        var navRect  = nav.getBoundingClientRect();
        var linkRect = links[indice].getBoundingClientRect();
        var xAtual   = linkRect.left - navRect.left;
        var xAnterior = parseFloat(sessionStorage.getItem('footer-pill-x'));

        // Largura do link + 20px de folga (10px de cada lado)
        var larguraPill = linkRect.width + 20;
        pill.style.width = larguraPill + 'px';
        // Ajusta a posição X para manter o pill centralizado sob o link
        var xAjustado = xAtual - 10; // desloca 10px para a esquerda
        pill.style.transitionDuration = '0s';
        pill.style.transform = 'translateX(' + (isNaN(xAnterior) ? xAjustado : xAnterior) + 'px)';

        void pill.offsetHeight;

        requestAnimationFrame(function() {
            pill.style.transitionDuration = '';
            pill.style.transform = 'translateX(' + xAjustado + 'px)';
            sessionStorage.setItem('footer-pill-x', String(xAjustado));
        });
    });
}

document.addEventListener('DOMContentLoaded', configurarFooter);