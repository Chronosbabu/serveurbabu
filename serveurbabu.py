from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session, abort, jsonify
from flask_socketio import SocketIO, emit, join_room
import os, json, hashlib
from datetime import datetime, timedelta, timezone
from werkzeug.utils import secure_filename
import requests
import random
import string
import threading
import time
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import uuid
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret_key_here")  # Use Render env or fallback

# Load Google OAuth credentials from Render environment variables
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

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
STORIES_FILE = os.path.join(DATA_DIR, "stories.json")

socketio = SocketIO(app, manage_session=True, cors_allowed_origins="*")

connected_users = set()
user_notifications = {}

FEE_DOLLAR = 2
FEE_FRANC = 6000
TEST_MODE = True

BOOST_TARIFFS = {
    'franc': {
        1: 5000,
        7: 20000,
        30: 100000,
        365: 500000
    },
    'dollar': {
        1: 2,
        7: 8,
        30: 36,
        365: 180
    }
}

@app.template_filter('timestamp')
def timestamp_filter(s):
    return int(datetime.now(timezone.utc).timestamp())

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
    users = load_users()
    liker = next((u for u in users if u["username"] == liker_username), None)
    avatar_url = url_for('avatar_file', filename=liker["avatar"], _external=True) + f"?t={int(datetime.now(timezone.utc).timestamp())}" if liker and liker.get("avatar") else None
    user_notifications.setdefault(target_user_id, []).append({"type": "like", "sender": liker_username, "message": f"{liker_username} a aimé votre publication", "post_id": post_id, "avatar": avatar_url})
    socketio.emit("new_notification", {"type": "like", "sender": liker_username, "message": f"{liker_username} a aimé votre publication", "post_id": post_id, "avatar": avatar_url}, room=str(target_user_id), namespace='/')

def notify_comment(target_user_id, commenter_username, post_id):
    users = load_users()
    commenter = next((u for u in users if u["username"] == commenter_username), None)
    avatar_url = url_for('avatar_file', filename=commenter["avatar"], _external=True) + f"?t={int(datetime.now(timezone.utc).timestamp())}" if commenter and commenter.get("avatar") else None
    user_notifications.setdefault(target_user_id, []).append({"type": "comment", "sender": commenter_username, "message": f"{commenter_username} a commenté votre publication", "post_id": post_id, "avatar": avatar_url})
    socketio.emit("new_notification", {"type": "comment", "sender": commenter_username, "message": f"{commenter_username} a commenté votre publication", "post_id": post_id, "avatar": avatar_url}, room=str(target_user_id), namespace='/')

@socketio.on("join", namespace='/')
def handle_join(data):
    user_id = data.get("user_id")
    if user_id:
        join_room(str(user_id), namespace='/')

for file_path, default in [(DATA_FILE, []), (USER_FILE, []), (MESSAGES_FILE, {}), (BANK_FILE, []), (CONVERSIONS_FILE, []), (STORIES_FILE, [])]:
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
        bank.append({"username": "platform", "balance_franc": 0, "balance_dollar": 0, "account_id": "00000000", "password": "", "subscription_end": None, "referrer_id": None, "referrals_count": 0})
        save_bank(bank)
    # Ensure referrals_count exists for all accounts
    for acc in bank:
        if "referrals_count" not in acc:
            acc["referrals_count"] = 0
    save_bank(bank)
    return bank

def save_bank(bank):
    with open(BANK_FILE, "w", encoding="utf-8") as f:
        json.dump(bank, f, ensure_ascii=False, indent=2)

def load_stories():
    if not os.path.exists(STORIES_FILE):
        return []
    with open(STORIES_FILE, "r", encoding="utf-8") as f:
        stories = json.load(f)
    now = datetime.now(timezone.utc)
    active_stories = []
    for s in stories:
        if "viewers" not in s:
            s["viewers"] = []
        if now < datetime.fromisoformat(s["timestamp"]) + timedelta(hours=24):
            active_stories.append(s)
    if len(active_stories) < len(stories):
        save_stories(active_stories)
    return active_stories

def save_stories(stories):
    with open(STORIES_FILE, "w", encoding="utf-8") as f:
        json.dump(stories, f, ensure_ascii=False, indent=2)

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
    now_iso = datetime.now(timezone.utc).isoformat()
    entry = {"sender": sender, "text": text, "type": msg_type, "url": url, "date": now_iso, "read_by": [sender], "delivered_to": [] if receiver not in connected_users else [receiver]}
    if key1 in messages:
        messages[key1].append(entry)
        key = key1
    elif key2 in messages:
        messages[key2].append(entry)
        key = key2
    else:
        messages[key1] = [entry]
        key = key1
    save_messages(messages)
    return entry, messages, key

