function configurarFooter() {

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