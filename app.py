from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import sqlite3
import os
import re
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "trilhafuturo_secret_key_dev")

# Configuração do Rate Limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"  # Adicionado para maior compatibilidade
)

DB_NAME = "trilhafuturo.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedbacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                comentario TEXT NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resultados_teste (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                pontuacao INTEGER,
                perfil TEXT NOT NULL,
                data_teste TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversas_chat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                pergunta TEXT NOT NULL,
                resposta TEXT NOT NULL,
                data_conversa TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            )
        """)
        # Adicionar índices para melhor performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_resultados_usuario ON resultados_teste(usuario_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedbacks_usuario ON feedbacks(usuario_id)")

init_db()

# Funções auxiliares
def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(senha):
    return len(senha) >= 6

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# Base de conhecimento para chat - EXPANDIDA
CHAT_KNOWLEDGE_BASE = {
    "ux": {
        "resposta": "UX Designer (User Experience Designer) foca na experiência do usuário, criando produtos que sejam eficientes, fáceis de usar e agradáveis. Trabalha com pesquisa, prototipagem e testes de usabilidade.",
        "carreiras": ["UX Designer", "UI Designer", "Product Designer", "UX Researcher"],
        "habilidades": ["Pesquisa com usuários", "Wireframing", "Prototipagem", "Testes de usabilidade", "Design Thinking"]
    },
    "marketing": {
        "resposta": "Marketing envolve estratégias de promoção, análise de mercado e comunicação com clientes. Inclui marketing digital, análise de dados e gestão de marcas.",
        "carreiras": ["Marketing Digital", "Brand Manager", "Analista de Mídia", "Social Media Manager"],
        "habilidades": ["Análise de mercado", "SEO", "Mídias sociais", "Estratégia de conteúdo", "Google Analytics"]
    },
    "dados": {
        "resposta": "Cientista de dados transforma dados em insights valiosos usando estatística, machine learning e programação. Área em alta demanda no mercado.",
        "carreiras": ["Cientista de Dados", "Analista de Dados", "Engenheiro de Dados", "BI Analyst"],
        "habilidades": ["Python", "SQL", "Machine Learning", "Estatística", "Visualização de Dados"]
    },
    "programacao": {
        "resposta": "Programação envolve desenvolvimento de software, aplicativos e sistemas. Pode ser front-end, back-end ou full-stack.",
        "carreiras": ["Desenvolvedor Full-Stack", "Front-end Developer", "Back-end Developer", "Mobile Developer"],
        "habilidades": ["Linguagens de programação", "Banco de dados", "APIs", "Versionamento", "Estrutura de dados"]
    },
    "design": {
        "resposta": "Design gráfico combina criatividade e técnica para criar soluções visuais que comunicam ideias de forma eficaz.",
        "carreiras": ["Designer Gráfico", "Illustrator", "Motion Designer", "Web Designer"],
        "habilidades": ["Adobe Creative Suite", "Teoria das cores", "Tipografia", "Layout", "Branding"]
    }
}

# Sistema de recomendações - MELHORADO
RECOMENDACOES = {
    "humanas": {
        "nome": "Área de Humanas",
        "descricao": "Perfil com forte inclinação para relações humanas, comunicação e pensamento crítico. Você se destaca em atividades que envolvem empatia, diálogo e compreensão do comportamento humano.",
        "carreiras": ["Psicologia", "Pedagogia", "Serviço Social", "Direito", "Jornalismo", "Recursos Humanos", "Relações Internacionais"],
        "trilhas": [
            {"titulo": "Trilha de Psicologia", "link": "#", "duracao": "8 semanas"},
            {"titulo": "Trilha de Pedagogia", "link": "#", "duracao": "6 semanas"},
            {"titulo": "Trilha de Serviço Social", "link": "#", "duracao": "7 semanas"}
        ],
        "cursos_recomendados": ["Comunicação Eficaz", "Psicologia Social", "Ética Profissional", "Gestão de Pessoas"]
    },
    "exatas": {
        "nome": "Área de Exatas",
        "descricao": "Perfil analítico, com aptidão para números, lógica e resolução de problemas complexos. Você tem facilidade com cálculos e pensamento estruturado.",
        "carreiras": ["Engenharia", "Arquitetura", "Matemática", "Ciência da Computação", "Estatística", "Física", "Economia"],
        "trilhas": [
            {"titulo": "Trilha de Engenharia", "link": "#", "duracao": "10 semanas"},
            {"titulo": "Trilha de Ciência da Computação", "link": "#", "duracao": "12 semanas"},
            {"titulo": "Trilha de Arquitetura", "link": "#", "duracao": "9 semanas"}
        ],
        "cursos_recomendados": ["Lógica de Programação", "Cálculo", "Geometria Analítica", "Estatística Aplicada"]
    },
    "biologicas": {
        "nome": "Área de Biológicas",
        "descricao": "Perfil com interesse em ciências da vida, saúde e pesquisa biológica. Você se interessa pelo funcionamento dos seres vivos e pelo cuidado com a saúde.",
        "carreiras": ["Medicina", "Biologia", "Farmácia", "Enfermagem", "Nutrição", "Veterinária", "Biomedicina"],
        "trilhas": [
            {"titulo": "Trilha de Medicina", "link": "#", "duracao": "15 semanas"},
            {"titulo": "Trilha de Biologia", "link": "#", "duracao": "8 semanas"},
            {"titulo": "Trilha de Nutrição", "link": "#", "duracao": "7 semanas"}
        ],
        "cursos_recomendados": ["Biologia Celular", "Anatomia Humana", "Bioquímica", "Genética"]
    }
}

# Middleware para verificar autenticação nas rotas protegidas
@app.before_request
def check_authentication():
    protected_routes = ['/dashboard', '/teste', '/feedback', '/chat', '/api/stats']
    if request.path in protected_routes and 'usuario_id' not in session:
        flash("Por favor, faça login para acessar esta página.", "warning")
        return redirect(url_for('login'))

# Rotas
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def register():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        if not nome or not email or not senha:
            flash("Todos os campos são obrigatórios.", "danger")
            return render_template("register.html")

        if not validate_email(email):
            flash("Por favor, insira um e-mail válido.", "danger")
            return render_template("register.html")

        if not validate_password(senha):
            flash("A senha deve ter pelo menos 6 caracteres.", "danger")
            return render_template("register.html")

        senha_hash = generate_password_hash(senha)
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)",
                (nome, email, senha_hash)
            )
            conn.commit()
            flash("Cadastro realizado com sucesso! Faça login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Este e-mail já está cadastrado.", "danger")
        except Exception as e:
            flash("Erro interno do sistema. Tente novamente.", "danger")
        finally:
            conn.close()

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        if not email or not senha:
            flash("Por favor, preencha todos os campos.", "danger")
            return render_template("login.html")

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
            usuario = cursor.fetchone()

            if usuario and check_password_hash(usuario["senha"], senha):
                session["usuario_id"] = usuario["id"]
                session["usuario_nome"] = usuario["nome"]
                session["usuario_email"] = usuario["email"]
                flash(f"Bem-vinda(o), {usuario['nome']}!", "success")
                next_page = request.args.get('next')
                return redirect(next_page or url_for("dashboard"))
            else:
                flash("E-mail ou senha incorretos.", "danger")
        except Exception as e:
            flash("Erro interno do sistema. Tente novamente.", "danger")
        finally:
            conn.close()

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("index"))

@app.route("/dashboard")
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT perfil, data_teste FROM resultados_teste
            WHERE usuario_id = ? ORDER BY data_teste DESC LIMIT 5
        """, (session["usuario_id"],))
        historico_testes = cursor.fetchall()

        cursor.execute("""
            SELECT comentario, data_criacao FROM feedbacks
            WHERE usuario_id = ? ORDER BY data_criacao DESC LIMIT 3
        """, (session["usuario_id"],))
        ultimos_feedbacks = cursor.fetchall()

        # Contar total de testes realizados
        cursor.execute("SELECT COUNT(*) FROM resultados_teste WHERE usuario_id = ?", (session["usuario_id"],))
        total_testes = cursor.fetchone()[0]

    except Exception as e:
        flash("Erro ao carregar dados do dashboard.", "danger")
        historico_testes = []
        ultimos_feedbacks = []
        total_testes = 0
    finally:
        conn.close()

    return render_template("dashboard.html",
                           nome=session.get("usuario_nome"),
                           historico_testes=historico_testes,
                           ultimos_feedbacks=ultimos_feedbacks,
                           total_testes=total_testes)

