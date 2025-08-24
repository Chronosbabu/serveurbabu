# --- Imports et initialisation ---
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session, abort, jsonify
from flask_socketio import SocketIO, emit, join_room
import os, json, hashlib
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secret_key_here"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_FOLDER = os.path.join(DATA_DIR, "uploads")
AVATAR_FOLDER = os.path.join(DATA_DIR, "avatars")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AVATAR_FOLDER, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

DATA_FILE = os.path.join(DATA_DIR, "posts.json")
USER_FILE = os.path.join(DATA_DIR, "users.json")
MESSAGES_FILE = os.path.join(DATA_DIR, "messages.json")

for file_path, default in [(DATA_FILE, []), (USER_FILE, []), (MESSAGES_FILE, {})]:
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)

socketio = SocketIO(app, manage_session=True, cors_allowed_origins="*")

# --- Fonctions utilitaires ---
def load_posts():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_posts(posts):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)

def load_users():
    with open(USER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users):
    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def load_messages():
    with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_messages(messages):
    with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user(username):
    users = load_users()
    return next((u for u in users if u.get("username") == username), None)

def append_message(sender, receiver, text, msg_type="text", url=None):
    messages = load_messages()
    key1 = f"{sender}_{receiver}"
    key2 = f"{receiver}_{sender}"
    now_iso = datetime.now().isoformat()
    entry = {"sender": sender, "text": text, "date": now_iso, "type": msg_type}
    if url:
        entry["url"] = url

    if key1 in messages:
        messages[key1].append(entry)
    elif key2 in messages:
        messages[key2].append(entry)
    else:
        messages[key1] = [entry]

    save_messages(messages)
    return entry

# --- Routes chat et messages ---
@app.route("/chat/<username>")
def chat(username):
    if "username" not in session:
        return redirect(url_for("login"))
    messages = load_messages()
    key1 = f"{session['username']}_{username}"
    key2 = f"{username}_{session['username']}"
    conv = messages.get(key1) or messages.get(key2) or []
    return render_template("chat.html", chat_user=username, messages=conv)

@app.route("/send_message", methods=["POST"])
def send_message_http():
    if "username" not in session:
        return jsonify({"success": False, "error": "Non connecté"}), 401
    data = request.get_json(silent=True) or {}
    sender = session.get("username")
    receiver = (data.get("recipient") or "").strip()
    text = (data.get("message") or "").strip()
    if not receiver or not text:
        return jsonify({"success": False, "error": "Champs manquants"}), 400
    entry = append_message(sender, receiver, text)
    socketio.emit("new_message", entry, room=receiver)
    socketio.emit("new_message", entry, room=sender)
    return jsonify({"success": True})

# --- NOUVELLE ROUTE pour fichiers ---
@app.route("/send_file", methods=["POST"])
def send_file_http():
    if "username" not in session:
        return jsonify({"success": False, "error": "Non connecté"}), 401
    sender = session.get("username")
    receiver = request.form.get("recipient", "").strip()
    file = request.files.get("file")
    if not receiver or not file:
        return jsonify({"success": False, "error": "Fichier ou destinataire manquant"}), 400

    filename = datetime.now().strftime("%Y%m%d%H%M%S_") + secure_filename(file.filename)
    file.save(os.path.join(UPLOAD_FOLDER, filename))

    url = url_for("uploaded_file", filename=filename)
    msg_type = "image" if file.content_type.startswith("image/") else "video"
    text = "[Fichier envoyé]"  # texte visible en plus
    entry = append_message(sender, receiver, text, msg_type, url)
    socketio.emit("new_message", entry, room=receiver)
    socketio.emit("new_message", entry, room=sender)
    return jsonify({"success": True, "url": url})

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# --- SocketIO ---
@socketio.on("connect")
def handle_connect():
    user = session.get("username")
    if user:
        join_room(user)

@socketio.on("send_message")
def handle_send_message(data):
    sender = session.get("username")
    receiver = (data.get("receiver") or "").strip()
    text = (data.get("text") or "").strip()
    if not sender or not receiver or not text:
        return
    entry = append_message(sender, receiver, text)
    emit("new_message", entry, room=receiver)
    emit("new_message", entry, room=sender)

# --- Lancement ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port)

