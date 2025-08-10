
console.log("JavaScript chargé - école");

// Connexion au serveur Socket.IO
const socket = io();

window.onload = function() {
  const btnInscrire = document.getElementById('btnInscrire');
  const listeEnfants = document.getElementById('listeEnfants');

  // Ajoute un enfant dans la liste affichée (bouton avec id en petit dessous)
  function ajouterEnfant(id, nom) {
    const li = document.createElement('li');

    const btn = document.createElement('button');
    btn.textContent = nom;
    btn.classList.add('enfant-btn');
    btn.style.padding = "8px 15px";
    btn.style.cursor = "pointer";
    btn.style.borderRadius = "6px";
    btn.style.border = "1px solid #007BFF";
    btn.style.backgroundColor = "#f0f4ff";
    btn.style.color = "#003366";
    btn.style.fontWeight = "bold";
    btn.style.fontSize = "1.1em";
    btn.style.display = "block";
    btn.style.width = "100%";
    btn.style.textAlign = "left";

    btn.addEventListener('mouseover', () => btn.style.backgroundColor = '#d0e1ff');
    btn.addEventListener('mouseout', () => btn.style.backgroundColor = '#f0f4ff');

    btn.addEventListener('click', () => {
      const message = prompt(`Envoyer un message à ${nom} (${id}):`);
      if (message && message.trim() !== '') {
        socket.emit('envoyer_message', { id_enfant: id, message: message.trim() });
        alert('Message envoyé !');
      }
    });

    const idPetit = document.createElement('small');
    idPetit.textContent = id.toLowerCase();
    idPetit.style.display = 'block';
    idPetit.style.color = '#555';
    idPetit.style.fontStyle = 'italic';
    idPetit.style.marginTop = '3px';

    li.appendChild(btn);
    li.appendChild(idPetit);
    li.style.listStyle = 'none';

    listeEnfants.appendChild(li);
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
};
