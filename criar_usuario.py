# Arquivo: criar_usuario.py
from app import app, db
from models.users import Usuario  # Notei no seu log que o arquivo é 'users'
from werkzeug.security import generate_password_hash

def criar_admin():
    with app.app_context():
        # Verifica se o usuário já existe para não dar erro
        usuario_existente = Usuario.query.filter_by(matricula="12345").first()
        
        if not usuario_existente:
            senha_hash = generate_password_hash("minhasenha")
            usuario = Usuario(
                nome="Bruno Vitor", 
                matricula="12345", 
                senha=senha_hash, 
                cargo="Delegado Geral"
            )
            db.session.add(usuario)
            db.session.commit()
            print("Usuário criado com sucesso!")
        else:
            print("Usuário já existe.")

if __name__ == "__main__":
    criar_admin()