from db import db
from datetime import datetime

class Pessoa(db.Model):
    __tablename__ = 'pessoas'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    rg = db.Column(db.String(20), unique=True) # Mudado de CPF para RG
    data_nascimento = db.Column(db.String(10)) # Novo
    nome_mae = db.Column(db.String(150))       # Novo
    endereco = db.Column(db.String(200))
    antecedentes = db.Column(db.Text) # Pode ser texto ou vinculado aos crimes depois
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Pessoa {self.nome}>'