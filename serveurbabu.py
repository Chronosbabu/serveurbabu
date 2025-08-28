from flask import Flask, request, jsonify, render_template_string, redirect, url_for
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)  # pour autoriser les requêtes depuis les fichiers locaux

# Base de données simple en mémoire (à remplacer par JSON ou vraie DB)
USERS = {}       # username -> {"francs": 0, "dollars": 0}
MATCHES = []     # liste de dicts {"equipe1": ..., "equipe2": ...}
RESULTS = []     # liste de dicts {"match_id": ..., "resultat": ...}

# --- Page principale : inscription utilisateur ---
@app.route("/", methods=["GET", "POST"])
def accueil():
    if request.method == "POST":
        username = request.form.get("username")
        if not username:
            return "Nom d'utilisateur requis", 400
        
        # Création automatique si nouveau
        if username not in USERS:
            USERS[username] = {"francs": 0, "dollars": 0}
        
        # Rediriger vers la page de dépôt
        return redirect(url_for("page_depot", username=username))
    
    html = """
    <!DOCTYPE html>
    <html lang="fr">
    <head><meta charset="UTF-8"><title>Connexion</title></head>
    <body>
        <h1>Connexion / Inscription</h1>
        <form method="post">
            <label>Nom d'utilisateur :</label>
            <input type="text" name="username" required>
            <button type="submit">Valider</button>
        </form>
    </body>
    </html>
    """
    return render_template_string(html)

# --- Page dépôt ---
@app.route("/depot/<username>", methods=["GET", "POST"])
def page_depot(username):
    if username not in USERS:
        return "Utilisateur introuvable", 404
    
    if request.method == "POST":
        francs = int(request.form.get("francs", 0))
        dollars = int(request.form.get("dollars", 0))
        USERS[username]["francs"] += francs
        USERS[username]["dollars"] += dollars
        return redirect(url_for("page_compte"))
    
    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head><meta charset="UTF-8"><title>Dépôt</title></head>
    <body>
        <h1>Dépôt pour {username}</h1>
        <form method="post">
            <label>Francs :</label>
            <input type="number" name="francs" min="0" value="0"><br>
            <label>Dollars :</label>
            <input type="number" name="dollars" min="0" value="0"><br>
            <button type="submit">Déposer</button>
        </form>
        <a href="/">Retour accueil</a>
    </body>
    </html>
    """
    return render_template_string(html)

# --- Page compte : afficher tous les utilisateurs ---
@app.route("/compte")
def page_compte():
    html = "<h2>Gestion des comptes :</h2><ul>"
    for user, solde in USERS.items():
        html += f"<li>{user} - Francs: {solde['francs']}, Dollars: {solde['dollars']}</li>"
    html += "</ul><a href='/'>Retour accueil</a>"
    return render_template_string(html)

# --- API JSON existante (toujours dispo si besoin) ---
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

# --- Liste matches ---
@app.route("/matches")
def liste_matches():
    html = "<h2>Liste des matches :</h2><ul>"
    for m in MATCHES:
        html += f"<li>{m['equipe1']} vs {m['equipe2']} (ID: {m['id']})</li>"
    html += "</ul><a href='/'>Retour</a>"
    return render_template_string(html)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

