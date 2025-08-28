from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # pour autoriser les requêtes depuis les fichiers locaux

# Base de données simple en mémoire (à remplacer par JSON ou vraie DB)
USERS = {}       # username -> {"francs": 0, "dollars": 0}
MATCHES = []     # liste de dicts {"equipe1": ..., "equipe2": ...}
RESULTS = []     # liste de dicts {"match_id": ..., "resultat": ...}

# --- Routes utilisateur / compte ---
@app.route("/compte/verifier/<username>")
def verifier_user(username):
    if username in USERS:
        return jsonify({"exists": True})
    return jsonify({"exists": False}), 404

@app.route("/compte/depot", methods=["POST"])
def depot():
    data = request.json
    username = data.get("username")
    francs = data.get("francs", 0)
    dollars = data.get("dollars", 0)

    if username not in USERS:
        return jsonify({"success": False, "message": "Utilisateur introuvable"}), 404

    USERS[username]["francs"] += francs
    USERS[username]["dollars"] += dollars
    return jsonify({"success": True, "message": f"Dépôt effectué pour {username}"})

@app.route("/compte/ajouter/<username>")
def ajouter_user(username):
    if username in USERS:
        return jsonify({"success": False, "message": "Utilisateur existe déjà"}), 400
    USERS[username] = {"francs": 0, "dollars": 0}
    return jsonify({"success": True, "message": f"Utilisateur {username} ajouté"})

# --- Routes pour les matches ---
@app.route("/matches/add", methods=["POST"])
def add_match():
    data = request.json
    equipe1 = data.get("equipe1")
    equipe2 = data.get("equipe2")
    match_id = len(MATCHES) + 1
    MATCHES.append({"id": match_id, "equipe1": equipe1, "equipe2": equipe2})
    return jsonify({"success": True, "match_id": match_id, "message": "Match ajouté"})

@app.route("/resultat", methods=["POST"])
def add_result():
    data = request.json
    match_id = data.get("match_id")
    resultat = data.get("resultat")

    if not resultat:
        return jsonify({"success": False, "message": "Résultat vide"}), 400

    RESULTS.append({"match_id": match_id, "resultat": resultat})
    return jsonify({"success": True, "message": "Résultat publié"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