def recommend_posts(post_list, interacted_posts, current_user):
    if not post_list or not interacted_posts:
        return sorted(post_list, key=lambda p: datetime.fromisoformat(p["date"]).timestamp(), reverse=True)
    
    # Extract features for ranking
    now = datetime.now(timezone.utc)
    all_descriptions = [p["description"] for p in post_list]
    interacted_descriptions = [p["description"] for p in interacted_posts]
    
    # Content similarity using TF-IDF
    try:
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(all_descriptions + interacted_descriptions)
        tfidf_posts = tfidf_matrix[:len(post_list)]
        tfidf_interacted = tfidf_matrix[len(post_list):]
        content_scores = cosine_similarity(tfidf_posts, tfidf_interacted).mean(axis=1)
    except Exception as e:
        print(f"TF-IDF error: {e}")
        content_scores = np.zeros(len(post_list))

    # Engagement and recency scores
    scores = []
    like_ids = set(current_user.get("liked_posts", []))
    view_ids = set(current_user.get("viewed_posts", []))
    following = set(current_user.get("following", []))
    
    for i, post in enumerate(post_list):
        # Engagement score: likes, comments, and shares
        engagement = post.get("likes", 0) * 0.5 + len(post.get("comments", [])) * 0.3
        # Recency score: newer posts get higher weight
        post_time = datetime.fromisoformat(post["date"]).timestamp()
        time_diff = (now.timestamp() - post_time) / (24 * 3600)  # Days since post
        recency_score = max(0, 1 - time_diff / 7)  # Decay over 7 days
        # Connection score: boost if from followed user
        connection_score = 2.0 if post["username"] in following else 1.0
        # Interaction score: boost if user liked or viewed
        interaction_score = 2.0 if post["id"] in like_ids else 1.5 if post["id"] in view_ids else 1.0
        # Combine scores (weights tuned to mimic Facebook's emphasis)
        total_score = (content_scores[i] * 0.4 + engagement * 0.3 + recency_score * 0.2) * connection_score * interaction_score
        scores.append(total_score)
    
    # Sort posts by score
    sorted_indices = np.argsort(scores)[::-1]
    return [post_list[i] for i in sorted_indices]

