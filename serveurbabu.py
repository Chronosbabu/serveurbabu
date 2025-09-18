from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session, abort, jsonify
from flask_socketio import SocketIO, emit, join_room
import os, json, hashlib
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import requests
import random
import string

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
BANK_FILE = os.path.join(DATA_DIR, "bank_accounts.json")
CONVERSIONS_FILE = os.path.join(DATA_DIR, "conversions.json")
MATCHES_FILE = os.path.join(DATA_DIR, "matches.json")
BETS_FILE = os.path.join(DATA_DIR, "bets.json")

socketio = SocketIO(app, manage_session=True, cors_allowed_origins="*")

connected_users = set()
user_notifications = {}

FEE_DOLLAR = 2  # Droit mensuel en dollars
FEE_FRANC = 6000  # Droit mensuel en francs
TEST_MODE = True  # Pour tests, 1 minute = 30 jours

@app.template_filter('timestamp')
def timestamp_filter(s):
    return int(datetime.now().timestamp())

def toggle_follow(current_user, target_user):
    users = load_users()
    cu = next((u for u in users if u["username"] == current_user), None)
    if not cu:
        return False
    following_list = cu.setdefault("following", [])
    if target_user in following_list:
        following_list.remove(target_user)
        following = False
    else:
        following_list.append(target_user)
        following = True
    save_users(users)
    return following

def is_following(current_user, target_user):
    users = load_users()
    cu = next((u for u in users if u["username"] == current_user), None)
    if not cu:
        return False
    return target_user in cu.get("following", [])

def notify_like(target_user_id, liker_username, post_id):
    msg = f"{liker_username} a aimé votre publication"
    user_notifications.setdefault(target_user_id, []).append(msg)
    socketio.emit("new_notification", {"message": msg, "post_id": post_id}, room=str(target_user_id))

def notify_comment(target_user_id, commenter_username, post_id):
    msg = f"{commenter_username} a commenté votre publication"
    user_notifications.setdefault(target_user_id, []).append(msg)
    socketio.emit("new_notification", {"message": msg, "post_id": post_id}, room=str(target_user_id))

@socketio.on("join")
def handle_join(data):
    user_id = data.get("user_id")
    if user_id:
        join_room(str(user_id))

for file_path, default in [(DATA_FILE, []), (USER_FILE, []), (MESSAGES_FILE, {}), (BANK_FILE, []), (CONVERSIONS_FILE, []), (MATCHES_FILE, []), (BETS_FILE, [])]:
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)

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

def load_bank():
    with open(BANK_FILE, "r", encoding="utf-8") as f:
        bank = json.load(f)
    if not any(acc["username"] == "platform" for acc in bank):
        bank.append({"username": "platform", "balance_franc": 0, "balance_dollar": 0, "account_id": "00000000", "password": "", "subscription_end": None, "referrer_id": None})
        save_bank(bank)
    return bank

def save_bank(bank):
    with open(BANK_FILE, "w", encoding="utf-8") as f:
        json.dump(bank, f, ensure_ascii=False, indent=2)

