async function loadProfile() {
  const response = await fetch("http://localhost:5000/api/user/me");
  const data = await response.json();

  document.getElementById("nome").innerText = data.name;
  document.getElementById("numero_eventos_criou").innerText = data.usuaria_criou_n_eventos;
  document.getElementById("numero_eventos_participou").innerText = data.usuaria_participou_n_eventos;
}

loadProfile();