#!/usr/bin/env python3
"""
Script para criar usuários no sistema
Execute: python criar_usuarios.py
"""

from app import app, db, User

# Definir usuários que deseja criar
USUARIOS = [
    {'username': 'admin', 'email': 'marcosvinicius.info@gmail.com', 'password': 'admin123', 'is_admin': True},
    {'username': 'Marcos', 'email': 'xinaiders@gmail.com', 'password': 'Marcos', 'is_admin': True},
    {'username': 'Evandro', 'email': 'estoque@lineflex.com.br', 'password': 'Evandro', 'is_admin': False},
    {'username': 'operador2', 'email': 'operador2@estoque.com', 'password': 'operador2', 'is_admin': False},
    {'username': 'supervisor', 'email': 'supervisor@estoque.com', 'password': 'supervisor', 'is_admin': True},
    {'username': 'gestor', 'email': 'gestor@estoque.com', 'password': 'gestor', 'is_admin': True},
]

def criar_usuarios():
    """Cria todos os usuários definidos"""
    with app.app_context():
        print("🔄 Criando usuários no sistema...\n")
        
        for user_data in USUARIOS:
            # Verificar se usuário já existe
            if User.query.filter_by(username=user_data['username']).first():
                print(f"⏭️  Usuário '{user_data['username']}' já existe - ignorando")
                continue
            
            # Criar novo usuário
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                is_admin=user_data['is_admin']
            )
            user.set_password(user_data['password'])
            db.session.add(user)
            print(f"✅ Usuário '{user_data['username']}' criado com sucesso!")
        
        # Salvar no banco
        db.session.commit()
        print("\n✅ Todos os usuários foram criados!")

if __name__ == '__main__':
    criar_usuarios()

