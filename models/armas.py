from db import db
from datetime import datetime

class Arma(db.Model):
    __tablename__ = 'armas'

    id = db.Column(db.Integer, primary_key=True)
    
    # Classificação
    acervo = db.Column(db.String(20), nullable=False) # 'Patrimonio' ou 'Evidencia'
    tipo = db.Column(db.String(50), nullable=False)   # 'Pistola', 'Droga', 'Dinheiro', etc.
    
    # Detalhes Técnicos
    modelo = db.Column(db.String(100), nullable=False) # Para drogas: 'Cocaína', 'Maconha'
    marca = db.Column(db.String(100)) # Opcional
    calibre = db.Column(db.String(20)) # Para drogas: Quantidade/Peso (ex: '500g')
    numero_serie = db.Column(db.String(50), nullable=True) # Nem tudo tem série (drogas não tem)
    
    # Estado Atual
    status = db.Column(db.String(20), default='Disponivel')
    localizacao_atual = db.Column(db.String(100))
    
    # VÍNCULOS (Chaves Estrangeiras)
    boletim_id = db.Column(db.Integer, db.ForeignKey('boletins.id'), nullable=True)
    auto_prisao_id = db.Column(db.Integer, db.ForeignKey('autos_prisao.id'), nullable=True)
    
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos para acesso fácil no template
    boletim = db.relationship('Boletim', backref=db.backref('itens_apreendidos', lazy=True))
    auto_prisao = db.relationship('AutoPrisao', backref=db.backref('itens_apreendidos', lazy=True))

    def __repr__(self):
        return f'<Item {self.tipo} - {self.modelo}>'

class MovimentacaoArma(db.Model):
    __tablename__ = 'movimentacoes_armas'

    id = db.Column(db.Integer, primary_key=True)
    arma_id = db.Column(db.Integer, db.ForeignKey('armas.id'), nullable=False)
    usuario_responsavel_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    tipo_movimentacao = db.Column(db.String(20))
    destinatario = db.Column(db.String(150)) 
    data_movimentacao = db.Column(db.DateTime, default=datetime.utcnow)
    observacao = db.Column(db.Text)

    arma = db.relationship('Arma', backref=db.backref('historico', lazy=True))
    responsavel = db.relationship('Usuario')