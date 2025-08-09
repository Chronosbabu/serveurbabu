from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import json
import os
import eventlet

eventlet.monkey_patch()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

ENFANTS_FILE = 'data/enfants.json'

def lire_enfants():
    if not os.path.exists(ENFANTS_FILE):
        return {}
    with open(ENFANTS_FILE, 'r') as f:
        return json.load(f)

def ecrire_enfants(data):
    with open(ENFANTS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

@app.route('/')
def index():
    return "Serveur actif"

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

@socketio.on('connect')
def on_connect():
    print('Client connecté')

@socketio.on('envoyer_message')
def on_message(data):
    # data attendu: {'id_enfant': ..., 'message': ...}
    id_enfant = data.get('id_enfant')
    message = data.get('message')
    if not id_enfant or not message:
        return
    # Ici tu peux stocker le message si besoin (ex: fichier ou base)
    emit('nouveau_message', {'id_enfant': id_enfant, 'message': message}, broadcast=True)

if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)
    socketio.run(app, host='0.0.0.0', port=5000)