def get_sorted_posts(posts, current_user, filter_videos=False):
    now = datetime.now(timezone.utc)
    username = current_user.get("username")
    
    # Separate boosted and non-boosted posts
    boosted = [p for p in posts if p.get("boost_end") and datetime.fromisoformat(p["boost_end"]) > now]
    boosted_unseen = [p for p in boosted if username not in p.get("boosted_viewed_by", [])]
    boosted_seen = [p for p in boosted if p not in boosted_unseen]
    
    # Sort boosted unseen posts by recency
    boosted_unseen.sort(key=lambda p: datetime.fromisoformat(p["boost_start"]).timestamp(), reverse=True)
    non_boosted = [p for p in posts if p not in boosted]
    
    # Split non-boosted into followed and other posts
    following = current_user.get("following", [])
    followed_posts = [p for p in non_boosted if p["username"] in following]
    other_posts = [p for p in non_boosted if p["username"] not in following]
    
    # Get interacted posts for personalization
    interacted_post_ids = list(set(current_user.get("liked_posts", []) + current_user.get("viewed_posts", [])))
    interacted_posts = [p for p in posts if p["id"] in interacted_post_ids]
    
    # Rank posts using enhanced recommendation
    rec_followed = recommend_posts(followed_posts, interacted_posts, current_user)
    rec_other = recommend_posts(other_posts, interacted_posts, current_user)
    
    # Interleave posts for diversity
    final_posts = []
    boosted_index = 0
    followed_index = 0
    other_index = 0
    max_boosted = min(len(boosted_unseen), 3)  # Limit boosted posts
    
    while boosted_index < len(boosted_unseen) or followed_index < len(rec_followed) or other_index < len(rec_other):
        # Prioritize boosted unseen posts (mimicking Facebook ads)
        if boosted_index < max_boosted and boosted_index < len(boosted_unseen):
            final_posts.append(boosted_unseen[boosted_index])
            boosted_index += 1
        # Add followed posts
        elif followed_index < len(rec_followed):
            final_posts.append(rec_followed[followed_index])
            followed_index += 1
        # Add other posts
        elif other_index < len(rec_other):
            final_posts.append(rec_other[other_index])
            other_index += 1
        else:
            # Add remaining boosted unseen posts
            if boosted_index < len(boosted_unseen):
                final_posts.append(boosted_unseen[boosted_index])
                boosted_index += 1
    
    # Append seen boosted posts at the end
    final_posts.extend(boosted_seen)
    
    if filter_videos:
        video_posts = [p for p in final_posts if p.get("type") == "video" or any(f["type"] == "video" for f in p.get("files", []))]
        return video_posts
    
    return final_posts

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        prenom = (request.form.get("prenom") or "").strip()
        nom = (request.form.get("nom") or "").strip()
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip()
        telephone = (request.form.get("telephone") or "").strip()
        password = (request.form.get("password") or "").strip()
        confirm_password = (request.form.get("confirm_password") or "").strip()
        avatar_file = request.files.get("avatar")
        if not all([prenom, nom, username, email, telephone, password, confirm_password]):
            return "Tous les champs sont requis.", 400
        if password != confirm_password:
            return "Les mots de passe ne correspondent pas.", 400
        users = load_users()
        if any(u["username"].lower() == username.lower() for u in users):
            return "Nom d'utilisateur déjà pris !", 400
        if any(u["email"].lower() == email.lower() for u in users):
            return "Email déjà utilisé !", 400
        if any(u["telephone"] == telephone for u in users):
            return "Numéro de téléphone déjà utilisé !", 400
        avatar_filename = None
        if avatar_file and avatar_file.filename:
            avatar_filename = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S_") + secure_filename(avatar_file.filename)
            avatar_file.save(os.path.join(AVATAR_FOLDER, avatar_filename))
        users.append({
            "prenom": prenom,
            "nom": nom,
            "username": username,
            "email": email,
            "telephone": telephone,
            "password": hash_password(password),
            "avatar": avatar_filename,
            "bio": "",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "following": [],
            "liked_posts": [],
            "viewed_posts": []
        })
        save_users(users)
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/recuperer", methods=["GET", "POST"])
def recuperer():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        telephone = (request.form.get("telephone") or "").strip()
        if not email or not telephone:
            return render_template("recuperer.html", error="Email et numéro de téléphone requis.")
        users = load_users()
        user = next((u for u in users if u["email"].lower() == email.lower() and u["telephone"] == telephone), None)
        if not user:
            return render_template("recuperer.html", error="Email ou numéro de téléphone incorrect.")
        session["recovery_user"] = user["username"]
        return redirect(url_for("reset_password"))
    return render_template("recuperer.html")

@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if "recovery_user" not in session:
        return redirect(url_for("recuperer"))
    if request.method == "POST":
        new_password = (request.form.get("new_password") or "").strip()
        confirm_password = (request.form.get("confirm_password") or "").strip()
        if not new_password or not confirm_password:
            return render_template("reset_password.html", error="Nouveau mot de passe requis.")
        if new_password != confirm_password:
            return render_template("reset_password.html", error="Les mots de passe ne correspondent pas.")
        users = load_users()
        user = next((u for u in users if u["username"] == session["recovery_user"]), None)
        if not user:
            session.pop("recovery_user", None)
            return redirect(url_for("recuperer"))
        user["password"] = hash_password(new_password)
        save_users(users)
        session.pop("recovery_user", None)
        return redirect(url_for("login"))
    return render_template("reset_password.html")

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
        return render_template("login.html", error="Nom ou mot de passe incorrect !", google_client_id=GOOGLE_CLIENT_ID)
    return render_template("login.html", google_client_id=GOOGLE_CLIENT_ID)

