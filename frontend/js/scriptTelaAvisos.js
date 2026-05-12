async function carregarAvisos() {
  const avisos = [
    {
      "imagem": "./images/icone-duas_pessoas_verde.svg",
      "titulo": "12 pessoas confirmadas",
      "mensagem": "A Reunião do Conselho Comunitário já tem 12 participantes confirmados",
      "quando": "Há 1 dia"
    },
    {
      "imagem": "./images/icone_calendario_verde.svg",
      "titulo": "Novo evento criado",
      "mensagem": "Maria Silva criou o evento “Reunião do Conselho Comunitário”",
      "quando": "Há 1 dia"
    },
    {
      "imagem": "./images/icone_calendario_verde.svg",
      "titulo": "Lembrete: Mutirão amanhã",
      "mensagem": "Não esqueça do Mutirão de Limpeza da Praça amanhã às 8h.",
      "quando": "Há 1 dia"
    }

  ];
  const mount = document.getElementById('lista-avisos');
  mount.innerHTML = "";
  for (let aviso of avisos) {
    mount.appendChild(await make('componenteAviso', aviso));
  }
}

carregarAvisos();
