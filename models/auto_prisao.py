from db import db
from datetime import datetime

class AutoPrisao(db.Model):
    # ADICIONE ESTA LINHA OBRIGATORIAMENTE
    __tablename__ = 'autos_prisao' 
    
    id = db.Column(db.Integer, primary_key=True)
    preso = db.Column(db.String(120), nullable=False)
    descricao_fato = db.Column(db.Text, nullable=False)
    testemunhas = db.Column(db.Text)
    policial_responsavel = db.Column(db.String(120), nullable=False)
    horario = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamento (Opcional, mas útil se quiser acessar as armas a partir da prisão)
    # armas = db.relationship('Armas', backref='auto_prisao', lazy=True)

    def __repr__(self):
        return f'<AutoPrisao {self.id}>'