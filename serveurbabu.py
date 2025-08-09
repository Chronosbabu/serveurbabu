from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room
import json
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
socketio = SocketIO(app, cors_allowed_origins="*")

ENFANTS_FILE = 'data/enfants.json'
MESSAGES_FILE = 'data/messages.json'

def lire_enfants():
    if not os.path.exists(ENFANTS_FILE):
        return {}
    with open(ENFANTS_FILE, 'r') as f:
        return json.load(f)

def ecrire_enfants(data):
    with open(ENFANTS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def lire_messages():
    if not os.path.exists(MESSAGES_FILE):
        return {}
    with open(MESSAGES_FILE, 'r') as f:
        return json.load(f)

def ecrire_messages(data):
    with open(MESSAGES_FILE, 'w') as f:
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

@app.route('/api/chercher_enfant', methods=['POST'])
def chercher_enfant():
    data = request.get_json()
    id_enfant = data.get('id', '').strip()
    enfants = lire_enfants()
    if id_enfant in enfants:
        return jsonify({'nom': enfants[id_enfant]['nom']})
    else:
        return jsonify({'erreur': 'ID introuvable'}), 404

# --- SocketIO events ---

# Quand un client rejoint une "room" basée sur l'id de l'enfant
@socketio.on('join')
def on_join(data):
    id_enfant = data.get('id')
    if id_enfant:
        join_room(id_enfant)
        emit('status', {'msg': f'Connecté à la room {id_enfant}'})

# Envoi d'un message en temps réel
@socketio.on('envoyer_message')
def handle_envoyer_message(data):
    id_enfant = data.get('id')
    message = data.get('message')
    emetteur = data.get('emetteur')
    destinataire = data.get('destinataire')

    if not all([id_enfant, message, emetteur, destinataire]):
        emit('erreur', {'msg': 'Données manquantes'})
        return

    messages = lire_messages()
    if id_enfant not in messages:
        messages[id_enfant] = []

    messages[id_enfant].append({
        'emetteur': emetteur,
        'destinataire': destinataire,
        'message': message,
        'lu': False
    })
    ecrire_messages(messages)

    # Émettre le message à tous dans la room de cet enfant
    emit('nouveau_message', {
        'emetteur': emetteur,
        'destinataire': destinataire,
        'message': message
    }, room=id_enfant)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)

