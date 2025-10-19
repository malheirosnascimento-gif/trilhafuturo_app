from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
import sqlite3
import os
import re
from werkzeug.security import generate_password_hash, check_password_hash
import json

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "trilhafuturo_secret_key_dev")

# Configuração do Rate Limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

DB_NAME = "trilhafuturo.db"

# --- ESTRUTURAÇÃO DO BANCO DE DADOS ---
def init_db():
    # Esta função cria o banco de dados se ele não existir
    if not os.path.exists(DB_NAME):
        print(f"Criando banco de dados '{DB_NAME}'...")
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
        print("Banco de dados criado com sucesso.")

# --- FUNÇÕES AUXILIARES ---
def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(senha):
    return len(senha) >= 6

def get_db_connection():
    ### CORREÇÃO ###
    # Verificamos se o banco de dados existe *antes* de conectar.
    # Se não existir (como no servidor após um 'rm'), a função init_db() será chamada.
    init_db() 
    
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# --- BASES DE CONHECIMENTO (DADOS ESTÁTICOS) ---
CHAT_KNOWLEDGE_BASE = {
    "ux": { 
        "resposta": "UX Designer é um profissional que foca na experiência do usuário, criando produtos intuitivos e agradáveis. Trabalha com pesquisa de usuários, prototipagem e testes de usabilidade.", 
        "carreiras": ["UX Designer", "UI Designer", "Product Designer", "UX Researcher"], 
        "habilidades": ["Pesquisa com usuários", "Wireframes", "Testes de usabilidade", "Prototipagem"] 
    },
    "programação": { 
        "resposta": "Programação envolve criar soluções através de código. Desenvolvedores trabalham com diversas linguagens e frameworks para construir aplicações web, mobile e desktop.", 
        "carreiras": ["Desenvolvedor Front-end", "Desenvolvedor Back-end", "Full Stack", "Mobile Developer"], 
        "habilidades": ["Lógica de programação", "Estruturas de dados", "Versionamento", "Resolução de problemas"] 
    },
    "dados": { 
        "resposta": "Área de dados foca em coletar, processar e analisar informações para gerar insights valiosos para empresas.", 
        "carreiras": ["Cientista de Dados", "Analista de Dados", "Engenheiro de Dados", "BI Analyst"], 
        "habilidades": ["Estatística", "Python/R", "SQL", "Visualização de dados"] 
    }
}
     
RECOMENDACOES = {
    "humanas": { 
        "nome": "Área de Humanas", 
        "descricao": "Perfil criativo e social, com forte habilidade de comunicação e interesse por relações humanas.", 
        "carreiras": ["Psicólogo", "Professor", "Jornalista", "Advogado", "RH"], 
        "cursos_recomendados": ["Psicologia", "Letras", "História", "Direito", "Pedagogia"],
        # --- ADIÇÃO ---
        "trilhas": [
            {
                "id_trilha": "humanas_comunicacao",
                "titulo": "Fundamentos da Comunicação Social",
                "duracao": "4 Semanas",
                "modulos": [
                    {"nome": "Introdução à Comunicação", "link": "#"},
                    {"nome": "Comunicação e Oratória", "link": "#"},
                    {"nome": "Escrita Criativa", "link": "#"}
                ]
            },
            {
                "id_trilha": "humanas_psicologia",
                "titulo": "Introdução à Psicologia",
                "duracao": "6 Semanas",
                "modulos": [
                    {"nome": "Psicologia Comportamental", "link": "#"},
                    {"nome": "Processos Cognitivos", "link": "#"}
                ]
            }
        ]
        # --- FIM DA ADIÇÃO ---
    },
    "exatas": { 
        "nome": "Área de Exatas", 
        "descricao": "Perfil analítico e lógico, com aptidão para números e resolução de problemas complexos.", 
        "carreiras": ["Engenheiro", "Cientista de Dados", "Desenvolvedor", "Matemático"], 
        "cursos_recomendados": ["Engenharia", "Ciência da Computação", "Matemática", "Física"],
        # --- ADIÇÃO ---
        "trilhas": [
            {
                "id_trilha": "exatas_programacao",
                "titulo": "Fundamentos da Programação",
                "duracao": "8 Semanas",
                "modulos": [
                    {"nome": "Lógica de Programação", "link": "#"},
                    {"nome": "Introdução ao Python", "link": "#"},
                    {"nome": "Estrutura de Dados", "link": "#"}
                ]
            },
            {
                "id_trilha": "exatas_dados",
                "titulo": "Introdução à Análise de Dados",
                "duracao": "6 Semanas",
                "modulos": [
                    {"nome": "SQL Básico", "link": "#"},
                    {"nome": "Estatística para Dados", "link": "#"},
                    {"nome": "Visualização (Power BI/Tableau)", "link": "#"}
                ]
            }
        ]
        # --- FIM DA ADIÇÃO ---
    },
    "biologicas": { 
        "nome": "Área de Biológicas", 
        "descricao": "Perfil observador e investigativo, com interesse por seres vivos e processos naturais.", 
        "carreiras": ["Médico", "Biólogo", "Enfermeiro", "Pesquisador"], 
        "cursos_recomendados": ["Medicina", "Biologia", "Enfermagem", "Farmácia"],
        # --- ADIÇÃO ---
        "trilhas": [
            {
                "id_trilha": "bio_saude",
                "titulo": "Fundamentos da Área da Saúde",
                "duracao": "10 Semanas",
                "modulos": [
                    {"nome": "Anatomia Humana Básica", "link": "#"},
                    {"nome": "Bioquímica Celular", "link": "#"},
                    {"nome": "Saúde Coletiva", "link": "#"}
                ]
            },
            {
                "id_trilha": "bio_ambiental",
                "titulo": "Ecologia e Ciências Ambientais",
                "duracao": "8 Semanas",
                "modulos": [
                    {"nome": "Ecossistemas Brasileiros", "link": "#"},
                    {"nome": "Gestão Ambiental", "link": "#"}
                ]
            }
        ]
        # --- FIM DA ADIÇÃO ---
    }
}
# --- MIDDLEWARE DE AUTENTICAÇÃO ---
@app.before_request
def check_authentication():
    # Esta função já protege suas rotas. Não precisamos do decorador @login_required.
    protected_routes = ['/dashboard', '/teste', '/feedback', '/chat', '/api/stats', '/api/chart/profile-distribution']
    if request.path in protected_routes and 'usuario_id' not in session:
        flash("Por favor, faça login para acessar esta página.", "warning")
        return redirect(url_for('login', next=request.path)) # 'next' leva o usuário de volta após o login

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.utcnow().year}

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d/%m/%Y %H:%M'):
    if value is None:
        return ""
    try:
        # Tenta parsear o formato padrão do SQLite
        dt_object = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        return dt_object.strftime(format)
    except (ValueError, TypeError):
        # Se falhar, tenta como se já fosse um objeto datetime (pouco provável, mas seguro)
        try:
            return value.strftime(format)
        except:
            return value # Retorna o valor original se tudo falhar

