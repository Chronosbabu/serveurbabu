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

@app.route('/api/inscrire_enfant', methods=['POST'])
def inscrire_enfant():
    data = request.get_json()
    nom = data.get('nom', '').strip()
    if not nom:
        return jsonify({'erreur': 'Nom vide'}), 400

    enfants = lire_enfants()
    # Création d’un ID simple
    nouvel_id = f"ENFANT{len(enfants) + 1:03d}"

    enfants[nouvel_id] = {'nom': nom}
    ecrire_enfants(enfants)

    return jsonify({'id': nouvel_id, 'nom': nom})