@app.route("/teste", methods=["GET", "POST"])
def teste():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    if request.method == "POST":
        respostas = request.form.to_dict()
        if len(respostas) < 5:  # Mínimo de 5 respostas
            flash("Você precisa responder pelo menos 5 perguntas para um resultado preciso.", "warning")
            return redirect(url_for("teste"))

        # Algoritmo de pontuação melhorado
        pontuacao_humanas = 0
        pontuacao_exatas = 0
        pontuacao_biologicas = 0

        for pergunta, resposta in respostas.items():
            if resposta == "criativo":
                pontuacao_humanas += 2
                pontuacao_biologicas += 1
            elif resposta == "analitico":
                pontuacao_exatas += 2
                pontuacao_biologicas += 1
            elif resposta == "social":
                pontuacao_humanas += 2
                pontuacao_biologicas += 1
            elif resposta == "organizado":
                pontuacao_exatas += 1
                pontuacao_humanas += 1

        # Determinar perfil baseado na maior pontuação
        if pontuacao_exatas >= pontuacao_humanas and pontuacao_exatas >= pontuacao_biologicas:
            perfil = "exatas"
        elif pontuacao_biologicas >= pontuacao_humanas and pontuacao_biologicas >= pontuacao_exatas:
            perfil = "biologicas"
        else:
            perfil = "humanas"

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO resultados_teste (usuario_id, pontuacao, perfil) VALUES (?, ?, ?)",
                (session["usuario_id"], max(pontuacao_exatas, pontuacao_humanas, pontuacao_biologicas), perfil)
            )
            conn.commit()
        except Exception as e:
            flash("Erro ao salvar resultado do teste.", "danger")
        finally:
            conn.close()

        return redirect(url_for("resultado", perfil=perfil))

    return render_template("teste.html")