# --- ROTAS PRINCIPAIS E DE AUTENTICAÇÃO ---
@app.route("/")
def index():
    stats = {
        'total_users': 0,
        'total_tests': 0
    }
    chart_data = {"labels": [], "values": []}

    try:
        with get_db_connection() as conn:
            stats['total_users'] = conn.execute("SELECT COUNT(id) FROM usuarios").fetchone()[0]
            stats['total_tests'] = conn.execute("SELECT COUNT(id) FROM resultados_teste").fetchone()[0]

            dados_grafico = conn.execute("""
                SELECT perfil, COUNT(id) as count
                FROM resultados_teste
                GROUP BY perfil
            """).fetchall()

            if dados_grafico:
                chart_data['labels'] = [row['perfil'].capitalize() for row in dados_grafico]
                chart_data['values'] = [row['count'] for row in dados_grafico]

    except Exception as e:
        # Se o banco de dados acabou de ser criado, as tabelas podem estar vazias
        print(f"Erro ao buscar dados para a página inicial (pode ser normal na primeira execução): {e}")

    chart_data_json = json.dumps(chart_data)
    return render_template("index.html", stats=stats, chart_data=chart_data_json)

@app.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def register():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        if not all([nome, email, senha]):
            flash("Todos os campos são obrigatórios.", "danger")
            return render_template("register.html")
        if not validate_email(email):
            flash("Por favor, insira um e-mail válido.", "danger")
            return render_template("register.html")
        if not validate_password(senha):
            flash("A senha deve ter pelo menos 6 caracteres.", "danger")
            return render_template("register.html")

        senha_hash = generate_password_hash(senha)

        try:
            with get_db_connection() as conn:
                conn.execute(
                    "INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)",
                    (nome, email, senha_hash)
                )
                conn.commit()
                flash("Cadastro realizado com sucesso! Faça login.", "success")
                return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Este e-mail já está cadastrado.", "danger")
        except Exception as e:
            flash(f"Ocorreu um erro inesperado: {e}", "danger")

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

        try:
            with get_db_connection() as conn:
                usuario = conn.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()

                if usuario and check_password_hash(usuario["senha"], senha):
                    session.clear() # Limpa qualquer sessão antiga
                    session["usuario_id"] = usuario["id"]
                    session["usuario_nome"] = usuario["nome"]
                    session["usuario_email"] = usuario["email"]
                    flash(f"Bem-vinda(o), {usuario['nome']}!", "success")
                    next_page = request.args.get('next')
                    return redirect(next_page or url_for("dashboard"))
                else:
                    flash("E-mail ou senha incorretos.", "danger")
        except Exception as e:
            flash(f"Ocorreu um erro inesperado: {e}", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("index"))

