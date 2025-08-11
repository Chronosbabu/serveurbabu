console.log("JavaScript chargé - école");

const socket = io();

window.onload = function() {
  const btnInscrire = document.getElementById('btnInscrire');
  const nomEnfantInput = document.getElementById('nomEnfant');
  const listeEnfants = document.getElementById('listeEnfants');

  const btnEnvoyerMessageTop = document.getElementById('btnEnvoyerMessageTop');
  const modalMessage = document.getElementById('modalMessage');
  const modalOverlay = document.getElementById('modalOverlay');
  const btnEnvoyerModal = document.getElementById('btnEnvoyerModal');
  const btnFermerModal = document.getElementById('btnFermerModal');
  const textareaMessage = document.getElementById('messageEnfants');

  const inputRecherche = document.getElementById('rechercheEnfant');
  const checkboxSelectTout = document.getElementById('selectTout');

  let enfants = []; // tableau {id, nom}

  function afficherEnfants() {
    const filtre = inputRecherche.value.toLowerCase();
    listeEnfants.innerHTML = '';

    enfants.forEach(({id, nom}) => {
      if (nom.toLowerCase().includes(filtre) || id.toLowerCase().includes(filtre)) {
        const li = document.createElement('li');
        li.style.listStyle = 'none';

        const divEnfant = document.createElement('div');
        divEnfant.classList.add('enfant-btn');

        const divNom = document.createElement('div');
        divNom.style.flexGrow = '1';

        const spanNom = document.createElement('span');
        spanNom.textContent = nom;
        spanNom.classList.add('enfant-nom');

        const spanId = document.createElement('small');
        spanId.textContent = id.toLowerCase();
        spanId.classList.add('enfant-id');

        divNom.appendChild(spanNom);
        divNom.appendChild(spanId);

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.classList.add('chk-enfant');
        checkbox.dataset.id = id;

        checkbox.addEventListener('change', () => {
          majBoutonEnvoyer();
          majCheckboxTout();
        });

        divEnfant.appendChild(divNom);
        divEnfant.appendChild(checkbox);

        li.appendChild(divEnfant);
        listeEnfants.appendChild(li);
      }
    });
    majBoutonEnvoyer();
  }

  function majCheckboxTout() {
    const total = document.querySelectorAll('.chk-enfant').length;
    const coches = document.querySelectorAll('.chk-enfant:checked').length;
    checkboxSelectTout.checked = (total > 0 && total === coches);
  }

  checkboxSelectTout.addEventListener('change', () => {
    const cocher = checkboxSelectTout.checked;
    document.querySelectorAll('.chk-enfant').forEach(cb => {
      cb.checked = cocher;
    });
    majBoutonEnvoyer();
  });

  inputRecherche.addEventListener('input', afficherEnfants);

  function majBoutonEnvoyer() {
    const nbSelectionnes = document.querySelectorAll('.chk-enfant:checked').length;
    btnEnvoyerMessageTop.disabled = (nbSelectionnes === 0);
  }

  btnEnvoyerMessageTop.addEventListener('click', () => {
    if (btnEnvoyerMessageTop.disabled) return;
    textareaMessage.value = '';
    modalMessage.style.display = 'block';
    modalOverlay.style.display = 'block';
  });

  btnFermerModal.addEventListener('click', fermerModal);
  modalOverlay.addEventListener('click', fermerModal);

  function fermerModal() {
    modalMessage.style.display = 'none';
    modalOverlay.style.display = 'none';
  }

  btnEnvoyerModal.addEventListener('click', () => {
    const message = textareaMessage.value.trim();
    if (!message) {
      alert("Écris un message.");
      return;
    }
    const coches = [...document.querySelectorAll('.chk-enfant:checked')];
    if (coches.length === 0) {
      alert("Sélectionne au moins un enfant.");
      fermerModal();
      return;
    }

    coches.forEach(cb => {
      const id = cb.dataset.id;
      socket.emit('envoyer_message', { id_enfant: id, message });
    });

    alert("Message envoyé aux enfants sélectionnés.");
    fermerModal();
  });

  function ajouterEnfant(id, nom) {
    enfants.push({id, nom});
    afficherEnfants();
  }

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

  // Initialiser affichage
  afficherEnfants();
};

