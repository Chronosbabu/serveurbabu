from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os
import json
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join("data", "uploads")

# créer dossier si pas encore
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DATA_FILE = os.path.join("data", "posts.json")
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump([], f)

# charger les posts
def load_posts():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

# sauver les posts
def save_posts(posts):
    with open(DATA_FILE, "w") as f:
        json.dump(posts, f, indent=4)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "file" not in request.files:
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            return redirect(request.url)
        
        # sauver fichier
        filename = datetime.now().strftime("%Y%m%d%H%M%S_") + file.filename
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        
        # déterminer type
        ext = file.filename.lower().split('.')[-1]
        file_type = "video" if ext in ["mp4","webm","ogg"] else "image"
        
        # enregistrer dans json
        posts = load_posts()
        posts.insert(0, {"type": file_type, "file": filename, "date": str(datetime.now())})
        save_posts(posts)
        
        return redirect(url_for("index"))
    
    posts = load_posts()
    return render_template("style.html", posts=posts)

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

