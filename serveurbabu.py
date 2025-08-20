from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session, abort, jsonify
from flask_socketio import SocketIO
import os, json, hashlib
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret_key_here"

# Dossiers
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_FOLDER = os.path.join(DATA_DIR, "uploads")
AVATAR_FOLDER = os.path.join(DATA_DIR, "avatars")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AVATAR_FOLDER, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Fichiers JSON
DATA_FILE = os.path.join(DATA_DIR, "posts.json")
USER_FILE = os.path.join(DATA_DIR, "users.json")

# Créer fichiers si inexistants
for file_path, default in [(DATA_FILE, []), (USER_FILE, [])]:
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)

socketio = SocketIO(app)

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

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user(username):
    users = load_users()
    return next((u for u in users if u.get("username") == username), None)

# --- Auth / Users ---
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
            avatar_filename = datetime.now().strftime("%Y%m%d%H%M%S_") + avatar_file.filename
            avatar_path = os.path.join(AVATAR_FOLDER, avatar_filename)
            avatar_file.save(avatar_path)

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

# --- Flux principal ---
@app.route("/", methods=["GET", "POST"])
def index():
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        description = (request.form.get("description") or "").strip()
        if "file" not in request.files or not description:
            return redirect(request.url)

        file = request.files["file"]
        if not file or file.filename == "":
            return redirect(request.url)

        filename = datetime.now().strftime("%Y%m%d%H%M%S_") + file.filename
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)

        ext = file.filename.lower().rsplit('.', 1)[-1] if '.' in file.filename else ""
        file_type = "video" if ext in ["mp4", "webm", "ogg"] else "image"

        posts = load_posts()
        new_post = {
            "id": len(posts) + 1,
            "username": session["username"],
            "avatar": session.get("avatar"),
            "type": file_type,
            "file": filename,
            "description": description,
            "likes": 0,
            "liked_by": [],
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        posts.insert(0, new_post)
        save_posts(posts)
        socketio.emit('new_post', new_post)
        return redirect(url_for("index"))

    posts = load_posts()
    # Marquer si l'utilisateur a liké les posts
    for p in posts:
        p['liked_by_user'] = session["username"] in p.get("liked_by", [])
    return render_template("style.html",
                           posts=posts,
                           username=session["username"],
                           avatar=session.get("avatar"))

# --- Like route ---
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
    else:
        post.setdefault("liked_by", []).append(username)
    post["likes"] = len(post["liked_by"])
    save_posts(posts)
    return jsonify({"likes": post["likes"], "liked": username in post.get("liked_by", [])})

# --- Page profil ---
@app.route("/profile/<username>")
def profile(username):
    user = get_user(username)
    if not user:
        abort(404)

    posts = load_posts()
    user_posts = [p for p in posts if p.get("username") == user["username"]]
    for p in user_posts:
        p['liked_by_user'] = session.get("username") in p.get("liked_by", [])
    return render_template("profile.html",
                           profile_user=user,
                           posts=user_posts,
                           current_username=session.get("username"),
                           current_avatar=session.get("avatar"))

# --- Static medias ---
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/avatars/<filename>")
def avatar_file(filename):
    return send_from_directory(AVATAR_FOLDER, filename)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port)

