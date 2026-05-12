window.addEventListener('load', async () => {

  const eventos = [
    {
      mes: 'ABR',
      dia: '16',
      tipo_evento: 'Reunião',
      confirmado: 'Você confirmou',
      titulo: 'Reunião do Conselho Comunitário',
      horario: '14:00',
      local: 'Centro Comunitário Parelheiros',
      confirmados: '12 pessoas confirmadas',
      organizador: 'Luiza'
    },

    {
      mes: 'ABR',
      dia: '20',
      tipo_evento: 'Oficina',
      confirmado: 'Evento aberto',
      titulo: 'Oficina de Capacitação',
      horario: '09:00',
      local: 'CEU Parelheiros',
      confirmados: '20 pessoas confirmadas',
      organizador: 'Fernanda'
    },

    {
      mes: 'MAI',
      dia: '03',
      tipo_evento: 'Mutirão',
      confirmado: 'Você confirmou',
      titulo: 'Mutirão Comunitário',
      horario: '08:30',
      local: 'Praça Central',
      confirmados: '35 pessoas confirmadas',
      organizador: 'Carlos'
    }
  ];

  const mount = document.getElementById('lista-avisos');

  mount.innerHTML = '';

  for (let evento of eventos) {
    mount.appendChild(
      await make('componenteEventoDetalhado', evento)
    );
  }

});