#!/usr/bin/env python3
"""
SCRIPT DE EXEMPLO - Copie para criar_usuarios.py e ajuste as senhas

⚠️ SEGURANÇA: 
- NUNCA commite criar_usuarios.py com senhas reais no Git!
- Use variáveis de ambiente em produção
- Mantenha senhas padrão apenas para desenvolvimento local
"""

import os
from app import app, db, User

def obter_senha(usuario, senha_padrao, variavel_env):
    """
    Obtém senha de variável de ambiente ou usa padrão como fallback
    Variável de ambiente deve ter formato: USUARIO_ADMIN_PASSWORD, USUARIO_MARCOS_PASSWORD, etc.
    """
    senha_env = os.environ.get(variavel_env)
    if senha_env:
        print(f"✅ Senha de {usuario} obtida de variável de ambiente")
        return senha_env
    
    # Em produção, nunca usar senha padrão
    if os.environ.get('FLASK_ENV') == 'production':
        raise ValueError(f"❌ Variável de ambiente {variavel_env} não encontrada! Não use senhas padrão em produção.")
    
    # Apenas para desenvolvimento local
    print(f"⚠️  Usando senha padrão para {usuario} (apenas desenvolvimento local)")
    return senha_padrao

# Definir usuários que deseja criar
# ⚠️ IMPORTANTE: Em produção, defina as senhas via variáveis de ambiente!
# Exemplo: export USUARIO_ADMIN_PASSWORD="sua_senha_segura"
USUARIOS = [
    {
        'username': 'admin', 
        'email': 'seu-email@gmail.com', 
        'password': obter_senha('admin', 'ALTERE_A_SENHA_AQUI', 'USUARIO_ADMIN_PASSWORD'),
        'is_admin': True
    },
    # Adicione outros usuários aqui...
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

