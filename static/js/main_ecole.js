console.log("JavaScript chargé - école");

window.onload = function() {
  const btnInscrire = document.getElementById('btnInscrire');
  if (!btnInscrire) return;

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
      const liste = document.getElementById('listeEnfants');
      const li = document.createElement('li');
      li.textContent = `${data.nom} (ID: ${data.id})`;
      liste.appendChild(li);
      document.getElementById('nomEnfant').value = '';
    })
    .catch(error => {
      console.error('Erreur:', error);
      alert("Erreur lors de l'inscription.");
    });
  });
};

