from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELOS ---

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    matricula = db.Column(db.String(20), unique=True, nullable=False)
    ativos = db.relationship('Ativo', backref='responsavel', lazy=True)

class Ativo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    patrimonio = db.Column(db.String(50), unique=True, nullable=False)
    laboratorio = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='Disponível')
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)

with app.app_context():
    db.create_all()
    # Criar um utilizador de teste se não existir
    if not Usuario.query.first():
        user_teste = Usuario(nome="João Mateus", matricula="12345")
        db.session.add(user_teste)
        db.session.commit()

# --- ROTAS ---

@app.route('/')
def index():
    ativos = Ativo.query.all()
    usuarios = Usuario.query.all()
    return render_template('index.html', ativos=ativos, usuarios=usuarios)

@app.route('/adicionar', methods=['POST'])
def adicionar():
    novo = Ativo(
        nome=request.form.get('nome'),
        patrimonio=request.form.get('patrimonio'),
        laboratorio=request.form.get('laboratorio'),
        status='Disponível'
    )
    db.session.add(novo)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/retirar/<int:id>', methods=['POST'])
def retirar(id):
    ativo = Ativo.query.get_or_404(id)
    ativo.status = 'Em Uso'
    ativo.usuario_id = request.form.get('usuario_id')
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/devolver/<int:id>')
def devolver(id):
    ativo = Ativo.query.get_or_404(id)
    ativo.status = 'Disponível'
    ativo.usuario_id = None
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)