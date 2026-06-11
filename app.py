from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "trackit_secret_key_senai"

# Configuração do Banco de Dados
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trackit.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ==========================================
# MODELOS DO BANCO DE DADOS
# ==========================================
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)  # Armazena o Nome para compatibilidade com o Admin
    senha = db.Column(db.String(255), nullable=False) # Aumentado para suportar o hash criptografado
    is_admin = db.Column(db.Boolean, default=False)
    emprestimos = db.relationship('Emprestimo', backref='usuario', lazy=True)

class Ativo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    patrimonio = db.Column(db.String(50), unique=True, nullable=False)
    laboratorio = db.Column(db.Integer, nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)      
    qtd_disponivel = db.Column(db.Integer, nullable=False)   
    emprestimos = db.relationship('Emprestimo', backref='ativo', lazy=True)

class Emprestimo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    ativo_id = db.Column(db.Integer, db.ForeignKey('ativo.id'), nullable=False)
    quantidade_pega = db.Column(db.Integer, nullable=False)
    # MELHORIA 1: Colunas para Auditoria e Histórico Permanente
    status = db.Column(db.String(20), default='Ativo') # 'Ativo' ou 'Devolvido'
    data_retirada = db.Column(db.DateTime, default=datetime.now)
    data_devolucao = db.Column(db.DateTime, nullable=True)

# ==========================================
# ROTAS DE REDIRECIONAMENTO E SESSÃO
# ==========================================
@app.route('/')
def index():
    # Remove qualquer sessão aberta para garantir que caia sempre no Login ao digitar a URL pura
    session.clear() 
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_input = request.form.get('cpf')
        senha = request.form.get('senha')
        
        # 1. VALIDAÇÃO MASTER (SUPER ADMIN FIXO)
        if login_input == 'admin' and senha == 'admin123':
            session['username'] = 'admin'
            return redirect(url_for('pegar_itens'))
            
        # 2. VALIDAÇÃO POR CPF OU NOME COM CRIPTOGRAFIA
        user = Usuario.query.filter((Usuario.cpf == login_input) | (Usuario.nome == login_input)).first()
        if user and check_password_hash(user.senha, senha):
            session['username'] = user.username
            return redirect(url_for('pegar_itens'))
            
        flash('Credenciais incorretas. Verifique seu CPF/Nome e senha.', 'erro')
        return render_template('login.html')
            
    session.pop('_flashes', None)
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==========================================
# CADASTRO DE USUÁRIO (CRIPTOGRAFANDO A SENHA)
# ==========================================
@app.route('/cadastro_usuario', methods=['GET', 'POST'])
def cadastro_usuario():
    if request.method == 'POST':
        nome = request.form.get('nome')
        cpf = request.form.get('cpf')
        senha = request.form.get('senha')
        
        if not nome or not cpf or not senha:
            flash('Por favor, preencha todos os campos obrigatórios!', 'erro')
            return render_template('cadastro_usuario.html')

        cpf_existente = Usuario.query.filter_by(cpf=cpf).first()
        if cpf_existente:
            flash('Este CPF já está cadastrado no sistema!', 'erro')
            return render_template('cadastro_usuario.html')

        if nome.lower().strip() == 'admin':
            flash('Nome de usuário reservado pelo sistema!', 'erro')
            return render_template('cadastro_usuario.html')

        try:
            # Senha salva utilizando hash criptográfico seguro
            senha_criptografada = generate_password_hash(senha)
            novo_usuario = Usuario(nome=nome, cpf=cpf, username=nome, senha=senha_criptografada, is_admin=False)
            db.session.add(novo_usuario)
            db.session.commit()
            
            flash('Cadastro realizado com sucesso! Faça seu login informando o CPF.', 'sucesso')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            flash('Erro ao salvar no banco de dados. Tente novamente.', 'erro')
            return render_template('cadastro_usuario.html')

    session.pop('_flashes', None)
    return render_template('cadastro_usuario.html')