def load_matches():
    with open(MATCHES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_matches(matches):
    with open(MATCHES_FILE, "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)

def load_bets():
    with open(BETS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_bets(bets):
    with open(BETS_FILE, "w", encoding="utf-8") as f:
        json.dump(bets, f, ensure_ascii=False, indent=2)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_account_id():
    while True:
        digits = ''.join(random.choice(string.digits) for _ in range(6))
        account_id = '01' + digits
        bank = load_bank()
        if not any(acc.get("account_id") == account_id for acc in bank):
            return account_id

def get_user(username):
    users = load_users()
    return next((u for u in users if u.get("username") == username), None)

def append_message(sender, receiver, text, msg_type="text", url=None):
    messages = load_messages()
    key1 = f"{sender}_{receiver}"
    key2 = f"{receiver}_{sender}"
    now_iso = datetime.now().isoformat()
    entry = {"sender": sender, "text": text, "type": msg_type, "url": url, "date": now_iso, "read_by": [sender]}

    if key1 in messages:
        messages[key1].append(entry)
    elif key2 in messages:
        messages[key2].append(entry)
    else:
        messages[key1] = [entry]

    save_messages(messages)
    return entry

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
            "created_at": datetime.now().isoformat(),
            "following": []
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
            session["user_id"] = user.get("username")
            return redirect(url_for("index"))
        return "Nom ou mot de passe incorrect !", 401
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("avatar", None)
    session.pop("user_id", None)
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
def index():
    if "username" not in session:
        return redirect(url_for("login"))

    posts = load_posts()
    users = {u["username"]: u for u in load_users()}
    for p in posts:
        p['liked_by_user'] = session["username"] in p.get("liked_by", [])
        p['comments_count'] = len(p.get("comments", []))
        p['following'] = is_following(session["username"], p["username"])
        p['avatar'] = users.get(p["username"], {}).get("avatar")
        for comment in p.get("comments", []):
            comment['avatar'] = users.get(comment["username"], {}).get("avatar")
    return render_template("style.html", posts=posts, username=session["username"], avatar=session.get("avatar"))

@app.route("/follow/<username>", methods=["POST"])
def follow_user(username):
    if "username" not in session:
        return jsonify({"error": "Non connecté"}), 401
    current_user = session["username"]
    following = toggle_follow(current_user, username)

    socketio.emit(
        "update_follow",
        {"target_user": username, "follower": current_user, "following": following},
        room=username
    )

    if following:
        msg = f"{current_user} a commencé à vous suivre"
        user_notifications.setdefault(username, []).append(msg)
        socketio.emit("new_notification", {"message": msg}, room=username)

    return jsonify({"following": following})

@app.route("/add_post", methods=["GET", "POST"])
def add_post():
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        content = (request.form.get("content") or "").strip()
        media_files = request.files.getlist("media")
        files_data = []

        for media_file in media_files:
            if media_file and media_file.filename:
                filename = datetime.now().strftime("%Y%m%d%H%M%S_") + secure_filename(media_file.filename)
                media_file.save(os.path.join(UPLOAD_FOLDER, filename))
                ext = os.path.splitext(filename)[1].lower()

                if ext in [".jpg", ".jpeg", ".png", ".gif"]:
                    media_type = "image"
                elif ext in [".mp4", ".mov", ".avi", ".webm"]:
                    media_type = "video"
                else:
                    media_type = "other"

                files_data.append({"name": filename, "type": media_type})

        posts = load_posts()
        new_post = {
            "id": len(posts) + 1,
            "username": session["username"],
            "files": files_data,
            "description": content,
            "likes": 0,
            "liked_by": [],
            "comments": [],
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        posts.insert(0, new_post)
        save_posts(posts)

        socketio.emit('new_post', {
            "id": new_post["id"],
            "username": new_post["username"],
            "description": new_post["description"]
        })

        return redirect(url_for("index"))

    return render_template("new_post.html")

@app.route("/like/<int:post_id>", methods=["POST"])
def like_post(post_id):
    if "username" not in session:
        return jsonify({"error": "Non connecté"}), 401
    posts = load_posts()
    post = next((p for p in posts if p["id"] == post_id), None)
    if not post:
        return jsonify({"error": "Post non trouvé"}), 404

    username = session["username"]
    liked_before = username in post.get("liked_by", [])

    if liked_before:
        post["liked_by"].remove(username)
        liked = False
    else:
        post.setdefault("liked_by", []).append(username)
        liked = True
        post_owner = post.get("username")
        if post_owner != username:
            notify_like(target_user_id=post_owner, liker_username=username, post_id=post_id)

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

    users = {u["username"]: u for u in load_users()}
    if request.method == "POST":
        content = (request.form.get("comment") or "").strip()
        if content:
            next_id = len(post.setdefault("comments", [])) + 1
            comment_data = {
                "id": next_id,
                "username": session["username"],
                "content": content,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            post["comments"].append(comment_data)
            save_posts(posts)
            post_owner = post["username"]
            if post_owner != session["username"]:
                notify_comment(post_owner, session["username"], post_id)
            return jsonify({"comment_id": next_id, "avatar": session.get("avatar")}), 201

    post['avatar'] = users.get(post["username"], {}).get("avatar")
    for comment in post.get("comments", []):
        comment['avatar'] = users.get(comment["username"], {}).get("avatar")
    return render_template("comments.html", post=post, username=session["username"], avatar=session.get("avatar"))

@app.route("/profile/<username>")
def profile(username):
    user = get_user(username)
    if not user:
        abort(404)

    posts = load_posts()
    users = {u["username"]: u for u in load_users()}
    user_posts = [p for p in posts if p.get("username") == user["username"]]
    current_username = session.get("username")
    current_user = get_user(current_username) if current_username else None
    for p in user_posts:
        p['liked_by_user'] = current_username in p.get("liked_by", [])
        p['comments_count'] = len(p.get("comments", []))
        p['following'] = username in current_user.get("following", []) if current_user else False
        p['avatar'] = users.get(p["username"], {}).get("avatar")
        for comment in p.get("comments", []):
            comment['avatar'] = users.get(comment["username"], {}).get("avatar")

    all_users = load_users()
    followers = [u["username"] for u in all_users if username in u.get("following", [])]
    user["followers"] = followers

    return render_template(
        "profile.html",
        profile_user=user,
        posts=user_posts,
        current_username=session.get("username"),
        current_avatar=session.get("avatar")
    )

@app.route("/search", methods=["GET"])
def search_users():
    if "username" not in session:
        return redirect(url_for("login"))

    query = (request.args.get("q") or "").strip().lower()
    users = load_users()
    posts = load_posts()
    users_dict = {u["username"]: u for u in users}

    users_results, posts_results = [], []

    if query:
        users_results = [u for u in users if query in u["username"].lower()]
        posts_results = [p for p in posts if query in p["description"].lower()]
        for p in posts_results:
            p['avatar'] = users_dict.get(p["username"], {}).get("avatar")
            for comment in p.get("comments", []):
                comment['avatar'] = users_dict.get(comment["username"], {}).get("avatar")

    return render_template(
        "search.html",
        users=users_results,
        posts=posts_results,
        current_username=session["username"],
        query=request.args.get("q", "")
    )

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/avatars/<filename>")
def avatar_file(filename):
    return send_from_directory(AVATAR_FOLDER, filename)

@app.route("/send_file", methods=["POST"])
def send_file_route():
    if "username" not in session:
        return jsonify({"success": False, "error": "Non connecté"}), 401

    receiver = request.form.get("recipient", "").strip()
    file = request.files.get("file")
    if not receiver or not file:
        return jsonify({"success": False, "error": "Champs manquants"}), 400

    filename = datetime.now().strftime("%Y%m%d%H%M%S_") + secure_filename(file.filename)
    file.save(os.path.join(UPLOAD_FOLDER, filename))

    ext = os.path.splitext(filename)[1].lower()
    file_type = "text"
    if ext in [".jpg", ".jpeg", ".png", ".gif"]:
        file_type = "image"
    elif ext in [".mp4", ".mov", ".avi"]:
        file_type = "video"
    elif ext in [".mp3", ".wav", ".ogg", ".m4a", ".webm"]:
        file_type = "audio"

    url = url_for("uploaded_file", filename=filename)

    entry = append_message(session["username"], receiver, f"[{file_type}]: {filename}", msg_type=file_type, url=url)
    socketio.emit("new_message", entry, room=receiver)
    socketio.emit("new_message", entry, room=session["username"])

    return jsonify({"success": True, "url": url, "type": file_type})

@app.route("/update_avatar", methods=["POST"])
def update_avatar():
    if "username" not in session:
        return jsonify({"success": False, "error": "Non connecté"}), 401

    file = request.files.get("avatar")
    if not file or not file.filename:
        return jsonify({"success": False, "error": "Aucun fichier sélectionné"}), 400

    username = session["username"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".gif"]:
        return jsonify({"success": False, "error": "Format d'image non supporté"}), 400

    filename = f"{username}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
    file.save(os.path.join(AVATAR_FOLDER, filename))

    users = load_users()
    user = next((u for u in users if u["username"] == username), None)
    if user:
        old_avatar = user.get("avatar")
        user["avatar"] = filename
        save_users(users)
        session["avatar"] = filename
        if old_avatar and os.path.exists(os.path.join(AVATAR_FOLDER, old_avatar)):
            os.remove(os.path.join(AVATAR_FOLDER, old_avatar))
        new_avatar_url = url_for("avatar_file", filename=filename, _external=True) + f"?t={int(datetime.now().timestamp())}"
        socketio.emit("avatar_updated", {"username": username, "new_avatar_url": new_avatar_url})
        return jsonify({"success": True, "avatar_url": new_avatar_url})
    return jsonify({"success": False, "error": "Utilisateur non trouvé"}), 404

@app.route("/posts/<int:post_id>", methods=["DELETE"])
def delete_post(post_id):
    if "username" not in session:
        return jsonify({"success": False, "error": "Non connecté"}), 401

    posts = load_posts()
    post = next((p for p in posts if p["id"] == post_id), None)
    if not post:
        return jsonify({"success": False, "error": "Post non trouvé"}), 404

    if post["username"] != session["username"]:
        return jsonify({"success": False, "error": "Non autorisé"}), 403

    for file in post.get("files", []):
        file_path = os.path.join(UPLOAD_FOLDER, file["name"])
        if os.path.exists(file_path):
            os.remove(file_path)

    posts = [p for p in posts if p["id"] != post_id]
    save_posts(posts)

    socketio.emit("post_deleted", {"post_id": post_id})

    return jsonify({"success": True})

@app.route("/conversations")
def conversations():
    if "username" not in session:
        return redirect(url_for("login"))

    messages = load_messages()
    username = session.get("username")
    users = {u["username"]: u for u in load_users()}
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

        other_user_data = get_user(other_user)
        user_conversations.append({
            "username": other_user,
            "profile_pic": users.get(other_user, {}).get("avatar"),
            "last_msg": last_msg,
            "last_date": last_date,
            "unread_count": sum(1 for m in conv if username not in m.get("read_by", []))
        })

    user_conversations.sort(key=lambda x: x.get("last_date", ""), reverse=True)
    return render_template("conversations.html", conversations=user_conversations)

@app.route("/chat/<username>")
def chat(username):
    if "username" not in session:
        return redirect(url_for("login"))

    messages = load_messages()
    users = {u["username"]: u for u in load_users()}
    key1 = f"{session['username']}_{username}"
    key2 = f"{username}_{session['username']}"
    conv = messages.get(key1) or messages.get(key2) or []
    for msg in conv:
        msg['avatar'] = users.get(msg["sender"], {}).get("avatar")
    return render_template("chat.html", chat_user=username, messages=conv, avatar=session.get("avatar"))

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

    entry = append_message(sender, receiver, text, msg_type="text")
    socketio.emit("new_message", entry, room=receiver)
    socketio.emit("new_message", entry, room=sender)

    return jsonify({"success": True})

@socketio.on("connect")
def handle_connect():
    user = session.get("username")
    if user:
        join_room(user)
        connected_users.add(user)
        emit('user_online', {'username': user}, broadcast=True)

@socketio.on("disconnect")
def handle_disconnect():
    user = session.get("username")
    if user and user in connected_users:
        connected_users.remove(user)
        emit('user_offline', {'username': user}, broadcast=True)

@socketio.on("send_message")
def handle_send_message(data):
    sender = session.get("username")
    receiver = (data.get("receiver") or "").strip()
    text = (data.get("text") or "").strip()
    if not sender or not receiver or not text:
        return

    entry = append_message(sender, receiver, text, msg_type="text")
    emit("new_message", entry, room=receiver)
    emit("new_message", entry, room=sender)

@socketio.on('mark_read')
def mark_read(data):
    user = session.get("username")
    sender = data.get("sender")
    messages = load_messages()
    key1 = f"{sender}_{user}"
    key2 = f"{user}_{sender}"
    conv = messages.get(key1) or messages.get(key2) or []
    for m in conv:
        if user not in m.get("read_by", []):
            m.setdefault("read_by", []).append(user)
    save_messages(messages)
    emit('update_unread', {'from': sender}, room=user)

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
    post_owner = post.get("username")
    if post_owner != data['username']:
        notify_comment(target_user_id=post_owner, commenter_username=data['username'], post_id=post_id)
    avatar = data.get('avatar') or get_user(data['username'])['avatar'] if get_user(data['username']) else None
    date = data.get('date') or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    comment_id = data.get('comment_id') or None
    emit('new_comment', {"post_id": post_id, "comment_id": comment_id, "username": data['username'], "content": content, "avatar": avatar, "date": date})

@app.route("/notifications")
def notifications():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    username = session.get("username")

    notifications_list = user_notifications.get(user_id, [])
    user_notifications[user_id] = []

    return render_template(
        "notifications.html",
        username=username,
        notifications=notifications_list
    )

@socketio.on("join_room")
def handle_join_room(data):
    if isinstance(data, dict):
        username = data.get("username")
    else:
        username = data
    if username:
        join_room(username)

@app.route("/videos")
def videos():
    if "username" not in session:
        return redirect(url_for("login"))

    posts = load_posts()
    users = {u["username"]: u for u in load_users()}

    video_posts = []
    for p in posts:
        has_video = False
        if p.get("type") == "video" and not p.get("files"):
            has_video = True
        elif p.get("files"):
            for file in p["files"]:
                if file["type"] == "video":
                    has_video = True
                    break
        if has_video:
            p['liked_by_user'] = session["username"] in p.get("liked_by", [])
            p['comments_count'] = len(p.get("comments", []))
            p['following'] = is_following(session["username"], p["username"])
            p['avatar'] = users.get(p["username"], {}).get("avatar")
            for comment in p.get("comments", []):
                comment['avatar'] = users.get(comment["username"], {}).get("avatar")
            video_posts.append(p)

    return render_template(
        "videos.html",
        posts=video_posts,
        username=session["username"],
        avatar=session.get("avatar")
    )

@app.route("/user_exists/<username>", methods=["GET"])
def user_exists(username):
    return jsonify({"exists": bool(get_user(username))})

@app.route("/account")
def account():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("account.html")

@app.route("/bank/status", methods=["GET"])
def bank_status():
    if "username" not in session:
        return jsonify({"error": "Non connecté"}), 401
    un = session["username"]
    bank = load_bank()
    acc = next((a for a in bank if a["username"] == un), None)
    return jsonify({"exists": bool(acc)})

@app.route("/bank/check_subscription", methods=["GET"])
def check_subscription():
    if "username" not in session:
        return jsonify({"error": "Non connecté"}), 401
    un = session["username"]
    bank = load_bank()
    acc = next((a for a in bank if a["username"] == un), None)
    if not acc:
        return jsonify({"error": "Compte non trouvé"}), 404
    if not acc.get("subscription_end") or datetime.now() > datetime.fromisoformat(acc["subscription_end"]):
        return jsonify({"success": False, "error": "Abonnement non valide ou expiré"})
    return jsonify({"success": True})

@app.route("/bank/create", methods=["POST"])
def bank_create():
    if "username" not in session:
        return jsonify({"error": "Non connecté"}), 401
    data = request.json
    pwd = data.get("password")
    referral_id = data.get("referral_id", "")
    if not pwd:
        return jsonify({"error": "Mot de passe requis"}), 400
    un = session["username"]
    bank = load_bank()
    if next((a for a in bank if a["username"] == un), None):
        return jsonify({"error": "Compte existe déjà"}), 400
    if referral_id:
        referrer = next((a for a in bank if a.get("account_id") == referral_id), None)
        if not referrer:
            referral_id = ""  # Ignorer si invalide
    account_id = generate_account_id()
    bank.append({
        "username": un,
        "password": hash_password(pwd),
        "balance_franc": 0.0,
        "balance_dollar": 0.0,
        "account_id": account_id,
        "referrer_id": referral_id,
        "subscription_end": None
    })
    save_bank(bank)
    return jsonify({"success": True, "account_id": account_id})

@app.route("/bank/login", methods=["POST"])
def bank_login():
    if "username" not in session:
        return jsonify({"error": "Non connecté"}), 401
    data = request.json
    pwd = data.get("password")
    if not pwd:
        return jsonify({"error": "Mot de passe requis"}), 400
    un = session["username"]
    bank = load_bank()
    acc = next((a for a in bank if a["username"] == un), None)
    if not acc:
        return jsonify({"error": "Compte non trouvé"}), 404
    if acc["password"] != hash_password(pwd):
        return jsonify({"error": "Mot de passe incorrect"}), 401
    return jsonify({
        "success": True,
        "balances": {
            "franc": float(acc["balance_franc"]),
            "dollar": float(acc["balance_dollar"])
        },
        "account_id": acc.get("account_id", "")
    })

@app.route("/bank/get_username_by_id", methods=["POST"])
def get_username_by_id():
    data = request.json
    account_id = data.get("account_id")
    if not account_id:
        return jsonify({"error": "ID requis"}), 400
    bank = load_bank()
    acc = next((a for a in bank if a.get("account_id") == account_id), None)
    if not acc:
        return jsonify({"error": "ID non trouvé"}), 404
    return jsonify({"success": True, "username": acc["username"]})

@app.route("/bank/convert", methods=["POST"])
def bank_convert():
    if "username" not in session:
        return jsonify({"error": "Non connecté"}), 401
    data = request.json
    currency = data.get("currency")
    amount = data.get("amount")
    phone = data.get("phone")
    if not all([currency, amount is not None, phone]) or not isinstance(amount, (int, float)) or amount <= 0:
        return jsonify({"error": "Données invalides ou montant non valide"}), 400
    if currency not in ["franc", "dollar"]:
        return jsonify({"error": "Devise invalide"}), 400
    bank = load_bank()
    un = session["username"]
    acc = next((a for a in bank if a["username"] == un), None)
    if not acc:
        return jsonify({"error": "Compte non trouvé"}), 404
    if not acc.get("subscription_end") or datetime.now() > datetime.fromisoformat(acc["subscription_end"]):
        return jsonify({"error": "Payez le droit mensuel"}), 400
    key = f"balance_{currency}"
    if key not in acc or float(acc[key]) < float(amount):
        return jsonify({"error": f"Solde insuffisant en {currency}. Solde disponible: {acc[key]}"}), 400
    acc[key] = float(acc[key]) - float(amount)
    save_bank(bank)
    convs = []
    with open(CONVERSIONS_FILE, "r", encoding="utf-8") as f:
        convs = json.load(f)
    convs.append({"username": un, "phone": phone, "amount": float(amount), "currency": currency, "timestamp": datetime.now().isoformat()})
    with open(CONVERSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(convs, f, ensure_ascii=False, indent=2)
    currency_name = "francs" if currency == "franc" else "dollars"
    socketio.emit("balance_updated", {
        "username": acc["username"],
        "balance_franc": float(acc["balance_franc"]),
        "balance_dollar": float(acc["balance_dollar"]),
        "account_id": acc["account_id"]
    }, room=acc["username"])
    return jsonify({
        "success": True,
        "message": f"Vous avez converti {amount:.2f} {currency_name} à {phone}. Attendez votre réponse dans 5 heures du temps."
    })

@app.route("/bank/transfer", methods=["POST"])
def bank_transfer():
    if "username" not in session:
        return jsonify({"error": "Non connecté"}), 401
    data = request.json
    recipient_account_id = data.get("recipient_account_id")
    currency = data.get("currency")
    amount = data.get("amount")
    password = data.get("password")
    if not all([recipient_account_id, currency, amount is not None, password]) or not isinstance(amount, (int, float)) or amount <= 0:
        return jsonify({"error": "Données invalides ou montant non valide"}), 400
    if currency not in ["franc", "dollar"]:
        return jsonify({"error": "Devise invalide"}), 400
    bank = load_bank()
    sender = next((a for a in bank if a["username"] == session["username"]), None)
    if not sender:
        return jsonify({"error": "Compte émetteur non trouvé"}), 404
    if sender["password"] != hash_password(password):
        return jsonify({"error": "Mot de passe incorrect"}), 401
    if not sender.get("subscription_end") or datetime.now() > datetime.fromisoformat(sender["subscription_end"]):
        return jsonify({"error": "Abonnement non valide ou expiré"}), 400
    recipient = next((a for a in bank if a["account_id"] == recipient_account_id), None)
    if not recipient:
        return jsonify({"error": "Compte destinataire non trouvé"}), 404
    key = f"balance_{currency}"
    if key not in sender or float(sender[key]) < float(amount):
        return jsonify({"error": f"Solde insuffisant en {currency}. Solde disponible: {sender[key]}"}), 400
    sender[key] = float(sender[key]) - float(amount)
    recipient[key] = float(recipient[key]) + float(amount)
    save_bank(bank)
    currency_name = "francs" if currency == "franc" else "dollars"
    socketio.emit("balance_updated", {
        "username": sender["username"],
        "balance_franc": float(sender["balance_franc"]),
        "balance_dollar": float(sender["balance_dollar"]),
        "account_id": sender["account_id"]
    }, room=sender["username"])
    socketio.emit("balance_updated", {
        "username": recipient["username"],
        "balance_franc": float(recipient["balance_franc"]),
        "balance_dollar": float(recipient["balance_dollar"]),
        "account_id": recipient["account_id"]
    }, room=recipient["username"])
    return jsonify({
        "success": True,
        "message": f"Vous avez transféré {amount:.2f} {currency_name} à {recipient['username']}."
    })

@app.route("/pay_subscription", methods=["POST"])
def pay_subscription():
    data = request.json
    account_id = data.get("account_id")
    currency = data.get("currency")
    if not account_id or not currency:
        return jsonify({"error": "Données invalides"}), 400
    bank = load_bank()
    acc = next((a for a in bank if a.get("account_id") == account_id), None)
    if not acc:
        return jsonify({"error": "Compte non trouvé"}), 404
    platform = next((a for a in bank if a["username"] == "platform"), None)
    if not platform:
        return jsonify({"error": "Plateforme non trouvée"}), 500
    fee = FEE_FRANC if currency == "franc" else FEE_DOLLAR
    key = "balance_franc" if currency == "franc" else "balance_dollar"
    if acc[key] < fee:
        return jsonify({"error": f"Solde insuffisant pour payer les frais ({fee} {currency})"}), 400
    acc[key] -= fee
    platform[key] += fee * 0.7  # 70% à la plateforme
    referrer_id = acc.get("referrer_id")
    if referrer_id:
        referrer = next((a for a in bank if a.get("account_id") == referrer_id), None)
        if referrer:
            referrer[key] += fee * 0.3  # 30% à l'inviteur
    delta = timedelta(minutes=1) if TEST_MODE else timedelta(days=30)
    acc["subscription_end"] = (datetime.now() + delta).isoformat()
    save_bank(bank)
    socketio.emit("balance_updated", {
        "username": acc["username"],
        "balance_franc": float(acc["balance_franc"]),
        "balance_dollar": float(acc["balance_dollar"]),
        "account_id": acc["account_id"]
    }, room=acc["username"])
    return jsonify({"success": True})

@app.route("/bank/platform_balance", methods=["GET"])
def platform_balance():
    bank = load_bank()
    platform = next((a for a in bank if a["username"] == "platform"), None)
    if not platform:
        return jsonify({"error": "Plateforme non trouvée"}), 500
    return jsonify({"franc": float(platform["balance_franc"]), "dollar": float(platform["balance_dollar"])})

@app.route("/deposit", methods=["POST"])
def deposit():
    data = request.json
    account_id = data.get("account_id")
    franc = data.get("franc", 0)
    dollar = data.get("dollar", 0)
    if not account_id or (franc == 0 and dollar == 0):
        return jsonify({"error": "Données invalides"}), 400
    bank = load_bank()
    acc = next((a for a in bank if a.get("account_id") == account_id), None)
    if not acc:
        return jsonify({"error": "Compte non trouvé"}), 404
    acc["balance_franc"] = float(acc["balance_franc"]) + float(franc)
    acc["balance_dollar"] = float(acc["balance_dollar"]) + float(dollar)
    save_bank(bank)
    socketio.emit("balance_updated", {
        "username": acc["username"],
        "balance_franc": float(acc["balance_franc"]),
        "balance_dollar": float(acc["balance_dollar"]),
        "account_id": acc["account_id"]
    }, room=acc["username"])
    return jsonify({"success": True, "message": f"Vous avez déposé {franc:.2f} francs et {dollar:.2f} dollars pour l'ID {account_id} ({acc['username']})"})

@app.route("/conversions", methods=["GET"])
def get_conversions():
    convs = []
    with open(CONVERSIONS_FILE, "r", encoding="utf-8") as f:
        convs = json.load(f)
    return jsonify(convs)

@app.route("/pari")
def pari():
    if "username" not in session:
        return redirect(url_for("login"))
    matches = [m for m in load_matches() if not m.get("result")]
    return render_template("pari.html", matches=matches, username=session["username"])

@app.route("/publish_match", methods=["POST"])
def publish_match():
    data = request.json
    team1 = data.get("team1")
    odd1 = data.get("odd1")
    team2 = data.get("team2")
    odd2 = data.get("odd2")
    odd_draw = data.get("odd_draw", 0)
    bet_end_time_str = data.get("bet_end_time")
    if not team1 or not team2 or not odd1 or not odd2 or not bet_end_time_str:
        return jsonify({"error": "Équipes, cotes et heure de fin des paris requises"}), 400
    try:
        bet_end_time = datetime.fromisoformat(bet_end_time_str)
    except ValueError:
        return jsonify({"error": "Format d'heure invalide"}), 400
    matches = load_matches()
    match_id = len(matches) + 1
    new_match = {
        "id": match_id,
        "team1": team1,
        "odd_team1": float(odd1),
        "team2": team2,
        "odd_team2": float(odd2),
        "odd_draw": float(odd_draw),
        "bet_end_time": bet_end_time.isoformat(),
        "result": None
    }
    matches.append(new_match)
    save_matches(matches)
    socketio.emit("new_match", new_match)
    return jsonify({"success": True, "match": new_match})

@app.route("/publish_result", methods=["POST"])
def publish_result():
    data = request.json
    match_id = data.get("match_id")
    result = data.get("result")  # "team1", "team2" ou "0" pour nul
    matches = load_matches()
    match = next((m for m in matches if m["id"] == match_id), None)
    if not match:
        return jsonify({"error": "Match non trouvé"}), 404
    if match.get("result"):
        return jsonify({"error": "Résultat déjà publié"}), 400
    match["result"] = result
    save_matches(matches)

    # Distribuer les gains
    bets = load_bets()
    bank = load_bank()
    platform = next((a for a in bank if a["username"] == "platform"), None)
    for bet in bets:
        if bet["match_id"] == match_id:
            odd = 0
            if bet["choice"] == "1" and result == match["team1"]:
                odd = match["odd_team1"]
            elif bet["choice"] == "2" and result == match["team2"]:
                odd = match["odd_team2"]
            elif bet["choice"] == "0" and result == "0":
                odd = match["odd_draw"]
            if odd > 0:
                acc = next((a for a in bank if a["username"] == bet["username"]), None)
                if acc:
                    key = "balance_franc" if bet["currency"] == "franc" else "balance_dollar"
                    gain = bet["amount"] * odd
                    acc[key] = float(acc[key]) + float(gain)
                    platform[key] = float(platform[key]) - (float(gain) - float(bet["amount"]))  # Net payment from platform
                    socketio.emit("balance_updated", {
                        "username": bet["username"],
                        "balance_franc": float(acc["balance_franc"]),
                        "balance_dollar": float(acc["balance_dollar"]),
                        "account_id": acc["account_id"]
                    }, room=bet["username"])
    save_bets(bets)
    save_bank(bank)
    socketio.emit("match_result", {"match_id": match_id, "result": result})
    return jsonify({"success": True})

@app.route("/place_bet", methods=["POST"])
def place_bet():
    if "username" not in session:
        return jsonify({"error": "Non connecté"}), 401
    data = request.json
    match_id = data.get("match_id")
    choice = data.get("choice")
    currency = data.get("currency")
    amount = data.get("amount")
    pwd = data.get("password")
    if not all([match_id, choice, currency, amount, pwd]):
        return jsonify({"error": "Données manquantes"}), 400

    matches = load_matches()
    match = next((m for m in matches if m["id"] == match_id and not m.get("result")), None)
    if not match:
        return jsonify({"error": "Match non disponible"}), 404

    bet_end_time = datetime.fromisoformat(match.get("bet_end_time"))
    if datetime.now() > bet_end_time:
        return jsonify({"error": "Pari indisponible, le match a déjà commencé"}), 400

    bets = load_bets()
    if any(b["username"] == session["username"] and b["match_id"] == match_id for b in bets):
        return jsonify({"error": "Pari impossible car vous avez déjà parié pour ce match"}), 400

    bank = load_bank()
    acc = next((a for a in bank if a["username"] == session["username"]), None)
    if not acc or acc["password"] != hash_password(pwd):
        return jsonify({"error": "Mot de passe incorrect ou compte non trouvé"}), 401

    key = "balance_franc" if currency == "franc" else "balance_dollar"
    if float(acc[key]) < float(amount):
        return jsonify({"error": f"Solde insuffisant en {currency}. Solde disponible: {acc[key]}"}, 400)

    platform = next((a for a in bank if a["username"] == "platform"), None)
    acc[key] = float(acc[key]) - float(amount)
    platform[key] = float(platform[key]) + float(amount)
    save_bank(bank)

    bets.append({
        "username": session["username"],
        "match_id": match_id,
        "choice": choice,
        "amount": float(amount),
        "currency": currency
    })
    save_bets(bets)

    return jsonify({"success": True, "message": "Pari placé avec succès"})

@app.route("/get_matches", methods=["GET"])
def get_matches():
    matches = [m for m in load_matches() if not m.get("result")]
    return jsonify(matches)

@app.route("/get_balances", methods=["GET"])
def get_balances():
    if "username" not in session:
        return jsonify({"error": "Non connecté"}), 401
    un = session["username"]
    bank = load_bank()
    acc = next((a for a in bank if a["username"] == un), None)
    if not acc:
        return jsonify({"error": "Compte non trouvé"}), 404
    return jsonify({
        "balances": {
            "franc": float(acc["balance_franc"]),
            "dollar": float(acc["balance_dollar"])
        },
        "account_id": acc["account_id"]
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port)
