from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session
from flask_socketio import SocketIO
import os, json, hashlib
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret_key_here"

UPLOAD_FOLDER = os.path.join("data", "uploads")
AVATAR_FOLDER = os.path.join("data", "avatars")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AVATAR_FOLDER, exist_ok=True)

DATA_FILE = os.path.join("data", "posts.json")
USER_FILE = os.path.join("data", "users.json")

# Créer fichiers si inexistants
for file_path, default in [(DATA_FILE, []), (USER_FILE, [])]:
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            json.dump(default, f)

socketio = SocketIO(app)

# Fonctions utilitaires
def load_posts():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_posts(posts):
    with open(DATA_FILE, "w") as f:
        json.dump(posts, f, indent=4)

def load_users():
    with open(USER_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f, indent=4)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Routes utilisateurs
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        avatar_file = request.files.get("avatar")
        if not username or not password or not avatar_file:
            return redirect(request.url)
        users = load_users()
        if any(u["username"] == username for u in users):
            return "Nom d'utilisateur déjà pris !"

        avatar_filename = datetime.now().strftime("%Y%m%d%H%M%S_") + avatar_file.filename
        avatar_path = os.path.join(AVATAR_FOLDER, avatar_filename)
        avatar_file.save(avatar_path)

        users.append({
            "username": username,
            "password": hash_password(password),
            "avatar": avatar_filename
        })
        save_users(users)
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        users = load_users()
        user = next((u for u in users if u["username"] == username and u["password"] == hash_password(password)), None)
        if user:
            session["username"] = username
            session["avatar"] = user.get("avatar")
            return redirect(url_for("index"))
        return "Nom ou mot de passe incorrect !"
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

    if request.method == "POST":
        description = request.form.get("description", "").strip()
        if "file" not in request.files or not description:
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            return redirect(request.url)
        filename = datetime.now().strftime("%Y%m%d%H%M%S_") + file.filename
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)

        ext = file.filename.lower().split('.')[-1]
        file_type = "video" if ext in ["mp4", "webm", "ogg"] else "image"

        posts = load_posts()
        new_post = {
            "username": session["username"],
            "avatar": session.get("avatar"),
            "type": file_type,
            "file": filename,
            "description": description,
            "date": str(datetime.now())
        }
        posts.insert(0, new_post)
        save_posts(posts)
        socketio.emit('new_post', new_post)
        return redirect(url_for("index"))

    posts = load_posts()
    return render_template("style.html", posts=posts, username=session["username"], avatar=session.get("avatar"))

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/avatars/<filename>")
def avatar_file(filename):
    return send_from_directory(AVATAR_FOLDER, filename)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)