@app.route("/google_login", methods=["POST"])
def google_login():
    data = request.get_json()
    token = data.get("id_token")
    if not token:
        return jsonify({"error": "Token manquant"}), 400
    try:
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
        email = idinfo.get("email")
        name = idinfo.get("name", email.split("@")[0])
        users = load_users()
        user = next((u for u in users if u.get("google_email") == email or u["username"].lower() == name.lower()), None)
        if not user:
            user = {
                "username": name,
                "password": "",  # No password for Google login
                "avatar": None,
                "bio": "",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "following": [],
                "liked_posts": [],
                "viewed_posts": [],
                "google_email": email
            }
            users.append(user)
            save_users(users)
        session["username"] = user["username"]
        session["avatar"] = user.get("avatar")
        session["user_id"] = user["username"]
        user_info = {
            "username": user["username"],
            "avatar": user.get("avatar"),
            "user_id": user["username"],
            "bio": user.get("bio", ""),
            "created_at": user.get("created_at"),
            "following": user.get("following", []),
            "google_email": user.get("google_email", "")
        }
        return jsonify({"success": True, "redirect": url_for("index"), "user": user_info})
    except ValueError as e:
        return jsonify({"error": "Token invalide: " + str(e)}), 400

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
    users_list = load_users()
    current_user = next((u for u in users_list if u["username"] == session["username"]), None)
    if not current_user:
        session.pop("username", None)
        session.pop("avatar", None)
        session.pop("user_id", None)
        return redirect(url_for("login"))
    posts = get_sorted_posts(posts, current_user)
    users = {u["username"]: u for u in users_list}
    for p in posts:
        p['liked_by_user'] = session["username"] in p.get("liked_by", [])
        p['comments_count'] = len(p.get("comments", []))
        p['following'] = is_following(session["username"], p["username"])
        p['avatar'] = users.get(p["username"], {}).get("avatar")
        for comment in p.get("comments", []):
            comment['avatar'] = users.get(comment["username"], {}).get("avatar")
    following = current_user.get("following", [])
    all_stories = load_stories()
    stories_by_user = {}
    for s in all_stories:
        if s["username"] == session["username"] or s["username"] in following:
            stories_by_user.setdefault(s["username"], []).append(s)
    for user_stories in stories_by_user.values():
        user_stories.sort(key=lambda s: datetime.fromisoformat(s["timestamp"]))
    own_stories = stories_by_user.get(session["username"], [])
    other_stories_users = [u for u in following if u in stories_by_user]
    return render_template("style.html", posts=posts, username=session["username"], avatar=session.get("avatar"), own_stories=own_stories, other_stories_users=other_stories_users, stories_by_user=stories_by_user, users=users)

@app.route("/get_stories/<username>")
def get_stories(username):
    if "username" not in session:
        return jsonify({"error": "Non connecté"}), 401
    current_user = get_user(session["username"])
    if not current_user or (username != session["username"] and username not in current_user.get("following", [])):
        return jsonify({"error": "Non autorisé"}), 403
    stories = load_stories()
    user_stories = [s for s in stories if s["username"] == username]
    user_stories.sort(key=lambda x: datetime.fromisoformat(x["timestamp"]))
    stories_data = []
    users = load_users()
    is_own = username == session["username"]
    for s in user_stories:
        data = {
            "id": s["id"],
            "media_url": url_for('uploaded_file', filename=s["file"], _external=True),
            "type": s["type"]
        }
        viewers = s.get("viewers", [])
        data["viewer_count"] = len(viewers)
        if is_own:
            data["viewers"] = []
            for v in viewers:
                user = next((u for u in users if u["username"] == v), None)
                if user:
                    data["viewers"].append({
                        "username": v,
                        "avatar": user.get("avatar")
                    })
        stories_data.append(data)
    return jsonify({"stories": stories_data, "is_own": is_own})

@app.route("/view_story/<story_id>", methods=["POST"])
def view_story(story_id):
    if "username" not in session:
        return jsonify({"error": "Non connecté"}), 401
    stories = load_stories()
    story = next((s for s in stories if s["id"] == story_id), None)
    if not story:
        return jsonify({"error": "Story non trouvée"}), 404
    viewer = session["username"]
    if viewer == story["username"]:
        return jsonify({"success": True}), 200  # Owner doesn't count as viewer
    viewers = story.setdefault("viewers", [])
    if viewer not in viewers:
        viewers.append(viewer)
        save_stories(stories)
    return jsonify({"success": True}), 200

@app.route("/follow/<username>", methods=["POST"])
def follow_user(username):
    if "username" not in session:
        return jsonify({"error": "Non connecté"}), 401
    current_user = session["username"]
    following = toggle_follow(current_user, username)
    socketio.emit(
        "update_follow",
        {"target_user": username, "follower": current_user, "following": following},
        room=username,
        namespace='/'
    )
    if following:
        users = load_users()
        follower = next((u for u in users if u["username"] == current_user), None)
        avatar_url = url_for('avatar_file', filename=follower["avatar"], _external=True) + f"?t={int(datetime.now(timezone.utc).timestamp())}" if follower and follower.get("avatar") else None
        msg = f"{current_user} a commencé à vous suivre"
        user_notifications.setdefault(username, []).append({"type": "follow", "sender": current_user, "message": msg, "avatar": avatar_url})
        socketio.emit("new_notification", {"type": "follow", "sender": current_user, "message": msg, "avatar": avatar_url}, room=username, namespace='/')
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
                filename = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S_") + secure_filename(media_file.filename)
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
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "boosted_viewed_by": []
        }
        posts.insert(0, new_post)
        save_posts(posts)
        socketio.emit('new_post', {
            "id": new_post["id"],
            "username": new_post["username"],
            "description": new_post["description"]
        }, namespace='/')
        return redirect(url_for("index"))
    return render_template("new_post.html")

