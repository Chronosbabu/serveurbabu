console.log("JavaScript chargé - école");

const socket = io();

window.onload = function() {
  const btnInscrire = document.getElementById('btnInscrire');
  const nomEnfantInput = document.getElementById('nomEnfant');
  const listeEnfants = document.getElementById('listeEnfants');
  const inputRecherche = document.getElementById('rechercheEnfant');
  const checkboxSelectTout = document.getElementById('selectTout');
  const textareaMessage = document.getElementById('messageEnfants');
  const btnEnvoyerMessage = document.getElementById('btnEnvoyerMessage');
  const zoneMessageDiv = document.getElementById('zoneMessage'); // Assure-toi que cette div existe dans le HTML

  let enfants = []; // tableau {id, nom}

  // Rafraîchir affichage enfants selon filtre et checkbox
  function afficherEnfants() {
    const filtre = inputRecherche.value.toLowerCase();
    listeEnfants.innerHTML = '';

    enfants.forEach(({id, nom}) => {
      if (nom.toLowerCase().includes(filtre) || id.toLowerCase().includes(filtre)) {
        const li = document.createElement('li');
        li.style.display = 'flex';
        li.style.alignItems = 'center';
        li.style.justifyContent = 'space-between';
        li.style.padding = '8px 12px';
        li.style.border = '1px solid #007BFF';
        li.style.borderRadius = '6px';
        li.style.backgroundColor = '#f0f4ff';

        const divNom = document.createElement('div');
        divNom.style.flexGrow = '1';

        const spanNom = document.createElement('span');
        spanNom.textContent = nom;
        spanNom.style.fontWeight = 'bold';
        spanNom.style.color = '#003366';
        spanNom.style.fontSize = '1.1em';

        const spanId = document.createElement('small');
        spanId.textContent = id.toLowerCase();
        spanId.style.display = 'block';
        spanId.style.fontStyle = 'italic';
        spanId.style.color = '#555';
        spanId.style.marginTop = '3px';

        divNom.appendChild(spanNom);
        divNom.appendChild(spanId);

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.classList.add('chk-enfant');
        checkbox.dataset.id = id;

        checkbox.addEventListener('change', () => {
          majZoneMessage();
          majCheckboxTout();
        });

        li.appendChild(divNom);
        li.appendChild(checkbox);

        listeEnfants.appendChild(li);
      }
    });
  }

  // Met à jour la zone message selon sélection enfants
  function majZoneMessage() {
    const coches = document.querySelectorAll('.chk-enfant:checked');
    if (coches.length > 0) {
      zoneMessageDiv.style.display = 'block';
    } else {
      zoneMessageDiv.style.display = 'none';
      textareaMessage.value = '';
    }
  }

  // Met à jour checkbox « tout sélectionner » selon sélection enfants
  function majCheckboxTout() {
    const total = document.querySelectorAll('.chk-enfant').length;
    const coches = document.querySelectorAll('.chk-enfant:checked').length;
    checkboxSelectTout.checked = (total > 0 && total === coches);
  }

  // Clic sur checkbox tout sélectionner
  checkboxSelectTout.addEventListener('change', () => {
    const cocher = checkboxSelectTout.checked;
    document.querySelectorAll('.chk-enfant').forEach(cb => {
      cb.checked = cocher;
    });
    majZoneMessage();
  });

  // Filtrage dynamique
  inputRecherche.addEventListener('input', afficherEnfants);

  // Envoyer message aux enfants sélectionnés
  btnEnvoyerMessage.addEventListener('click', () => {
    const message = textareaMessage.value.trim();
    if (!message) {
      alert("Écris un message.");
      return;
    }
    const coches = [...document.querySelectorAll('.chk-enfant:checked')];
    if (coches.length === 0) {
      alert("Sélectionne au moins un enfant.");
      return;
    }

    coches.forEach(cb => {
      const id = cb.dataset.id;
      socket.emit('envoyer_message', { id_enfant: id, message });
    });

    alert("Message envoyé aux enfants sélectionnés.");
    textareaMessage.value = '';
    checkboxSelectTout.checked = false;
    coches.forEach(cb => cb.checked = false);
    majZoneMessage();
  });

  // Ajouter enfant dans tableau et afficher
  function ajouterEnfant(id, nom) {
    enfants.push({id, nom});
    afficherEnfants();
  }

  // Inscription d'un enfant
  btnInscrire.addEventListener('click', () => {
    const nom = nomEnfantInput.value.trim();
    if (!nom) {
      alert("Merci de saisir le nom de l’enfant.");
      return;
    }

    fetch('/api/inscrire_enfant', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ nom })
    })
    .then(res => res.json())
    .then(data => {
      if (data.erreur) {
        alert(data.erreur);
        return;
      }
      ajouterEnfant(data.id, data.nom);
      nomEnfantInput.value = '';
    })
    .catch(() => alert("Erreur lors de l'inscription."));
  });
};

