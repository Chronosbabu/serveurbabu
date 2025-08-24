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

def append_message(sender, receiver, text):
    messages = load_messages()
    key1 = f"{sender}_{receiver}"
    key2 = f"{receiver}_{sender}"
    now_iso = datetime.now().isoformat()
    entry = {"sender": sender, "text": text, "date": now_iso}

    if key1 in messages:
        messages[key1].append(entry)
    elif key2 in messages:
        messages[key2].append(entry)
    else:
        messages[key1] = [entry]

    save_messages(messages)
    return entry

# --- Routes utilisateurs/posts ---
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

@app.route("/", methods=["GET", "POST"])
def index():
    if "username" not in session:
        return redirect(url_for("login"))

    posts = load_posts()
    for p in posts:
        p['liked_by_user'] = session["username"] in p.get("liked_by", [])
        p['comments_count'] = len(p.get("comments", []))
    return render_template("style.html", posts=posts, username=session["username"], avatar=session.get("avatar"))

@app.route("/add_post", methods=["GET", "POST"])
def add_post():
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        content = (request.form.get("content") or "").strip()
        media_file = request.files.get("media")
        filename = None
        media_type = "text"

        if media_file and media_file.filename:
            filename = datetime.now().strftime("%Y%m%d%H%M%S_") + secure_filename(media_file.filename)
            media_file.save(os.path.join(UPLOAD_FOLDER, filename))
            ext = os.path.splitext(filename)[1].lower()
            if ext in [".jpg", ".jpeg", ".png", ".gif"]:
                media_type = "image"
            elif ext in [".mp4", ".mov", ".avi", ".webm"]:
                media_type = "video"

        posts = load_posts()
        new_post = {
            "id": len(posts) + 1,
            "username": session["username"],
            "avatar": session.get("avatar"),
            "type": media_type,
            "file": filename,
            "description": content,
            "likes": 0,
            "liked_by": [],
            "comments": [],
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        posts.insert(0, new_post)
        save_posts(posts)
        # --- CORRECTION ICI ---
        # socketio.emit('new_post', new_post, broadcast=True)  # ancienne ligne qui causait l'erreur
        socketio.emit('new_post', new_post)  # version compatible toutes versions
        return redirect(url_for("index"))

    return render_template("new_post.html")

# --- Suite des routes identiques, aucune modification ---
@app.route("/like/<int:post_id>", methods=["POST"])
def like_post(post_id):
    if "username" not in session:
        return jsonify({"error": "Non connecté"}), 401
    posts = load_posts()
    post = next((p for p in posts if p["id"] == post_id), None)
    if not post:
        return jsonify({"error": "Post non trouvé"}), 404

    username = session["username"]
    if username in post.get("liked_by", []):
        post["liked_by"].remove(username)
        liked = False
    else:
        post.setdefault("liked_by", []).append(username)
        liked = True

    post["likes"] = len(post["liked_by"])
    save_posts(posts)
    socketio.emit('update_like', {"post_id": post_id, "likes": post["likes"], "user": username})

    
    return jsonify({"likes": post["likes"], "liked": liked})

@app.route("/comments/<int:post_id>", methods=["GET", "POST"])
def comments(post_id):
    if "username" not in session:
        return redirect(url_for("login"))

    posts = load_posts()
    post = next((p for p in posts if p["id"] == post_id), None)
    if not post:
        abort(404)

    if request.method == "POST":
        content = (request.form.get("comment") or "").strip()
        if content:
            comment_data = {
                "username": session["username"],
                "avatar": session.get("avatar"),
                "content": content,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            post.setdefault("comments", []).append(comment_data)
            save_posts(posts)
            socketio.emit('new_comment', {"post_id": post_id, **comment_data}, broadcast=True)
        return redirect(url_for("comments", post_id=post_id))

    return render_template("comments.html", post=post, username=session["username"], avatar=session.get("avatar"))

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

@app.route("/search", methods=["GET"])
def search_users():
    if "username" not in session:
        return redirect(url_for("login"))
    query = (request.args.get("q") or "").strip().lower()
    users = load_users()
    if query:
        users = [u for u in users if query in u["username"].lower()]
    return render_template("search.html", users=users, current_username=session["username"])

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/avatars/<filename>")
def avatar_file(filename):
    return send_from_directory(AVATAR_FOLDER, filename)

# --- Routes Messages ---
@app.route("/conversations")
def conversations():
    if "username" not in session:
        return redirect(url_for("login"))

    messages = load_messages()
    username = session.get("username")
    user_conversations = []

    for key, conv in messages.items():
        try:
            u1, u2 = key.split("_", 1)
        except ValueError:
            continue
        if username not in (u1, u2):
            continue
        other_user = u2 if u1 == username else u1
        last_msg = conv[-1]["text"] if conv else ""
        last_date = conv[-1].get("date") if conv else ""
        user_conversations.append({
            "username": other_user,
            "last_msg": last_msg,
            "last_date": last_date
        })

    user_conversations.sort(key=lambda x: x.get("last_date", ""), reverse=True)
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
    socketio.emit("new_message", {"sender": sender, "text": text, "date": entry["date"]}, room=receiver)
    socketio.emit("new_message", {"sender": sender, "text": text, "date": entry["date"]}, room=sender)

    return jsonify({"success": True})

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
    emit("new_message", {"sender": sender, "text": text, "date": entry["date"]}, room=receiver)
    emit("new_message", {"sender": sender, "text": text, "date": entry["date"]}, room=sender)

@socketio.on('send_comment')
def handle_send_comment(data):
    if "username" not in session:
        return
    post_id = data.get('post_id')
    content = (data.get('content') or "").strip()
    if not post_id or not content:
        return
    posts = load_posts()
    post = next((p for p in posts if p["id"] == post_id), None)
    if not post:
        return
    comment_data = {
        "username": session["username"],
        "avatar": session.get("avatar"),
        "content": content,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    post.setdefault("comments", []).append(comment_data)
    save_posts(posts)
    emit('new_comment', {"post_id": post_id, **comment_data}, broadcast=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port)