@app.route("/add_story", methods=["POST"])
def add_story():
    if "username" not in session:
        return jsonify({"error": "Non connecté"}), 401
    files = request.files.getlist("file")
    if not files:
        return jsonify({"error": "Aucun fichier sélectionné"}), 400
    username = session["username"]
    stories = load_stories()
    new_stories = []
    for file in files:
        if file.filename:
            filename = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S_") + secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            ext = os.path.splitext(filename)[1].lower()
            if ext in [".jpg", ".jpeg", ".png", ".gif"]:
                media_type = "image"
            elif ext in [".mp4", ".mov", ".avi", ".webm"]:
                media_type = "video"
            else:
                continue
            new_story = {
                "id": str(uuid.uuid4()),
                "username": username,
                "file": filename,
                "type": media_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "viewers": []
            }
            stories.append(new_story)
            new_stories.append(new_story)
    save_stories(stories)
    return jsonify({"success": True})

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
    users = load_users()
    user = next((u for u in users if u["username"] == username), None)
    if user:
        liked_posts = user.setdefault("liked_posts", [])
        if liked:
            if post_id not in liked_posts:
                liked_posts.append(post_id)
        else:
            if post_id in liked_posts:
                liked_posts.remove(post_id)
        save_users(users)
    socketio.emit('update_like', {"post_id": post_id, "likes": post["likes"], "user": username}, namespace='/')
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
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
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
    bank = load_bank()
    acc = next((a for a in bank if a["username"] == username), None)
    referrals_count = acc.get("referrals_count", 0) if acc else 0
    user_posts = [p for p in posts if p.get("username") == user["username"]]
    current_username = session.get("username")
    current_user = get_user(current_username) if current_username else None
    for p in user_posts:
        p['liked_by_user'] = current_username in p.get("liked_by", []) if current_username else False
        p['comments_count'] = len(p.get("comments", []))
        p['following'] = username in current_user.get("following", []) if current_user else False
        p['avatar'] = users.get(p["username"], {}).get("avatar")
        for comment in p.get("comments", []):
            comment['avatar'] = users.get(comment["username"], {}).get("avatar")
    all_users = load_users()
    followers = [u["username"] for u in all_users if username in u.get("following", [])]
    user["followers"] = followers
    user["referrals_count"] = referrals_count
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
        current_username = session["username"]
        for p in posts_results:
            p['liked_by_user'] = current_username in p.get("liked_by", [])
            p['comments_count'] = len(p.get("comments", []))
            p['following'] = is_following(current_username, p["username"])
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
    filename = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S_") + secure_filename(file.filename)
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
    entry, messages, key = append_message(session["username"], receiver, f"[{file_type}]: {filename}", msg_type=file_type, url=url)
    entry['id'] = str(uuid.uuid4())
    save_messages(messages)
    socketio.emit("new_message", entry, room=receiver, namespace='/')
    socketio.emit("new_message", entry, room=session["username"], namespace='/')
    if receiver in connected_users:
        socketio.emit('message_delivered', {'id': entry['id']}, room=session["username"], namespace='/')
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
    filename = f"{username}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}{ext}"
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
        new_avatar_url = url_for("avatar_file", filename=filename, _external=True) + f"?t={int(datetime.now(timezone.utc).timestamp())}"
        socketio.emit("avatar_updated", {"username": username, "new_avatar_url": new_avatar_url}, namespace='/')
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
    socketio.emit("post_deleted", {"post_id": post_id}, namespace='/')
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
        last_msg_entry = conv[-1] if conv else None
        last_msg = last_msg_entry["text"] if last_msg_entry else ""
        last_date = last_msg_entry.get("date") if last_msg_entry else ""
        last_sender = last_msg_entry["sender"] if last_msg_entry else None
        last_status = None
        if last_sender == username and last_msg_entry:
            read_len = len(last_msg_entry.get("read_by", []))
            delivered_len = len(last_msg_entry.get("delivered_to", []))
            last_status = "read" if read_len > 1 else "delivered" if delivered_len > 0 else "sent"
        other_user_data = get_user(other_user)
        user_conversations.append({
            "username": other_user,
            "profile_pic": users.get(other_user, {}).get("avatar"),
            "last_msg": last_msg,
            "last_date": last_date,
            "unread_count": sum(1 for m in conv if username not in m.get("read_by", [])),
            "last_sender": last_sender,
            "last_status": last_status
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
    need_save = False
    newly_delivered = []
    newly_read = []
    for msg in conv:
        if 'id' not in msg:
            msg['id'] = str(uuid.uuid4())
            need_save = True
        if 'delivered_to' not in msg:
            msg['delivered_to'] = []
            need_save = True
        if msg['sender'] != session['username']:
            receiver = session['username']
            if receiver not in msg['delivered_to']:
                msg['delivered_to'].append(receiver)
                need_save = True
                newly_delivered.append(msg['id'])
                socketio.emit('message_delivered', {'id': msg['id']}, room=msg['sender'], namespace='/')
            if receiver not in msg.get('read_by', []):
                msg['read_by'].append(receiver)
                need_save = True
                newly_read.append(msg['id'])
    if need_save:
        save_messages(messages)
    if newly_read:
        socketio.emit('messages_read', {'ids': newly_read}, room=username, namespace='/')
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
    entry, messages, key = append_message(sender, receiver, text, msg_type="text")
    entry['id'] = data.get('id', str(uuid.uuid4()))
    save_messages(messages)
    socketio.emit("new_message", entry, room=receiver, namespace='/')
    socketio.emit("new_message", entry, room=sender, namespace='/')
    if receiver in connected_users:
        socketio.emit('message_delivered', {'id': entry['id']}, room=sender, namespace='/')
    return jsonify({"success": True})

@socketio.on('connect', namespace='/')
def handle_connect(auth=None):
    user = session.get("username")
    if user:
        join_room(user, namespace='/')
        connected_users.add(user)
        socketio.emit('user_online', {'username': user}, to=None, namespace='/')
        messages = load_messages()
        need_save = False
        for key, conv in messages.items():
            try:
                u1, u2 = key.split("_", 1)
            except ValueError:
                continue
            if user not in (u1, u2):
                continue
            sender = u1 if user == u2 else u2
            newly_delivered = []
            for m in conv:
                if m['sender'] == sender and user not in m.get('delivered_to', []):
                    m.setdefault('delivered_to', []).append(user)
                    need_save = True
                    if 'id' in m:
                        newly_delivered.append(m['id'])
            if newly_delivered:
                socketio.emit('messages_delivered', {'ids': newly_delivered}, room=sender, namespace='/')
        if need_save:
            save_messages(messages)

@socketio.on('disconnect', namespace='/')
def handle_disconnect():
    user = session.get("username")
    if user and user in connected_users:
        connected_users.remove(user)
        socketio.emit('user_offline', {'username': user}, to=None, namespace='/')

@socketio.on("send_message", namespace='/')
def handle_send_message(data):
    sender = session.get("username")
    receiver = (data.get("receiver") or "").strip()
    text = (data.get("text") or "").strip()
    if not sender or not receiver or not text:
        return
    entry, messages, key = append_message(sender, receiver, text, msg_type="text")
    entry['id'] = data.get('id', str(uuid.uuid4()))
    save_messages(messages)
    socketio.emit("new_message", entry, room=receiver, namespace='/')
    socketio.emit("new_message", entry, room=sender, namespace='/')
    if receiver in connected_users:
        socketio.emit('message_delivered', {'id': entry['id']}, room=sender, namespace='/')

@socketio.on('mark_read', namespace='/')
def mark_read(data):
    user = session.get("username")
    sender = data.get("sender")
    messages = load_messages()
    key1 = f"{sender}_{user}"
    key2 = f"{user}_{sender}"
    conv = messages.get(key1) or messages.get(key2) or []
    newly_read = []
    for m in conv:
        if user not in m.get("read_by", []):
            m.setdefault("read_by", []).append(user)
            if 'id' in m:
                newly_read.append(m['id'])
    save_messages(messages)
    if newly_read:
        socketio.emit('messages_read', {'ids': newly_read}, room=sender, namespace='/')

@socketio.on('send_comment', namespace='/')
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
    date = data.get('date') or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    comment_id = data.get('comment_id') or None
    socketio.emit('new_comment', {"post_id": post_id, "comment_id": comment_id, "username": data['username'], "content": content, "avatar": avatar, "date": date}, namespace='/')

@socketio.on('view_post', namespace='/')
def handle_view_post(data):
    if "username" not in session:
        return
    post_id = data.get('post_id')
    if not post_id:
        return
    users = load_users()
    user = next((u for u in users if u["username"] == session["username"]), None)
    if user:
        viewed_posts = user.setdefault("viewed_posts", [])
        if post_id not in viewed_posts:
            viewed_posts.append(post_id)
        posts = load_posts()
        post = next((p for p in posts if p["id"] == post_id), None)
        if post and post.get("boost_end") and datetime.fromisoformat(post["boost_end"]) > datetime.now(timezone.utc):
            boosted_viewed_by = post.setdefault("boosted_viewed_by", [])
            if session["username"] not in boosted_viewed_by:
                boosted_viewed_by.append(session["username"])
                save_posts(posts)
        save_users(users)

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

@socketio.on("join_room", namespace='/')
def handle_join_room(data):
    if isinstance(data, dict):
        username = data.get("username")
    else:
        username = data
    if username:
        join_room(username, namespace='/')

@app.route("/videos")
def videos():
    if "username" not in session:
        return redirect(url_for("login"))
    posts = load_posts()
    users = {u["username"]: u for u in load_users()}
    current_user = users.get(session["username"])
    if not current_user:
        session.pop("username", None)
        session.pop("avatar", None)
        session.pop("user_id", None)
        return redirect(url_for("login"))
    posts = get_sorted_posts(posts, current_user, filter_videos=True)
    for p in posts:
        p['liked_by_user'] = session["username"] in p.get("liked_by", [])
        p['comments_count'] = len(p.get("comments", []))
        p['following'] = is_following(session["username"], p["username"])
        p['avatar'] = users.get(p["username"], {}).get("avatar")
        for comment in p.get("comments", []):
            comment['avatar'] = users.get(comment["username"], {}).get("avatar")
    return render_template(
        "videos.html",
        posts=posts,
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
    if not acc.get("subscription_end") or datetime.now(timezone.utc) > datetime.fromisoformat(acc["subscription_end"]):
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
    referrer = next((a for a in bank if a.get("account_id") == referral_id), None)
    if not referrer:
        referral_id = ""
    else:
        # Increment referrer's referrals_count
        referrer["referrals_count"] = referrer.get("referrals_count", 0) + 1
    account_id = generate_account_id()
    bank.append({
        "username": un,
        "password": hash_password(pwd),
        "balance_franc": 0.0,
        "balance_dollar": 0.0,
        "account_id": account_id,
        "referrer_id": referral_id,
        "subscription_end": None,
        "referrals_count": 0
    })
    save_bank(bank)
    # Emit update if needed, but since it's new, perhaps notify referrer
    if referrer:
        socketio.emit("update_referrals", {"username": referrer["username"], "referrals_count": referrer["referrals_count"]}, namespace='/')
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
    if not acc.get("subscription_end") or datetime.now(timezone.utc) > datetime.fromisoformat(acc["subscription_end"]):
        return jsonify({"error": "Payez le droit mensuel"}), 400
    key = f"balance_{currency}"
    if key not in acc or float(acc[key]) < float(amount):
        return jsonify({"error": f"Solde insuffisant en {currency}. Solde disponible: {acc[key]}"}), 400
    acc[key] = float(acc[key]) - float(amount)
    save_bank(bank)
    convs = []
    with open(CONVERSIONS_FILE, "r", encoding="utf-8") as f:
        convs = json.load(f)
    convs.append({"username": un, "phone": phone, "amount": float(amount), "currency": currency, "timestamp": datetime.now(timezone.utc).isoformat()})
    with open(CONVERSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(convs, f, ensure_ascii=False, indent=2)
    currency_name = "francs" if currency == "franc" else "dollars"
    socketio.emit("balance_updated", {
        "username": acc["username"],
        "balance_franc": float(acc["balance_franc"]),
        "balance_dollar": float(acc["balance_dollar"]),
        "account_id": acc["account_id"]
    }, room=acc["username"], namespace='/')
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
    if not sender.get("subscription_end") or datetime.now(timezone.utc) > datetime.fromisoformat(sender["subscription_end"]):
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
    }, room=sender["username"], namespace='/')
    socketio.emit("balance_updated", {
        "username": recipient["username"],
        "balance_franc": float(recipient["balance_franc"]),
        "balance_dollar": float(recipient["balance_dollar"]),
        "account_id": recipient["account_id"]
    }, room=recipient["username"], namespace='/')
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
    referrer_id = acc.get("referrer_id")
    referrer = next((a for a in bank if a.get("account_id") == referrer_id), None) if referrer_id else None
    if referrer:
        platform[key] += fee * 0.7
        referrer[key] += fee * 0.3
    else:
        platform[key] += fee  # 100% to platform if no referrer
    delta = timedelta(minutes=1) if TEST_MODE else timedelta(days=30)
    acc["subscription_end"] = (datetime.now(timezone.utc) + delta).isoformat()
    save_bank(bank)
    socketio.emit("balance_updated", {
        "username": acc["username"],
        "balance_franc": float(acc["balance_franc"]),
        "balance_dollar": float(acc["balance_dollar"]),
        "account_id": acc["account_id"]
    }, room=acc["username"], namespace='/')
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
    }, room=acc["username"], namespace='/')
    return jsonify({"success": True, "message": f"Vous avez déposé {franc:.2f} francs et {dollar:.2f} dollars pour l'ID {account_id} ({acc['username']})"})

