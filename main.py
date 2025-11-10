"""
Ponto de entrada para o Google Cloud App Engine
Este arquivo é necessário para o deploy no Google Cloud
"""

from app import app, db, cache_manager

# Atualizar criação de índices antes do primeiro request
if __name__ == '__main__':
    with app.app_context():
        # Criar tabelas se não existirem
        db.create_all()
        
        print("🚀 Aplicação iniciada com sucesso!")
        app.run(debug=False, host='0.0.0.0', port=8080)

