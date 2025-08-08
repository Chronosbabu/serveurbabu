from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def accueil():
    return "Bienvenue sur le serveur"

@app.route('/ecole')
def ecole():
    return render_template("ecole.html")

@app.route('/parent')
def parent():
    return render_template("parent.html")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

    

