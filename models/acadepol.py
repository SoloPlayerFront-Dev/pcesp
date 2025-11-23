from db import db
from datetime import datetime

class Comunicado(db.Model):
    __tablename__ = 'comunicados_acadepol'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    
    # Categorias: 'Concurso', 'Resultado', 'Curso', 'Aviso'
    categoria = db.Column(db.String(50), nullable=False)
    
    # Arquivo anexo (PDF do edital, lista de aprovados, etc)
    arquivo_anexo = db.Column(db.String(200), nullable=True)
    
    # Quem publicou (Policial logado)
    autor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    
    data_publicacao = db.Column(db.DateTime, default=datetime.utcnow)
    ativo = db.Column(db.Boolean, default=True)

    autor = db.relationship('Usuario')

    def __repr__(self):
        return f'<Comunicado {self.titulo}>'