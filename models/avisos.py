from db import db
from datetime import datetime

class Aviso(db.Model):
    __tablename__ = 'avisos_dashboard'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    prioridade = db.Column(db.String(20), default='Normal') # 'Alta' ou 'Normal'
    
    autor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    autor = db.relationship('Usuario')

    def __repr__(self):
        return f'<Aviso {self.titulo}>'