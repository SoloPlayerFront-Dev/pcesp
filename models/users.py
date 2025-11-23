from db import db
from datetime import datetime

class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    matricula = db.Column(db.String(20), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)
    
    # Dados Profissionais
    cargo = db.Column(db.String(50))
    delegacia = db.Column(db.String(100))    # Novo: Ex: 1ª DP - Centro
    departamento = db.Column(db.String(100)) # Novo: Ex: Homicídios (DHPP)
    permissao = db.Column(db.String(20), default='comum')
    
    # Dados Pessoais
    endereco = db.Column(db.String(200))     # Novo
    foto_perfil = db.Column(db.String(120), nullable=True, default='default.jpg')
    
    # Anotações Administrativas
    observacoes = db.Column(db.Text)         # Novo: Para corregedoria ou notas do chefe
    
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamento com Promoções (1 Usuário tem Várias Promoções)
    promocoes = db.relationship('Promocao', backref='servidor', lazy=True)

    def __repr__(self):
        return f'<Usuario {self.nome}>'

class Promocao(db.Model):
    __tablename__ = 'promocoes'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    data_promocao = db.Column(db.DateTime, default=datetime.utcnow)
    
    cargo_anterior = db.Column(db.String(50))
    novo_cargo = db.Column(db.String(50), nullable=False)
    motivo = db.Column(db.String(200)) # Ex: Merecimento, Antiguidade

    def __repr__(self):
        return f'<Promocao {self.novo_cargo}>'