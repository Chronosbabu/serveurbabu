from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)

# Chemin vers le fichier enfants.json
ENFANTS_FILE = 'data/enfants.json'

# Fonction pour lire les enfants
def lire_enfants():
    if not os.path.exists(ENFANTS_FILE):
        return {}
    with open(ENFANTS_FILE, 'r') as f:
        return json.load(f)

# Fonction pour écrire les enfants
def ecrire_enfants(data):
    with open(ENFANTS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

@app.route('/')
def accueil():
    return "Bienvenue sur le serveur"

@app.route('/ecole')
def ecole():
    return render_template('ecole.html')

@app.route('/parent')
def parent():
    return render_template('parent.html')

@app.route('/api/inscrire_enfant', methods=['POST'])
def inscrire_enfant():
    data = request.get_json()
    nom = data.get('nom', '').strip()
    if not nom:
        return jsonify({'erreur': 'Nom vide'}), 400

    enfants = lire_enfants()
    nouvel_id = f"ENFANT{len(enfants) + 1:03d}"

    enfants[nouvel_id] = {'nom': nom}
    ecrire_enfants(enfants)

    return jsonify({'id': nouvel_id, 'nom': nom})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
