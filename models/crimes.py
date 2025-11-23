from db import db

class Crime(db.Model):
    __tablename__ = 'crimes'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False) # Ex: Roubo Qualificado
    artigo = db.Column(db.String(50)) # Ex: Art. 157 CP
    pena = db.Column(db.String(100)) # Ex: Reclusão de 4 a 10 anos

    def __repr__(self):
        return f'<Crime {self.nome}>'