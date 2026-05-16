from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = 'chave_secreta_para_sessoes_do_trackit'

# Configuração do Banco de Dados SQLite
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==========================================
#                  MODELOS
# ==========================================

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)  # Substituiu a matrícula
    username = db.Column(db.String(50), unique=True, nullable=False)
    senha = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    emprestimos = db.relationship('Emprestimo', backref='aluno', lazy=True)

class Ativo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    patrimonio = db.Column(db.String(50), unique=True, nullable=False)
    laboratorio = db.Column(db.String(50), nullable=False)
    quantidade = db.Column(db.Integer, default=1)        # Quantidade total do lote
    qtd_disponivel = db.Column(db.Integer, default=1)    # Saldo atual em estoque

class Emprestimo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    ativo_id = db.Column(db.Integer, db.ForeignKey('ativo.id'), nullable=False)
    quantidade_pega = db.Column(db.Integer, nullable=False)
    ativo = db.relationship('Ativo')

# Criar tabelas e aplicar auto-correção de Schema
with app.app_context():
    try:
        db.create_all()
        # Força um teste no banco para validar se a coluna CPF está fisicamente lá
        Usuario.query.filter_by(username='admin').first()
    except Exception:
        # Se falhar (coluna ausente), reconstrói o banco do zero de forma limpa
        db.drop_all()
        db.create_all()
        
    # Cria o Administrador Master padrão do sistema
    if not Usuario.query.filter_by(username='admin').first():
        admin_padrao = Usuario(
            nome="Administrador Trackit",
            cpf="000.000.000-00",
            username="admin",
            senha="admin123",
            is_admin=True
        )
        db.session.add(admin_padrao)
        db.session.commit()

# ==========================================
#          ROTAS DE AUTENTICAÇÃO
# ==========================================

