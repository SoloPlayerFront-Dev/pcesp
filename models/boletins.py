from db import db
from datetime import datetime

class Boletim(db.Model):
    __tablename__ = 'boletins'

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    
    autor = db.Column(db.String(120))
    vitima = db.Column(db.String(120))
    descricao = db.Column(db.Text)
    policial_responsavel = db.Column(db.String(120))
    
    status = db.Column(db.String(20), default='Pendente')
    
    # Mantemos este campo para compatibilidade ou como "Capa do B.O."
    arquivo_evidencia = db.Column(db.String(200), nullable=True)

    # Relacionamento com Múltiplos Anexos
    anexos = db.relationship('AnexoBoletim', backref='boletim', lazy=True)

    @property
    def numero_formatado(self):
        ano = self.data.year
        return f"B.O Nº {self.id:03d}/{ano}"

    def __repr__(self):
        return f'<Boletim {self.id}>'

class AnexoBoletim(db.Model):
    __tablename__ = 'anexos_boletim'

    id = db.Column(db.Integer, primary_key=True)
    boletim_id = db.Column(db.Integer, db.ForeignKey('boletins.id'), nullable=False)
    arquivo = db.Column(db.String(200), nullable=False) # Nome do arquivo
    tipo = db.Column(db.String(20)) # 'Imagem', 'PDF', 'Documento'
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)