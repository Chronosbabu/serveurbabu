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
        return jsonify({"exists": True, "solde": USERS[username]})
    return jsonify({"exists": False}), 404

@app.route("/compte/ajouter/<username>")
def ajouter_user(username):
    if username in USERS:
        return jsonify({"success": False, "message": "Utilisateur existe déjà"}), 400
    USERS[username] = {"francs":0, "dollars":0, "paris":[]}
    return jsonify({"success": True, "message": f"Utilisateur {username} ajouté", "solde": USERS[username]})

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port)
    
    
    
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
    
    