# --- ROTAS DO PAINEL DO USUÁRIO ---
@app.route('/dashboard')
### CORREÇÃO ###
# Removemos o @login_required daqui, pois a função @app.before_request já protege esta rota.
def dashboard():
    ### CORREÇÃO ###
    # Pegamos o 'usuario_id' da sessão para usar nas consultas SQL.
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        # Segurança extra, embora o before_request já deva pegar
        return redirect(url_for('login'))

    historico_testes = []
    ultimos_feedbacks = []
    total_testes = 0
    total_feedbacks = 0

    try:
        with get_db_connection() as conn:
            # Histórico de testes
            historico_testes = conn.execute("""
                SELECT perfil, data_teste FROM resultados_teste
                WHERE usuario_id = ? ORDER BY data_teste DESC
            """, (usuario_id,)).fetchall()

            # Últimos feedbacks
            ultimos_feedbacks = conn.execute("""
                SELECT comentario, data_criacao FROM feedbacks
                WHERE usuario_id = ? ORDER BY data_criacao DESC LIMIT 3
            """, (usuario_id,)).fetchall()

            # Total de testes
            total_testes = conn.execute(
                "SELECT COUNT(id) FROM resultados_teste WHERE usuario_id = ?",
                (usuario_id,)
            ).fetchone()[0]

            # Total de feedbacks
            total_feedbacks = conn.execute(
                "SELECT COUNT(id) FROM feedbacks WHERE usuario_id = ?",
                (usuario_id,)
            ).fetchone()[0]

    except Exception as e:
        # Este é o erro que você estava vendo!
        flash(f"Erro ao carregar dados do dashboard: {e}", "danger")

    ### CORREÇÃO ###
    # Removemos o 'return' duplicado que estava no topo desta função.
    # Este é o 'return' correto, que envia os dados para o template.
    return render_template("dashboard.html",
                        nome=session.get("usuario_nome"),
                        historico_testes=historico_testes,
                        ultimos_feedbacks=ultimos_feedbacks,
                        total_testes=total_testes,
                        total_feedbacks=total_feedbacks)

# --- ROTAS DE FUNCIONALIDADES (TESTE, CHAT, FEEDBACK) ---
@app.route("/teste", methods=["GET", "POST"])
def teste():
    if request.method == "POST":
        respostas = request.form.to_dict()
        if len(respostas) < 5:
            flash("Você precisa responder pelo menos 5 perguntas para um resultado preciso.", "warning")
            return redirect(url_for("teste"))

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

        if pontuacao_exatas >= pontuacao_humanas and pontuacao_exatas >= pontuacao_biologicas:
            perfil = "exatas"
        elif pontuacao_biologicas >= pontuacao_humanas and pontuacao_biologicas >= pontuacao_exatas:
            perfil = "biologicas"
        else:
            perfil = "humanas"
        
        # Pontuação total para salvar no DB (exemplo: a pontuação mais alta)
        pontuacao_total = max(pontuacao_exatas, pontuacao_humanas, pontuacao_biologicas)

        try:
            with get_db_connection() as conn:
                conn.execute(
                    "INSERT INTO resultados_teste (usuario_id, pontuacao, perfil) VALUES (?, ?, ?)",
                    (session["usuario_id"], pontuacao_total, perfil)
                )
                conn.commit()
                return redirect(url_for("resultado", perfil=perfil))
        except Exception as e:
            flash(f"Erro ao salvar resultado do teste: {e}", "danger")

    return render_template("teste.html")

@app.route("/resultado")
def resultado():
    perfil_key = request.args.get("perfil", "humanas")
    perfil = RECOMENDACOES.get(perfil_key, RECOMENDACOES["humanas"])
    nome = session.get("usuario_nome", "Visitante")

    return render_template("resultado.html", perfil=perfil, nome=nome)
@app.route("/trilha/<id_trilha>")
def trilha(id_trilha):
    # Esta rota é acessível publicamente (ou protegida pelo @app.before_request se você preferir)
    trilha_encontrada = None
    perfil_key = None

    # Procura a trilha em todos os perfis
    for key, perfil in RECOMENDACOES.items():
        for trilha_obj in perfil.get('trilhas', []):
            if trilha_obj['id_trilha'] == id_trilha:
                trilha_encontrada = trilha_obj
                perfil_key = key
                break
        if trilha_encontrada:
            break
            
    if not trilha_encontrada:
        flash("Trilha não encontrada.", "danger")
        return redirect(url_for("dashboard"))

    return render_template("trilha.html", trilha=trilha_encontrada, perfil_key=perfil_key)
