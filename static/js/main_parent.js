console.log("JavaScript chargé - parent");

window.onload = function() {
  const btn = document.getElementById('btnValiderId');
  if (btn) {
    btn.addEventListener('click', function() {
      const idEnfant = document.getElementById('inputIdEnfant').value.trim();
      if (idEnfant === '') {
          alert("Merci d'entrer l'ID de l'enfant.");
          return;
      }

      fetch('/api/chercher_enfant', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: idEnfant })
      })
      .then(response => response.json())
      .then(data => {
          const liste = document.getElementById('listeEnfants');
          if (data.erreur) {
              const li = document.createElement('li');
              li.textContent = `ID introuvable : ${idEnfant}`;
              li.style.color = 'red';
              liste.appendChild(li);
          } else {
              const li = document.createElement('li');
              li.textContent = `${data.nom} (ID: ${idEnfant})`;
              liste.appendChild(li);
          }
          document.getElementById('inputIdEnfant').value = '';
      })
      .catch(error => {
          console.error('Erreur:', error);
          alert("Erreur lors de la recherche de l'enfant.");
      });
    });
  } else {
    console.error("Bouton btnValiderId introuvable dans le DOM");
  }
};
