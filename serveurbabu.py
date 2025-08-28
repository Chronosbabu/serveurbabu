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
def pari():
    return render_template("pari.html")

# --- Routes utilisateur / compte ---
@app.route("/compte/verifier/<username>")
def verifier_user(username):
    if username in USERS:
        return jsonify({"exists": True})
    return jsonify({"exists": False}), 404

@app.route("/compte/ajouter/<username>")
def ajouter_user(username):
    if username in USERS:
        return jsonify({"success": False, "message": "Utilisateur existe déjà"}), 400
    USERS[username] = {"francs":0, "dollars":0, "paris":[]}
    return jsonify({"success": True, "message": f"Utilisateur {username} ajouté"})

@app.route("/compte/depot", methods=["POST"])
def depot():
    data = request.json
    username = data.get("username")
    francs = int(data.get("francs",0))
    dollars = int(data.get("dollars",0))

    if username not in USERS:
        return jsonify({"success": False, "message": "Utilisateur introuvable"}), 404

    USERS[username]["francs"] += francs
    USERS[username]["dollars"] += dollars
    return jsonify({"success": True, "message": f"Dépôt effectué pour {username}", "solde": USERS[username]})

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

# --- Route pour parier ---
@app.route("/pari", methods=["POST"])
def faire_pari():
    data = request.json
    username = data.get("username")
    match_id = int(data.get("match_id"))
    devise = data.get("devise")
    montant = int(data.get("montant"))

    if username not in USERS:
        return jsonify({"success": False, "message": "Utilisateur introuvable"}), 404

    # Vérifier si match existe
    match = next((m for m in MATCHES if m["id"]==match_id), None)
    if not match:
        return jsonify({"success": False, "message": "Match introuvable"}), 404

    # Vérifier si déjà parié
    if match_id in USERS[username]["paris"]:
        return jsonify({"success": False, "message": "Vous avez déjà parié sur ce match"}), 400

    # Vérifier solde
    if USERS[username][devise] < montant:
        return jsonify({"success": False, "message": "Solde insuffisant"}), 400

    # Retirer montant et enregistrer pari
    USERS[username][devise] -= montant
    USERS[username]["paris"].append(match_id)
    return jsonify({"success": True, "message": f"Pari placé sur {match['equipe1']} vs {match['equipe2']}", "solde": USERS[username]})

if __name__ == "__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port)

