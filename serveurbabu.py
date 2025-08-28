# app.py
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# Base de données en mémoire
USERS = {}         # username -> {"francs":0,"dollars":0,"paris":[]}
MATCHES = []       # liste de dicts {"id":..., "equipe1":..., "equipe2":...}
RESULTS = []       # liste de dicts {"match_id":..., "resultat":...}

# --- Routes pages HTML ---
@app.route("/")
def accueil():
    return render_template("index.html")

@app.route("/compte")
def compte():
    return render_template("compte.html")

@app.route("/pari")
def pari_page():
    return render_template("pari.html")

# --- Routes utilisateur / compte ---
@app.route("/compte/verifier/<username>")
def verifier_user(username):
    if username in USERS:
        return jsonify({"exists": True, "solde": USERS[username]})
    return jsonify({"exists": False}), 404

@app.route("/compte/ajouter/<username>")
def ajouter_user(username):
    if username in USERS:
        return jsonify({"success": False, "message": "Utilisateur existe déjà"}), 400
    USERS[username] = {"francs":0, "dollars":0, "paris":[]}
    return jsonify({"success": True, "message": f"Utilisateur {username} ajouté", "solde": USERS[username]})

@app.route("/compte/depot", methods=["POST"])
def depot():
    data = request.json
    username = data.get("username")
    francs = data.get("francs", 0)
    dollars = data.get("dollars", 0)

    if username not in USERS:
        return jsonify({"success": False, "message": "Utilisateur non trouvé"}), 404

    USERS[username]["francs"] += francs
    USERS[username]["dollars"] += dollars

    return jsonify({
        "success": True,
        "message": f"Dépôt effectué : {francs} Francs, {dollars} Dollars",
        "solde": USERS[username]
    })

# --- Routes pour les matches ---
@app.route("/matches/add", methods=["POST"])
def add_match():
    data = request.json
    equipe1 = data.get("equipe1")
    equipe2 = data.get("equipe2")
    match_id = len(MATCHES) + 1
    MATCHES.append({"id": match_id, "equipe1": equipe1, "equipe2": equipe2})
    return jsonify({"success": True, "match_id": match_id, "message": "Match ajouté"})

@app.route("/matches")
def get_matches():
    return jsonify(MATCHES)

# --- Route pour enregistrer un pari ---
@app.route("/pari", methods=["POST"])
def ajouter_pari():
    data = request.json
    username = data.get("username")
    match_id = data.get("match_id")
    devise = data.get("devise")
    montant = data.get("montant")

    if username not in USERS:
        return jsonify({"success": False, "message": "Utilisateur non trouvé"}), 404

    if devise not in ("francs","dollars"):
        return jsonify({"success": False, "message": "Devise invalide"}), 400

    if USERS[username][devise] < montant:
        return jsonify({"success": False, "message": "Solde insuffisant"}), 400

    # Débit du montant
    USERS[username][devise] -= montant
    # Ajout du pari
    USERS[username]["paris"].append({
        "match_id": match_id,
        "devise": devise,
        "montant": montant
    })

    return jsonify({"success": True, "message": f"Pari de {montant} {devise} sur le match {match_id} enregistré"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port)