@app.route("/conversions", methods=["GET"])
def get_conversions():
    convs = []
    with open(CONVERSIONS_FILE, "r", encoding="utf-8") as f:
        convs = json.load(f)
    return jsonify(convs)

@app.route("/get_server_time", methods=["GET"])
def get_server_time():
    return jsonify({"time": datetime.now(timezone.utc).isoformat()})

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

@app.route("/boost_init/<int:post_id>", methods=["POST"])
def boost_init(post_id):
    if "username" not in session:
        return jsonify({"error": "Non connecté"}), 401
    data = request.json
    duration_days = data.get("duration_days")
    password = data.get("password")
    if not duration_days or not password or duration_days not in [1, 7, 30, 365]:
        return jsonify({"error": "Données invalides"}), 400
    posts = load_posts()
    post = next((p for p in posts if p["id"] == post_id), None)
    if not post or post["username"] != session["username"]:
        return jsonify({"error": "Publication non trouvée ou non autorisée"}), 404
    bank = load_bank()
    acc = next((a for a in bank if a["username"] == session["username"]), None)
    if not acc or acc["password"] != hash_password(password):
        return jsonify({"error": "Mot de passe incorrect ou compte non trouvé"}), 401
    if acc["balance_franc"] <= 0 and acc["balance_dollar"] <= 0:
        return jsonify({"error": "Solde insuffisant"}), 400
    return jsonify({"success": True})

