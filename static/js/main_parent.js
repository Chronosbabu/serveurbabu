console.log("JavaScript chargé - parent");

// Connexion explicite au serveur Socket.IO
const socket = io(window.location.origin, {
  transports: ["websocket", "polling"]
});

window.onload = function () {
  const btnValider = document.getElementById("btnValiderId");
  const listeEnfants = document.getElementById("listeEnfants");
  const messagesDiv = document.getElementById("messages");
  const inputMessage = document.getElementById("inputMessage");
  const btnEnvoyer = document.getElementById("btnEnvoyerMessage");

  // Stocker enfants validés ici
  const enfantsValides = {};

  // Valider un ID enfant et l'ajouter à la liste
  btnValider.addEventListener("click", function () {
    const idEnfant = document.getElementById("inputIdEnfant").value.trim();
    if (idEnfant === "") {
      alert("Merci d'entrer l'ID de l'enfant.");
      return;
    }

    fetch("/api/chercher_enfant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: idEnfant })
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.erreur) {
          const li = document.createElement("li");
          li.textContent = `ID introuvable : ${idEnfant}`;
          li.style.color = "red";
          listeEnfants.appendChild(li);
        } else {
          if (enfantsValides[idEnfant]) {
            alert("Cet enfant est déjà ajouté.");
            return;
          }
          enfantsValides[idEnfant] = data.nom;
          const li = document.createElement("li");
          li.textContent = `${data.nom} (ID: ${idEnfant})`;
          listeEnfants.appendChild(li);

          // Rejoindre la room socket pour cet enfant
          socket.emit("join", { id: idEnfant });
        }
        document.getElementById("inputIdEnfant").value = "";
      })
      .catch((error) => {
        console.error("Erreur:", error);
        alert("Erreur lors de la recherche de l'enfant.");
      });
  });

  // Envoyer un message (au serveur / école)
  btnEnvoyer.addEventListener("click", function () {
    const message = inputMessage.value.trim();
    if (message === "") {
      alert("Merci d'écrire un message.");
      return;
    }
    // Pour simplifier, on envoie au premier enfant validé
    const ids = Object.keys(enfantsValides);
    if (ids.length === 0) {
      alert("Merci de valider d'abord l'ID d'un enfant.");
      return;
    }
    const idEnfant = ids[0];

    socket.emit("envoyer_message", {
      id_enfant: idEnfant, // cohérent avec le code serveur
      message: message,
      emetteur: "parent",
      destinataire: "ecole"
    });

    inputMessage.value = "";
  });

  // Afficher les messages reçus en temps réel
  socket.on("nouveau_message", function (data) {
    if (!data.message) return;
    const p = document.createElement("p");
    p.textContent = `[${data.emetteur || data.id_enfant}] : ${data.message}`;
    messagesDiv.appendChild(p);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  });

  socket.on("status", function (data) {
    console.log(data.msg);
  });

  socket.on("erreur", function (data) {
    alert("Erreur: " + data.msg);
  });
};


