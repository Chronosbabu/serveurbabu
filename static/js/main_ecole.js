console.log("JavaScript chargé - école");

// Connexion au serveur Socket.IO
const socket = io();

// Chargement une fois la page prête
window.onload = function() {
  const btnInscrire = document.getElementById('btnInscrire');
  const listeEnfants = document.getElementById('listeEnfants');
  const selectEnfant = document.getElementById('selectEnfant');
  const btnEnvoyer = document.getElementById('btnEnvoyerMessage');
  const inputMessage = document.getElementById('inputMessage');
  const divMessages = document.getElementById('messages');

  // Ajoute un enfant dans la liste affichée et dans le select
  function ajouterEnfant(id, nom) {
    const li = document.createElement('li');
    li.textContent = `${nom} (ID: ${id})`;
    listeEnfants.appendChild(li);

    const option = document.createElement('option');
    option.value = id;
    option.textContent = `${nom} (${id})`;
    selectEnfant.appendChild(option);
  }

  // Inscription d'un nouvel enfant
  btnInscrire.addEventListener('click', function() {
    const nom = document.getElementById('nomEnfant').value.trim();
    if (nom === '') {
      alert('Merci de saisir le nom de l’enfant.');
      return;
    }

    fetch('/api/inscrire_enfant', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nom: nom })
    })
    .then(response => response.json())
    .then(data => {
      if (data.erreur) {
        alert(data.erreur);
        return;
      }
      ajouterEnfant(data.id, data.nom);
      document.getElementById('nomEnfant').value = '';
    })
    .catch(() => alert("Erreur lors de l'inscription."));
  });

  // Envoi d'un message à un enfant
  btnEnvoyer.addEventListener('click', function() {
    const idEnfant = selectEnfant.value;
    const message = inputMessage.value.trim();
    if (!idEnfant) {
      alert("Choisis un enfant.");
      return;
    }
    if (!message) {
      alert("Écris un message.");
      return;
    }
    socket.emit('envoyer_message', { id_enfant: idEnfant, message: message });
    inputMessage.value = '';
  });

  // Réception des messages en temps réel
  socket.on('nouveau_message', data => {
    const { id_enfant, message } = data;
    const p = document.createElement('p');
    p.textContent = `[${id_enfant}] : ${message}`;
    divMessages.appendChild(p);
    divMessages.scrollTop = divMessages.scrollHeight;
  });
};

