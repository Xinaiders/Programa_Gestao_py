#!/usr/bin/env python3
"""
Script para obter o conteúdo do arquivo JSON de credenciais
formatted para ser usado como variável de ambiente no Cloud Run
"""
import json
import os

def main():
    credential_file = 'sistema-consulta-produtos-2c00b5872af4.json'
    
    if not os.path.exists(credential_file):
        print(f"❌ Arquivo não encontrado: {credential_file}")
        return
    
    try:
        # Ler o arquivo
        with open(credential_file, 'r', encoding='utf-8') as f:
            data = f.read()
        
        # Validar JSON
        json.loads(data)
        
        print("=" * 80)
        print("CONTEÚDO PARA VARIÁVEL DE AMBIENTE GOOGLE_SERVICE_ACCOUNT_INFO")
        print("=" * 80)
        print()
        print("Copie o texto abaixo e cole na variável de ambiente do Cloud Run:")
        print()
        print("-" * 80)
        print(data)
        print("-" * 80)
        print()
        print("=" * 80)
        print("[OK] JSON válido e pronto para usar!")
        print("=" * 80)
        
    except json.JSONDecodeError as e:
        print(f"❌ Erro: Arquivo JSON inválido - {e}")
    except Exception as e:
        print(f"❌ Erro ao ler arquivo: {e}")

if __name__ == '__main__':
    main()

