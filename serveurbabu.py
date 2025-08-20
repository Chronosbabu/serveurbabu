from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session
from flask_socketio import SocketIO
import os, json, hashlib
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret_key_here"
app.config['UPLOAD_FOLDER'] = os.path.join("data", "uploads")
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join("data", "avatars"), exist_ok=True)

POSTS_FILE = os.path.join("data", "posts.json")
USERS_FILE = os.path.join("data", "users.json")

if not os.path.exists(POSTS_FILE):
    with open(POSTS_FILE, "w") as f:
        json.dump([], f)
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump([], f)

socketio = SocketIO(app)

def load_posts():
    with open(POSTS_FILE, "r") as f:
        return json.load(f)

def save_posts(posts):
    with open(POSTS_FILE, "w") as f:
        json.dump(posts, f, indent=4)

def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def current_user():
    if "user_id" in session:
        users = load_users()
        for u in users:
            if u["id"] == session["user_id"]:
                return u
    return None

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        avatar_file = request.files.get("avatar")
        if not username or not password:
            return redirect(request.url)
        users = load_users()
        if any(u["username"] == username for u in users):
            return "Nom déjà utilisé!"
        avatar_name = ""
        if avatar_file and avatar_file.filename:
            avatar_name = datetime.now().strftime("%Y%m%d%H%M%S_") + avatar_file.filename
            avatar_file.save(os.path.join("data", "avatars", avatar_name))
        user_id = max([u["id"] for u in users], default=0) + 1
        users.append({"id": user_id, "username": username, "password": hash_password(password), "avatar": avatar_name})
        save_users(users)
        session["user_id"] = user_id
        return redirect(url_for("index"))
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        users = load_users()
        for u in users:
            if u["username"] == username and u["password"] == hash_password(password):
                session["user_id"] = u["id"]
                return redirect(url_for("index"))
        return "Identifiants invalides!"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
def index():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    if request.method == "POST":
        description = request.form.get("description", "").strip()
        if "file" not in request.files or not description:
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            return redirect(request.url)
        filename = datetime.now().strftime("%Y%m%d%H%M%S_") + file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        ext = file.filename.lower().split('.')[-1]
        file_type = "video" if ext in ["mp4", "webm", "ogg"] else "image"
        posts = load_posts()
        new_post = {
            "user_id": user["id"],
            "username": user["username"],
            "avatar": user["avatar"],
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
    return render_template("style.html", posts=posts, user=user)

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/avatars/<filename>")
def uploaded_avatar(filename):
    return send_from_directory(os.path.join("data","avatars"), filename)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)

