console.log("JavaScript chargé - école");

const socket = io();

window.onload = function() {
  const btnInscrire = document.getElementById('btnInscrire');
  const listeEnfants = document.getElementById('listeEnfants');
  const selectEnfant = document.getElementById('selectEnfant');
  const btnEnvoyer = document.getElementById('btnEnvoyerMessage');
  const inputMessage = document.getElementById('inputMessage');
  const messagesDiv = document.getElementById('messages');

  // Inscrire un enfant
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
      // Ajouter à la liste affichée
      const li = document.createElement('li');
      li.textContent = `${data.nom} (ID: ${data.id})`;
      listeEnfants.appendChild(li);

      // Ajouter dans le select pour envoyer message
      const option = document.createElement('option');
      option.value = data.id;
      option.textContent = `${data.nom} (${data.id})`;
      selectEnfant.appendChild(option);

      document.getElementById('nomEnfant').value = '';
    })
    .catch(error => {
      console.error('Erreur:', error);
      alert("Erreur lors de l'inscription.");
    });
  });

  // Envoyer un message en temps réel
  btnEnvoyer.addEventListener('click', function() {
    const idEnfant = selectEnfant.value;
    const message = inputMessage.value.trim();

    if (!idEnfant) {
      alert("Merci de choisir un enfant.");
      return;
    }
    if (message === '') {
      alert("Merci d'écrire un message.");
      return;
    }

    socket.emit('envoyer_message', {
      id: idEnfant,
      message: message,
      emetteur: 'ecole',
      destinataire: 'parent'
    });

    inputMessage.value = '';
  });

  // Rejoindre room quand enfant sélectionné (pour recevoir messages en temps réel)
  selectEnfant.addEventListener('change', function() {
    const idEnfant = selectEnfant.value;
    if (idEnfant) {
      socket.emit('join', { id: idEnfant });
      messagesDiv.innerHTML = ''; // vider ancien message affiché
    }
  });

  // Afficher les messages reçus en temps réel
  socket.on('nouveau_message', function(data) {
    if (!data.message) return;
    const p = document.createElement('p');
    p.textContent = `[${data.emetteur}] : ${data.message}`;
    messagesDiv.appendChild(p);
    messagesDiv.scrollTop = messagesDiv.scrollHeight; // scroll vers le bas
  });

  socket.on('status', function(data) {
    console.log(data.msg);
  });

  socket.on('erreur', function(data) {
    alert('Erreur: ' + data.msg);
  });
};