# ==========================================
# OUTRAS ROTAS DO SISTEMA
# ==========================================
@app.route('/admin')
def admin():
    username_logado = session.get('username')
    if not username_logado:
        return redirect(url_for('login'))
    
    # Validação do Usuário Fixo 'admin'
    if username_logado == 'admin':
        is_super_admin = True
    else:
        # Busca no banco de dados se o usuário da sessão existe de fato e é admin
        usuario_atual = Usuario.query.filter_by(username=username_logado).first()
        
        # SEGURANÇA CORRIGIDA: Se o usuário foi excluído ou is_admin for falso, barra na hora!
        if not usuario_atual or not usuario_atual.is_admin:
            session.clear() # Limpa o cookie órfão/antigo
            return redirect(url_for('login'))
        
        is_super_admin = False

    ativos = Ativo.query.all()
    usuarios = Usuario.query.all()
    usuarios_comuns = Usuario.query.filter_by(is_admin=False).all()
    historico_movimentacoes = Emprestimo.query.order_by(Emprestimo.id.desc()).all()
    
    total_ativos = db.session.query(db.func.sum(Ativo.quantidade)).scalar() or 0
    total_disponiveis = db.session.query(db.func.sum(Ativo.qtd_disponivel)).scalar() or 0
    total_em_uso = total_ativos - total_disponiveis
    total_users = Usuario.query.count()
    
    return render_template(
        'admin.html', 
        ativos=ativos, 
        usuarios=usuarios, 
        usuarios_comuns=usuarios_comuns,
        historico_movimentacoes=historico_movimentacoes,
        total_ativos=total_ativos, 
        total_disponiveis=total_disponiveis, 
        total_em_uso=total_em_uso, 
        total_users=total_users,
        is_super_admin=is_super_admin
    )

@app.route('/cadastro_equipamento', methods=['GET', 'POST'])
def cadastro_equipamento():
    if session.get('username') is None:
        return redirect(url_for('login'))
    return render_template('cadastro_equipamento.html')

@app.route('/api/resetar_senha_usuario', methods=['POST'])
def resetar_senha_usuario():
    data = request.json
    senha_admin = data.get('senha_admin')
    usuario_alvo_id = data.get('usuario_id')
    username_logado = session.get('username')
    
    if not username_logado:
        return jsonify({'sucesso': False, 'mensagem': 'Sessão expirada.'}), 401
        
    autenticado = False
    if username_logado == 'admin' and senha_admin == 'admin123':
        autenticado = True
    else:
        admin_logado = Usuario.query.filter_by(username=username_logado, is_admin=True).first()
        if admin_logado and check_password_hash(admin_logado.senha, senha_admin):
            autenticado = True
            
    if autenticado:
        user_alvo = Usuario.query.get(usuario_alvo_id)
        if user_alvo:
            user_alvo.senha = generate_password_hash("senai123") 
            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Senha resetada com sucesso para: senai123'})
            
    return jsonify({'sucesso': False, 'mensagem': 'Senha do administrador inválida.'}), 403

@app.route('/promover_admin', methods=['POST'])
def promover_admin():
    if session.get('username') != 'admin':
        return "Acesso negado!", 403
    usuario_id = request.form.get('usuario_id')
    user = Usuario.query.get(usuario_id)
    if user:
        user.is_admin = True
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/api/metricas_equipamento')
def metricas_equipamento():
    ativo_id = request.args.get('id')
    if not ativo_id or ativo_id == 'todos':
        total_ativos = db.session.query(db.func.sum(Ativo.quantidade)).scalar() or 0
        total_disponiveis = db.session.query(db.func.sum(Ativo.qtd_disponivel)).scalar() or 0
        total_em_uso = total_ativos - total_disponiveis
        return jsonify({'total': total_ativos, 'disponiveis': total_disponiveis, 'em_uso': total_em_uso})
    
    ativo = Ativo.query.get(ativo_id)
    if ativo:
        total_ativos = ativo.quantidade
        total_disponiveis = ativo.qtd_disponivel
        total_em_uso = total_ativos - total_disponiveis
    else:
        total_ativos, total_disponiveis, total_em_uso = 0, 0, 0
    return jsonify({'total': total_ativos, 'disponiveis': total_disponiveis, 'em_uso': total_em_uso})

