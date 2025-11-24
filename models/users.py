from db import db
from datetime import datetime

class Cargo(db.Model):
    __tablename__ = 'cargos'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)
    nivel = db.Column(db.Integer, nullable=False) # 100=Delegado Geral, 10=Administrativo
    
    # Relacionamento
    usuarios = db.relationship('Usuario', backref='cargo_obj', lazy=True)

    def __repr__(self):
        return f'<Cargo {self.nome} Nível:{self.nivel}>'

class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    matricula = db.Column(db.String(20), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)
    
    cargo_id = db.Column(db.Integer, db.ForeignKey('cargos.id'), nullable=True)
    
    delegacia = db.Column(db.String(100))
    departamento = db.Column(db.String(100))
    endereco = db.Column(db.String(200))
    foto_perfil = db.Column(db.String(120), nullable=True, default='default.jpg')
    observacoes = db.Column(db.Text)
    
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    promocoes = db.relationship('Promocao', backref='servidor', lazy=True)
    
    # Relacionamento de Advertências (Correção de Foreign Keys ambíguas)
    advertencias = db.relationship('Advertencia', 
                                   foreign_keys='Advertencia.usuario_id', 
                                   backref='servidor', 
                                   lazy=True)
    
    advertencias_aplicadas = db.relationship('Advertencia', 
                                             foreign_keys='Advertencia.autor_id', 
                                             backref='autor_advertencia', 
                                             lazy=True)

    # --- CORREÇÃO DO ERRO ---
    # Esta propriedade permite usar usuario.cargo nos templates como antigamente
    @property
    def cargo(self):
        return self.cargo_obj.nome if self.cargo_obj else "Sem Cargo"

    @property
    def cargo_nome(self):
        return self.cargo_obj.nome if self.cargo_obj else "Sem Cargo"

    @property
    def nivel_hierarquico(self):
        return self.cargo_obj.nivel if self.cargo_obj else 0

    def __repr__(self):
        return f'<Usuario {self.nome}>'

class Promocao(db.Model):
    __tablename__ = 'promocoes'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    data_promocao = db.Column(db.DateTime, default=datetime.utcnow)
    cargo_anterior = db.Column(db.String(50))
    novo_cargo = db.Column(db.String(50), nullable=False)
    motivo = db.Column(db.String(200))

class Advertencia(db.Model):
    __tablename__ = 'advertencias'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    autor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id')) 
    data_aplicacao = db.Column(db.DateTime, default=datetime.utcnow)
    tipo = db.Column(db.String(50))
    descricao = db.Column(db.Text)

class LogAtividade(db.Model):
    __tablename__ = 'logs_atividade'
    id = db.Column(db.Integer, primary_key=True)
    autor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    acao = db.Column(db.String(50))
    alvo = db.Column(db.String(100))
    detalhes = db.Column(db.Text)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    
    autor = db.relationship('Usuario')