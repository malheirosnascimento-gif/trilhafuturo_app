from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "trilhafuturo_secret_key")

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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resultados_teste (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                pontuacao INTEGER,
                perfil TEXT,
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
            )
        """)

init_db()

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# Rotas

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "").strip()
        if not nome or not email or not senha:
            flash("Todos os campos são obrigatórios.", "danger")
            return render_template("register.html")
        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)",
                (nome, email, senha)
            )
            conn.commit()
            flash("Cadastro realizado com sucesso! Faça login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Erro: e-mail já cadastrado.", "danger")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "").strip()
        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM usuarios WHERE email = ? AND senha = ?",
            (email, senha)
        ).fetchone()
        conn.close()
        if user:
            session["usuario_id"] = user["id"]
            session["usuario_nome"] = user["nome"]
            return redirect(url_for("dashboard"))
        else:
            flash("E-mail ou senha incorretos.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu da conta.", "info")
    return redirect(url_for("index"))

@app.route("/dashboard")
def dashboard():
    if "usuario_id" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", nome=session.get("usuario_nome"))

@app.route("/teste", methods=["GET", "POST"])
def teste():
    if "usuario_id" not in session:
        flash("Faça login para realizar o teste.", "warning")
        return redirect(url_for("login"))
    if request.method == "POST":
        respostas = request.form
        # calcular pontuação simples
        pontuacao = 0
        for v in respostas.values():
            if v == "criativo":
                pontuacao += 2
            elif v == "analitico":
                pontuacao += 1
        # determinar perfil
        perfil = "Área de Humanas"
        if pontuacao >= 10:
            perfil = "Área de Exatas"
        elif pontuacao >= 6:
            perfil = "Área de Humanas"
        # preparar recomendações
        if perfil == "Área de Humanas":
            rec = {
                "carreiras": ["Psicologia", "Pedagogia", "Serviço Social"],
                "trilhas": [{"titulo": "Trilha de Psicologia", "link": "#"}]
            }
        elif perfil == "Área de Exatas":
            rec = {
                "carreiras": ["Engenharia", "Arquitetura", "Matemática"],
                "trilhas": [{"titulo": "Trilha de Engenharia", "link": "#"}]
            }
        else:
            rec = {
                "carreiras": ["Medicina", "Biologia", "Farmácia"],
                "trilhas": [{"titulo": "Trilha de Medicina", "link": "#"}]
            }
        name = session.get("usuario_nome", "Visitante")
        return render_template("resultado.html", perfil=perfil, rec=rec, name=name)
    return render_template("teste.html")

@app.route("/resultado", methods=["POST"])
def resultado():
    # Isso pode ser o mesmo do bloco acima, caso você queira separar
    respostas = request.form
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
            "trilhas": [{"titulo": "Trilha de Psicologia", "link": "#"}]
        }
    elif pontuacao < 10:
        perfil = "Área de Exatas"
        rec = {
            "carreiras": ["Engenharia", "Arquitetura", "Matemática"],
            "trilhas": [{"titulo": "Trilha de Engenharia", "link": "#"}]
        }
    else:
        perfil = "Área de Biológicas"
        rec = {
            "carreiras": ["Medicina", "Biologia", "Farmácia"],
            "trilhas": [{"titulo": "Trilha de Medicina", "link": "#"}]
        }
    name = session.get("usuario_nome", "Visitante")
    return render_template("resultado.html", perfil=perfil, rec=rec, name=name)

@app.route("/chat", methods=["GET", "POST"])
def chat():
    reply = None
    if request.method == "POST":
        q = request.form.get("question", "").lower()
        if "ux" in q:
            reply = "UX Designer foca na experiência do usuário."
        elif "marketing" in q:
            reply = "Marketing envolve promoção e estratégia."
        else:
            reply = "Não sei responder isso ainda."
    return render_template("chat.html", reply=reply)

@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if "usuario_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        comentario = request.form.get("message", "").strip()
        if comentario:
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO feedbacks (usuario_id, comentario) VALUES (?, ?)",
                (session["usuario_id"], comentario)
            )
            conn.commit()
            conn.close()
            flash("Feedback enviado com sucesso!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Digite um comentário antes de enviar.", "warning")
    return render_template("feedback.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