@app.route("/chat", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def chat():
    reply = None
    carreiras = []
    habilidades = []

    if request.method == "POST":
        pergunta = request.form.get("question", "").lower().strip()
        if not pergunta:
            flash("Por favor, digite uma pergunta.", "warning")
        else:
            # Lógica de busca na base de conhecimento
            if "ux" in pergunta or "design" in pergunta or "experiência" in pergunta:
                info = CHAT_KNOWLEDGE_BASE["ux"]
                reply = info["resposta"]
                carreiras = info.get("carreiras", [])
                habilidades = info.get("habilidades", [])
            elif "programação" in pergunta or "codigo" in pergunta or "desenvolvedor" in pergunta:
                info = CHAT_KNOWLEDGE_BASE["programação"]
                reply = info["resposta"]
                carreiras = info.get("carreiras", [])
                habilidades = info.get("habilidades", [])
            elif "dados" in pergunta or "analise" in pergunta or "estatística" in pergunta:
                info = CHAT_KNOWLEDGE_BASE["dados"]
                reply = info["resposta"]
                carreiras = info.get("carreiras", [])
                habilidades = info.get("habilidades", [])
            else:
                reply = "Desculpe, não entendi. Pode reformular a pergunta? Posso ajudar com informações sobre UX Design, Programação ou Área de Dados."

        if 'usuario_id' in session and reply:
            try:
                with get_db_connection() as conn:
                    conn.execute(
                        "INSERT INTO conversas_chat (usuario_id, pergunta, resposta) VALUES (?, ?, ?)",
                        (session["usuario_id"], pergunta, reply)
                    )
                    conn.commit()
            except Exception as e:
                print(f"Erro ao salvar conversa: {e}")

    return render_template("chat.html", reply=reply, carreiras=carreiras, habilidades=habilidades)

@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if request.method == "POST":
        comentario = request.form.get("message", "").strip()
        
        if not comentario:
            flash("Por favor, digite seu feedback.", "danger")
        elif len(comentario) < 10:
            flash("O feedback deve ter pelo menos 10 caracteres.", "danger")
        else:
            try:
                with get_db_connection() as conn:
                    conn.execute(
                        "INSERT INTO feedbacks (usuario_id, comentario) VALUES (?, ?)",
                        (session["usuario_id"], comentario)
                    )
                    conn.commit()
                    flash("Feedback enviado com sucesso! Obrigado pela contribuição.", "success")
                    return redirect(url_for("dashboard"))
            except Exception as e:
                flash(f"Erro ao enviar feedback: {e}", "danger")

    return render_template("feedback.html")

# --- API E GERENCIAMENTO DE ERROS ---
@app.route("/api/stats")
def api_stats():
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return jsonify({"error": "Não autorizado"}), 401
        
    try:
        with get_db_connection() as conn:
            total_testes = conn.execute("SELECT COUNT(*) FROM resultados_teste WHERE usuario_id = ?", 
                                      (usuario_id,)).fetchone()[0]
            total_feedbacks = conn.execute("SELECT COUNT(*) FROM feedbacks WHERE usuario_id = ?", 
                                         (usuario_id,)).fetchone()[0]
            total_conversas = conn.execute("SELECT COUNT(*) FROM conversas_chat WHERE usuario_id = ?", 
                                         (usuario_id,)).fetchone()[0]

            return jsonify({
                "total_testes": total_testes,
                "total_feedbacks": total_feedbacks,
                "total_conversas": total_conversas
            })
    except Exception as e:
        return jsonify({"error": f"Erro interno: {e}"}), 500

@app.route("/api/chart/profile-distribution")
def profile_distribution_chart():
    # Este gráfico mostra a distribuição de TODOS os usuários, por isso não filtra por usuario_id
    try:
        with get_db_connection() as conn:
            dados_grafico = conn.execute("""
                SELECT perfil, COUNT(id) as count
                FROM resultados_teste
                GROUP BY perfil
            """).fetchall()

            if not dados_grafico:
                return jsonify({"labels": [], "values": []})

            labels = [row['perfil'].capitalize() for row in dados_grafico]
            values = [row['count'] for row in dados_grafico]

            return jsonify({"labels": labels, "values": values})
    except Exception as e:
        return jsonify({"error": f"Erro interno: {e}"}), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html"), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    flash("Muitas tentativas em pouco tempo. Aguarde um momento antes de tentar novamente.", "warning")
    # Redireciona para a página anterior ou para o index
    return redirect(request.referrer or url_for("index"))

# --- EXECUÇÃO DA APLICAÇÃO ---
if __name__ == "__main__":
    ### CORREÇÃO ###
    # Removido o init_db() daqui, pois ele agora é chamado por get_db_connection()
    # Removido o bloco duplicado
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port, debug=True)