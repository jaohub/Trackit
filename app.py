<<<<<<< HEAD
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# Configuração do Banco de Dados SQLite (gera o arquivo database.db automaticamente)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelo do Banco de Dados: O que vamos rastrear?
class Ativo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    patrimonio = db.Column(db.String(50), unique=True, nullable=False)
    laboratorio = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='Ativo') # Ativo, Manutenção, Baixado

# Cria o banco de dados dentro do contexto da aplicação
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    # Busca todos os ativos cadastrados
    ativos = Ativo.query.all()
    return render_template('index.html', ativos=ativos)

@app.route('/adicionar', methods=['POST'])
def adicionar():
    # Pega os dados do formulário HTML
    novo_ativo = Ativo(
        nome=request.form.get('nome'),
        patrimonio=request.form.get('patrimonio'),
        laboratorio=request.form.get('laboratorio'),
        status=request.form.get('status')
    )
    db.session.add(novo_ativo)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
=======
print("Oi mundo!")
print("hmjyk,uyki!")
>>>>>>> main