@app.route("/resultado")
def resultado():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    perfil_key = request.args.get("perfil", "humanas")
    perfil = RECOMENDACOES.get(perfil_key, RECOMENDACOES["humanas"])
    nome = session.get("usuario_nome", "Visitante")
    return render_template("resultado.html", perfil=perfil, nome=nome)

@app.route("/chat", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def chat():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    reply = None
    carreiras = []
    habilidades = []

    if request.method == "POST":
        pergunta = request.form.get("question", "").lower().strip()
        if not pergunta:
            flash("Por favor, digite uma pergunta.", "warning")
        else:
            # Busca inteligente por termos relacionados
            termos_encontrados = []
            for termo, info in CHAT_KNOWLEDGE_BASE.items():
                if termo in pergunta:
                    termos_encontrados.append(termo)
            
            if termos_encontrados:
                # Usar o primeiro termo encontrado (poderia ser melhorado para múltiplos termos)
                termo_principal = termos_encontrados[0]
                info = CHAT_KNOWLEDGE_BASE[termo_principal]
                reply = info["resposta"]
                carreiras = info.get("carreiras", [])
                habilidades = info.get("habilidades", [])
            else:
                # Resposta padrão para perguntas não reconhecidas
                reply = "Desculpe, ainda não tenho informações específicas sobre esse tema. Posso ajudar com informações sobre: UX Design, Marketing, Ciência de Dados, Programação ou Design. Sobre qual área você gostaria de saber mais?"

            # Salvar no histórico
            if 'usuario_id' in session:
                conn = get_db_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO conversas_chat (usuario_id, pergunta, resposta) VALUES (?, ?, ?)",
                        (session["usuario_id"], pergunta, reply)
                    )
                    conn.commit()
                except Exception as e:
                    print(f"Erro ao salvar conversa: {e}")
                finally:
                    conn.close()

    return render_template("chat.html", reply=reply, carreiras=carreiras, habilidades=habilidades)

@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    if request.method == "POST":
        comentario = request.form.get("message", "").strip()
        if not comentario:
            flash("Digite seu feedback antes de enviar.", "warning")
            return render_template("feedback.html")

        if len(comentario) < 10:
            flash("O feedback deve ter pelo menos 10 caracteres.", "warning")
            return render_template("feedback.html")

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO feedbacks (usuario_id, comentario) VALUES (?, ?)",
                (session["usuario_id"], comentario)
            )
            conn.commit()
            flash("Feedback enviado com sucesso! Obrigado pela contribuição.", "success")
            return redirect(url_for("dashboard"))
        except Exception as e:
            flash("Erro ao enviar feedback. Tente novamente.", "danger")
        finally:
            conn.close()

    return render_template("feedback.html")

@app.route("/api/stats")
def api_stats():
    if "usuario_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM resultados_teste WHERE usuario_id = ?", (session["usuario_id"],))
        total_testes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM feedbacks WHERE usuario_id = ?", (session["usuario_id"],))
        total_feedbacks = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM conversas_chat WHERE usuario_id = ?", (session["usuario_id"],))
        total_conversas = cursor.fetchone()[0]
        
        return jsonify({
            "total_testes": total_testes,
            "total_feedbacks": total_feedbacks,
            "total_conversas": total_conversas
        })
    except Exception as e:
        return jsonify({"error": "Erro interno"}), 500
    finally:
        conn.close()

@app.errorhandler(404)
def not_found_error(error):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html"), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    flash("Muitas tentativas em pouco tempo. Aguarde um momento antes de tentar novamente.", "warning")
    return redirect(request.referrer or url_for("index"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))  # Usa PORT ou 5001 como fallback
    app.run(host="0.0.0.0", port=port, debug=True)