@app.route('/recuperar_senha', methods=['GET', 'POST'])
def recuperar_senha(): return render_template('recuperar_senha.html')

@app.route('/deletar_ativo/<int:id>')
def deletar_ativo(id):
    ativo = Ativo.query.get_or_404(id)
    db.session.delete(ativo)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/deletar_usuario/<int:id>')
def deletar_usuario(id):
    user = Usuario.query.get_or_404(id)
    if user.emprestimos:
        for emp in user.emprestimos:
            if emp.status == 'Ativo':
                ativo = Ativo.query.get(emp.ativo_id)
                if ativo: ativo.qtd_disponivel += emp.quantidade_pega
            db.session.delete(emp)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('admin'))

# ==========================================
# RETIRAR E DEVOLVER MATERIAIS INTEGRADAS
# ==========================================
@app.route('/retirar/<int:id>', methods=['POST'])
def retirar(id):
    username_logado = session.get('username')
    if not username_logado: return redirect(url_for('login'))
    
    usuario = Usuario.query.filter_by(username=username_logado).first()
    ativo = Ativo.query.get_or_404(id)
    qtd_a_pegar = int(request.form.get('qtd_a_pegar', 1))
    
    if usuario and ativo and ativo.qtd_disponivel >= qtd_a_pegar:
        ativo.qtd_disponivel -= qtd_a_pegar
        
        novo_emprestimo = Emprestimo(
            usuario_id=usuario.id,
            ativo_id=ativo.id,
            quantidade_pega=qtd_a_pegar,
            status='Ativo',
            data_retirada=datetime.now()
        )
        db.session.add(novo_emprestimo)
        db.session.commit()
        flash(f'{qtd_a_pegar} unidade(s) de {ativo.nome} retiradas!', 'sucesso')
    else:
        flash('Quantidade indisponível no estoque!', 'erro')
        
    return redirect(url_for('pegar_itens'))

@app.route('/devolver_item/<int:id>')
def devolver_item(id):
    if 'username' not in session: return redirect(url_for('login'))
    
    emp = Emprestimo.query.get_or_404(id)
    if emp and emp.status == 'Ativo':
        ativo = Ativo.query.get(emp.ativo_id)
        if ativo:
            ativo.qtd_disponivel += emp.quantidade_pega
            
        emp.status = 'Devolvido'
        emp.data_devolucao = datetime.now()
        db.session.commit()
        flash('Equipamento unclaimed com sucesso!', 'sucesso')
        
    return redirect(url_for('pegar_itens'))

@app.route('/pegar_itens')
def pegar_itens():
    username_logado = session.get('username')
    if not username_logado: 
        return redirect(url_for('login'))
        
    usuario_atual = Usuario.query.filter_by(username=username_logado).first()
    
    # SEGURANÇA ADICIONAL: Caso o usuário tenha sido deletado enquanto estava logado
    if username_logado != 'admin' and not usuario_atual:
        session.clear()
        return redirect(url_for('login'))
        
    mostrar_botao_admin = True if username_logado == 'admin' or (usuario_atual and usuario_atual.is_admin) else False
    
    ativos = Ativo.query.all()
    meus_emprestimos = Emprestimo.query.filter_by(usuario_id=usuario_atual.id, status='Ativo').all() if usuario_atual else []
    user_nome = usuario_atual.nome if usuario_atual else 'Admin'
    
    # Injeta a variável na sessão para compatibilidade total com o front-end estável
    session['usuario'] = user_nome
    
    return render_template(
        'pegar_itens.html', 
        ativos=ativos, 
        meus_emprestimos=meus_emprestimos, 
        mostrar_botao_admin=mostrar_botao_admin, 
        user_nome=user_nome
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)