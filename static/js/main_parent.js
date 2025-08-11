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

  // Variable pour savoir si on est dans la "fenêtre chat"
  let chatOuvert = false;

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
    const ids = Object.keys(enfantsValides);
    if (ids.length === 0) {
      alert("Merci de valider d'abord l'ID d'un enfant.");
      return;
    }
    const idEnfant = ids[0];

    socket.emit("envoyer_message", {
      id_enfant: idEnfant,
      message: message,
      emetteur: "parent",
      destinataire: "ecole"
    });

    inputMessage.value = "";
  });

  // Fonction pour fermer la fenêtre chat (à appeler dans retour)
  function fermerChat() {
    chatOuvert = false;
    // Ici il faut cacher la fenêtre chat et réinitialiser selon ton code HTML
    // Par exemple:
    document.getElementById("chat-section").style.display = "none";
    messagesDiv.innerHTML = "";
    // Et enlever la classe ou styles éventuels sur container si tu en as
    document.getElementById("container").classList.remove("chat-ouvert");
  }

  // Ajoute la gestion bouton retour formulaire (à adapter si tu as un bouton retour)
  const btnRetourForm = document.getElementById("btnRetour");
  if (btnRetourForm) {
    btnRetourForm.addEventListener("click", () => {
      if (chatOuvert) {
        fermerChat();
        history.back();
      }
    });
  }

  // Gestion bouton physique retour Android via popstate
  window.addEventListener("popstate", (event) => {
    if (chatOuvert) {
      fermerChat();
      // empêche d'aller plus loin dans l'historique
      history.pushState(null, null, window.location.href);
    }
  });

  // Quand on ouvre la fenêtre chat, il faut pushState dans l'historique pour gérer retour
  function ouvrirChat(idEnfant) {
    chatOuvert = true;
    // Afficher la fenêtre chat, charger les messages etc.
    document.getElementById("chat-section").style.display = "flex";
    // Ajouter classe si besoin
    document.getElementById("container").classList.add("chat-ouvert");
    // Ajouter un état dans l'historique
    history.pushState({ chatOpen: true }, "");
  }

  // Réception messages serveur en temps réel
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

  // Expose ouvrirChat pour que tu l'utilises ailleurs dans ton code
  window.ouvrirChat = ouvrirChat;
};

