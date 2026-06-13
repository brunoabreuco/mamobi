async function reqGetEventos() {
  try {
    const res = await apiGet('/api/acoes');
    return res.data;
  } catch (err) {
    console.error('Erro ao buscar eventos:', err);
    mostrar_msg_erro('Erro ao buscar eventos:', "" + err);
  }
}

async function iniciarCalendario() {
  const eventos = await reqGetEventos();
  // espera o componente carregar no DOM
  while (
    !document.getElementById('monthYear') ||
    !document.getElementById('dates') ||
    !document.getElementById('prevBtn') ||
    !document.getElementById('nextBtn')
  ) {
    await new Promise(resolve => setTimeout(resolve, 50));
  }

  const monthYearElement = document.getElementById('monthYear');
  const datesElement = document.getElementById('dates');
  const prevBtn = document.getElementById('prevBtn');
  const nextBtn = document.getElementById('nextBtn');

  let currentDate = new Date();

  const updateCalendar = () => {
    const currentYear = currentDate.getFullYear();
    const currentMonth = currentDate.getMonth();

    const firstDay = new Date(currentYear, currentMonth, 1);
    const lastDay = new Date(currentYear, currentMonth + 1, 0);

    const totalDays = lastDay.getDate();
    const firstDayIndex = firstDay.getDay();
    const lastDayIndex = lastDay.getDay();

    const monthYearString = currentDate.toLocaleString('pt-BR', {
      month: 'long',
      year: 'numeric'
    });

    monthYearElement.textContent = monthYearString;

    let datesHTML = '';

    // dias do mês anterior
    for (let i = firstDayIndex; i > 0; i--) {
      const prevDate = new Date(currentYear, currentMonth, 0 - i + 1);

      datesHTML += `
        <div class="date inactive">
          ${prevDate.getDate()}
        </div>
      `;
    }

    // dias do mês atual
    for (let i = 1; i <= totalDays; i++) {
      const date = new Date(currentYear, currentMonth, i);

      const activeClass =
        date.toDateString() === new Date().toDateString()
          ? 'active'
          : '';

      let isAnEvent = false;
      for (let evt of eventos) {
        if (evt.event_datetime && dateTimeParseUTC(evt.event_datetime).toDateString() === date.toDateString()) {
          isAnEvent = true;
          break;
        }
      }
      const isAnEventClass = isAnEvent ? 'is-an-event' : '';

      datesHTML += `
        <div class="date ${activeClass} ${isAnEventClass}">
          ${i}
        </div>
      `;
    }

    // dias do próximo mês
    for (let i = 1; i <= 6 - lastDayIndex; i++) {
      const nextDate = new Date(currentYear, currentMonth + 1, i);

      datesHTML += `
        <div class="date inactive">
          ${nextDate.getDate()}
        </div>
      `;
    }

    datesElement.innerHTML = datesHTML;
  };

  async function updateNextEvents() {
    const mount = document.getElementById('proximos-eventos');

    mount.innerHTML = '';

    for (let evt of eventos) {
      mount.appendChild(
        await make('componenteproximosEventos', {
          data: formatToLocalDate(evt.event_datetime),
          desc: evt.title
        })
      );
    }
  }

  prevBtn.addEventListener('click', () => {
    currentDate.setMonth(currentDate.getMonth() - 1);
    updateCalendar();
  });

  nextBtn.addEventListener('click', () => {
    currentDate.setMonth(currentDate.getMonth() + 1);
    updateCalendar();
  });

  updateCalendar();
  await updateNextEvents();
}

iniciarCalendario();