@app.route('/cadastro_usuario', methods=['GET', 'POST'])
def cadastro_usuario():
    if request.method == 'POST':
        novo_user = Usuario(
            nome=request.form.get('nome'),
            cpf=request.form.get('cpf'),
            username=request.form.get('username'),
            senha=request.form.get('senha'),
            is_admin=False
        )
        try:
            db.session.add(novo_user)
            db.session.commit()
            return redirect(url_for('login'))
        except:
            return "Erro: Nome de usuário ou CPF já cadastrados no sistema."
    return render_template('cadastro_usuario.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('usuario')
        senha = request.form.get('senha')
        
        user = Usuario.query.filter_by(username=username, senha=senha).first()
        if user:
            session['user_id'] = user.id
            session['user_nome'] = user.nome
            session['is_admin'] = user.is_admin
            
            if user.is_admin:
                return redirect(url_for('admin'))
            return redirect(url_for('index'))
        else:
            return "Usuário ou senha incorretos."
    return render_template('login.html')

@app.route('/recuperar_senha', methods=['GET', 'POST'])
def recuperar_senha():
    if request.method == 'POST':
        cpf = request.form.get('cpf')
        user = Usuario.query.filter_by(cpf=cpf).first()
        if user:
            return f"""
            <div style="font-family: sans-serif; max-width: 400px; margin: 50px auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px; text-align: center;">
                <h3 style="color: #28a745;">Credenciais Encontradas!</h3>
                <p style="font-size: 16px;">Seu Usuário: <strong>{user.username}</strong></p>
                <p style="font-size: 16px;">Sua Senha: <strong>{user.senha}</strong></p>
                <br>
                <a href='/login' style="color: #007bff; text-decoration: none; font-weight: bold;">Voltar para o Login</a>
            </div>
            """
        else:
            return f"""
            <div style="font-family: sans-serif; max-width: 400px; margin: 50px auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px; text-align: center;">
                <h3 style="color: #dc3545;">Erro de Busca</h3>
                <p>Nenhum usuário foi localizado com este CPF.</p>
                <br>
                <a href='/recuperar_senha' style="color: #007bff; text-decoration: none; font-weight: bold;">Tentar novamente</a>
            </div>
            """
    return render_template('recuperar_senha.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==========================================
#          VISÃO DO USUÁRIO COMUM
# ==========================================

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    ativos = Ativo.query.all()
    meus_emprestimos = Emprestimo.query.filter_by(usuario_id=session['user_id']).all()
    return render_template('index.html', ativos=ativos, meus_emprestimos=meus_emprestimos)

@app.route('/retirar/<int:id>', methods=['POST'])
def retirar(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    ativo = Ativo.query.get_or_404(id)
    qtd_a_pegar = int(request.form.get('qtd_a_pegar', 1))
    
    # Processa o empréstimo se houver saldo disponível em estoque
    if 0 < qtd_a_pegar <= ativo.qtd_disponivel:
        ativo.qtd_disponivel -= qtd_a_pegar
        
        novo_emprestimo = Emprestimo(
            usuario_id=session['user_id'],
            ativo_id=ativo.id,
            quantidade_pega=qtd_a_pegar
        )
        db.session.add(novo_emprestimo)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/devolver_item/<int:id>')
def devolver_item(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    emprestimo = Emprestimo.query.get_or_404(id)
    
    # Restringe a devolução ao dono do empréstimo ou ao administrador
    if emprestimo.usuario_id == session['user_id'] or session.get('is_admin'):
        ativo = Ativo.query.get(emprestimo.ativo_id)
        ativo.qtd_disponivel += emprestimo.quantidade_pega  # Restitui saldo ao laboratório
        
        db.session.delete(emprestimo)
        db.session.commit()
        
    if session.get('is_admin'):
        return redirect(url_for('admin'))
    return redirect(url_for('index'))

# ==========================================
#          PAINEL ADMINISTRATIVO
# ==========================================

@app.route('/admin')
def admin():
    if 'user_id' not in session or not session.get('is_admin'):
        return "Acesso negado. Área restrita à administradores.", 403
        
    ativos = Ativo.query.all()
    usuarios = Usuario.query.filter_by(is_admin=False).all()
    todos_emprestimos = Emprestimo.query.all()
    
    return render_template('admin.html', 
                           ativos=ativos, 
                           usuarios=usuarios, 
                           todos_emprestimos=todos_emprestimos,
                           total_ativos=len(ativos),
                           total_users=len(usuarios))

@app.route('/admin/cadastro_equipamento', methods=['GET', 'POST'])
def cadastro_equipamento():
    if 'user_id' not in session or not session.get('is_admin'):
        return "Acesso negado.", 403
        
    if request.method == 'POST':
        qtd = int(request.form.get('quantidade', 1))
        novo = Ativo(
            nome=request.form.get('nome'),
            patrimonio=request.form.get('patrimonio'),
            laboratorio=request.form.get('laboratorio'),
            quantidade=qtd,
            qtd_disponivel=qtd  # Sincroniza estoque total e disponível no cadastro
        )
        db.session.add(novo)
        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('cadastro.html')

@app.route('/admin/deletar_ativo/<int:id>')
def deletar_ativo(id):
    if 'user_id' not in session or not session.get('is_admin'):
        return "Acesso negado.", 403
        
    ativo = Ativo.query.get_or_404(id)
    # Limpa referências na tabela de empréstimos antes de excluir o ativo
    Emprestimo.query.filter_by(ativo_id=id).delete()
    db.session.delete(ativo)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/deletar_usuario/<int:id>')
def deletar_usuario(id):
    if 'user_id' not in session or not session.get('is_admin'):
        return "Acesso negado.", 403
        
    user = Usuario.query.get_or_404(id)
    
    # Se o usuário for excluído com posses, devolve a quantidade correspondente para o estoque
    for emp in user.emprestimos:
        ativo = Ativo.query.get(emp.ativo_id)
        if ativo:
            ativo.qtd_disponivel += emp.quantidade_pega
        db.session.delete(emp)
        
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)