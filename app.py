from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "trilhafuturo_secret_key"

DB_NAME = "trilhafuturo.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedbacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                comentario TEXT,
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
            )
        """)
    # não precisa do conn.commit aqui, o with já fecha

init_db()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nome = request.form.get("nome")
        email = request.form.get("email")
        senha = request.form.get("senha")

        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)",
                    (nome, email, senha)
                )
                conn.commit()
                flash("Cadastro realizado com sucesso! Faça login.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("Erro: e-mail já cadastrado.", "danger")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")

        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM usuarios WHERE email = ? AND senha = ?", (email, senha)
            )
            usuario = cursor.fetchone()

            if usuario:
                session["usuario_id"] = usuario[0]
                session["usuario_nome"] = usuario[1]
                return redirect(url_for("dashboard"))
            else:
                flash("E-mail ou senha incorretos.", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("index"))

@app.route("/dashboard")
def dashboard():
    if "usuario_id" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", nome=session.get("usuario_nome"))

@app.route("/teste", methods=["GET"])
def teste():
    if "usuario_id" not in session:
        flash("Faça login para realizar o teste.", "warning")
        return redirect(url_for("login"))
    return render_template("teste.html")


@app.route("/resultado", methods=["POST"])
def resultado():
    respostas = request.form.to_dict()

    pontuacao = sum(2 if v == "criativo" else 1 for v in respostas.values())

    if pontuacao < 6:
        perfil = "Área de Humanas"
        rec = {
            "carreiras": ["Psicologia", "Pedagogia", "Serviço Social"],
            "trilhas": [{"titulo": "Trilha de Psicologia", "link": "https://link-psicologia.com"}]
        }
    elif pontuacao < 10:
        perfil = "Área de Exatas"
        rec = {
            "carreiras": ["Engenharia", "Arquitetura", "Matemática"],
            "trilhas": [{"titulo": "Trilha de Engenharia", "link": "https://link-engenharia.com"}]
        }
    else:
        perfil = "Área de Biológicas"
        rec = {
            "carreiras": ["Medicina", "Biologia", "Farmácia"],
            "trilhas": [{"titulo": "Trilha de Medicina", "link": "https://link-medicina.com"}]
        }

    name = session.get("usuario_nome", "Visitante")
    return render_template("resultado.html", perfil=perfil, rec=rec, name=name)


    return render_template("teste.html")

@app.route("/resultado", methods=["POST"])
def resultado():
    respostas = request.form
    # Vamos pontuar com base nos valores “criativo” / “analitico”
    # atribuir valores numéricos arbitrários:
    pontuacao = 0
    for v in respostas.values():
        if v == "criativo":
            pontuacao += 2
        elif v == "analitico":
            pontuacao += 1

    if pontuacao < 6:
        perfil = "Área de Humanas"
        rec = {
            "carreiras": ["Psicologia", "Pedagogia", "Serviço Social"],
            "trilhas": [{"titulo": "Trilha de Psicologia", "link": "https://link-psicologia.com"}]
        }
    elif pontuacao < 10:
        perfil = "Área de Exatas"
        rec = {
            "carreiras": ["Engenharia", "Arquitetura", "Matemática"],
            "trilhas": [{"titulo": "Trilha de Engenharia", "link": "https://link-engenharia.com"}]
        }
    else:
        perfil = "Área de Biológicas"
        rec = {
            "carreiras": ["Medicina", "Biologia", "Farmácia"],
            "trilhas": [{"titulo": "Trilha de Medicina", "link": "https://link-medicina.com"}]
        }

    name = session.get("usuario_nome", "Visitante")
    return render_template("resultado.html", perfil=perfil, rec=rec, name=name)

@app.route("/chat", methods=["GET", "POST"])
def chat():
    reply = None
    if request.method == "POST":
        q = request.form.get("question", "").lower()
        # lógica simples de resposta
        if "ux" in q:
            reply = "Um UX Designer foca na experiência do usuário."
        elif "marketing" in q:
            reply = "Marketing envolve promoção e estratégia digital."
        elif "dados" in q:
            reply = "Cientista de dados transforma dados em insights."
        else:
            reply = "Não sei responder isso ainda."
    return render_template("chat.html", reply=reply)

@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if "usuario_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        comentario = request.form.get("message")
        usuario_id = session["usuario_id"]
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO feedbacks (usuario_id, comentario) VALUES (?, ?)",
                (usuario_id, comentario)
            )
            conn.commit()
        flash("Feedback enviado com sucesso!", "success")
        return redirect(url_for("dashboard"))
    return render_template("feedback.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