@app.route("/boost_confirm/<int:post_id>", methods=["POST"])
def boost_confirm(post_id):
    if "username" not in session:
        return jsonify({"error": "Non connecté"}), 401
    data = request.json
    duration_days = data.get("duration_days")
    currency = data.get("currency")
    password = data.get("password")
    if not all([duration_days, currency, password]) or duration_days not in [1, 7, 30, 365] or currency not in ["franc", "dollar"]:
        return jsonify({"error": "Données invalides"}), 400
    posts = load_posts()
    post = next((p for p in posts if p["id"] == post_id), None)
    if not post or post["username"] != session["username"]:
        return jsonify({"error": "Publication non trouvée ou non autorisée"}), 404
    if post.get("boost_end"):
        return jsonify({"error": "Publication déjà boostée"}), 400
    bank = load_bank()
    acc = next((a for a in bank if a["username"] == session["username"]), None)
    if not acc or acc["password"] != hash_password(password):
        return jsonify({"error": "Mot de passe de confirmation incorrect"}), 401
    tariff = BOOST_TARIFFS[currency][duration_days]
    key = f"balance_{currency}"
    if acc[key] < tariff:
        return jsonify({"error": "Solde insuffisant"}), 400
    acc[key] -= tariff
    platform = next((a for a in bank if a["username"] == "platform"), None)
    platform[key] += tariff
    now = datetime.now(timezone.utc)
    post["boost_start"] = now.isoformat()
    post["boost_end"] = (now + timedelta(days=duration_days)).isoformat()
    post["boosted_viewed_by"] = []
    save_posts(posts)
    save_bank(bank)
    durations = {1: "jour", 7: "semaine", 30: "mois", 365: "an"}
    delai = durations[duration_days]
    devise = "FC" if currency == "franc" else "USD"
    message = f"Vous avez payé {tariff} {devise} pour un {delai} de boost."
    socketio.emit('new_boosted_post', {
        "id": post["id"],
        "username": post["username"],
        "description": post["description"],
        "boost_start": post["boost_start"],
        "boost_end": post["boost_end"]
    }, namespace='/')
    return jsonify({"success": True, "message": message})

@socketio.on('typing', namespace='/')
def handle_typing(data):
    receiver = data.get('receiver')
    if receiver:
        emit('user_typing', {'sender': session.get('username')}, room=receiver)

@socketio.on('stop_typing', namespace='/')
def handle_stop_typing(data):
    receiver = data.get('receiver')
    if receiver:
        emit('stop_typing', {'sender': session.get('username')}, room=receiver)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port)
