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

socketio = SocketIO(app, manage_session=False)

# --- Utilitaires ---
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

# --- Routes Utilisateurs / Posts ---
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        avatar_file = request.files.get("avatar")
        if not username or not password:
            return "Nom d'utilisateur et mot de passe requis.", 400
        users = load_users()
        if any(u["username"].lower() == username.lower() for u in users):
            return "Nom d'utilisateur déjà pris !", 400
        avatar_filename = None
        if avatar_file and avatar_file.filename:
            avatar_filename = datetime.now().strftime("%Y%m%d%H%M%S_") + secure_filename(avatar_file.filename)
            avatar_file.save(os.path.join(AVATAR_FOLDER, avatar_filename))
        users.append({
            "username": username,
            "password": hash_password(password),
            "avatar": avatar_filename,
            "bio": "",
            "created_at": datetime.now().isoformat()
        })
        save_users(users)
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        users = load_users()
        user = next((u for u in users if u["username"].lower() == username.lower()
                     and u["password"] == hash_password(password)), None)
        if user:
            session["username"] = user["username"]
            session["avatar"] = user.get("avatar")
            return redirect(url_for("index"))
        return "Nom ou mot de passe incorrect !", 401
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("avatar", None)
    return redirect(url_for("login"))

@app.route("/", methods=["GET"])
def index():
    if "username" not in session:
        return redirect(url_for("login"))
    posts = load_posts()
    for p in posts:
        p['liked_by_user'] = session["username"] in p.get("liked_by", [])
        p['comments_count'] = len(p.get("comments", []))
    return render_template("style.html", posts=posts, username=session["username"], avatar=session.get("avatar"))

@app.route("/profile/<username>")
def profile(username):
    user = get_user(username)
    if not user:
        abort(404)
    posts = load_posts()
    user_posts = [p for p in posts if p.get("username") == user["username"]]
    for p in user_posts:
        p['liked_by_user'] = session.get("username") in p.get("liked_by", [])
        p['comments_count'] = len(p.get("comments", []))
    return render_template("profile.html", profile_user=user, posts=user_posts,
                           current_username=session.get("username"), current_avatar=session.get("avatar"))

# --- Routes Messagerie ---
@app.route("/conversations")
def conversations():
    if "username" not in session:
        return redirect(url_for("login"))
    messages = load_messages()
    user_conversations = []
    for key, conv in messages.items():
        if session["username"] in key.split("_"):
            other = [u for u in key.split("_") if u != session["username"]][0]
            last_msg = conv[-1]["text"] if conv else ""
            user_conversations.append({"username": other, "last_msg": last_msg})
    return render_template("conversations.html", conversations=user_conversations)

@app.route("/chat/<username>")
def chat(username):
    if "username" not in session:
        return redirect(url_for("login"))
    messages = load_messages()
    key1 = f"{session['username']}_{username}"
    key2 = f"{username}_{session['username']}"
    conv = messages.get(key1) or messages.get(key2) or []
    return render_template("chat.html", chat_user=username, messages=conv)

# --- SocketIO Messagerie ---
@socketio.on("connect")
def socket_connect():
    if "username" in session:
        join_room(session["username"])

@socketio.on("send_message")
def handle_send_message(data):
    sender = session.get("username")
    receiver = data.get("receiver")
    text = data.get("text")
    if not sender or not receiver or not text:
        return
    messages = load_messages()
    key1 = f"{sender}_{receiver}"
    key2 = f"{receiver}_{sender}"
    msg_obj = {"sender": sender, "text": text, "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    if key1 in messages:
        messages[key1].append(msg_obj)
    elif key2 in messages:
        messages[key2].append(msg_obj)
    else:
        messages[key1] = [msg_obj]
    save_messages(messages)
    emit("new_message", {"sender": sender, "text": text, "date": msg_obj["date"]}, room=receiver)
    emit("new_message", {"sender": sender, "text": text, "date": msg_obj["date"]}, room=sender)

# --- Fichiers statiques ---
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/avatars/<filename>")
def avatar_file(filename):
    return send_from_directory(AVATAR_FOLDER, filename)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port)

