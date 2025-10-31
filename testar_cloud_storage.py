#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para testar salvamento de PDFs no Google Cloud Storage
"""

import os
import json
from google.cloud import storage as gcs
from google.oauth2.service_account import Credentials

def testar_cloud_storage():
    """Testa conexao com Cloud Storage usando as novas credenciais"""
    
    print("=" * 60)
    print("[TESTE] TESTE DE CLOUD STORAGE")
    print("=" * 60)
    
    bucket_name = 'romaneios-separacao'
    credential_file = 'gestaosolicitacao-fe66ad097590.json'
    
    try:
        # 1. Verificar arquivo de credenciais
        print(f"\n[1/5] Verificando arquivo de credenciais...")
        
        if not os.path.exists(credential_file):
            print(f"[ERRO] Arquivo nao encontrado: {credential_file}")
            return False
        
        print(f"[OK] Arquivo encontrado: {credential_file}")
        
        # 2. Carregar credenciais
        print(f"\n[2/5] Carregando credenciais...")
        with open(credential_file, 'r', encoding='utf-8') as f:
            cred_info = json.load(f)
            creds = Credentials.from_service_account_info(cred_info)
        
        print(f"[OK] Credenciais carregadas!")
        print(f"   Email: {cred_info.get('client_email')}")
        print(f"   Project ID: {cred_info.get('project_id')}")
        
        # 3. Criar cliente GCS
        print(f"\n[3/5] Criando cliente Cloud Storage...")
        client = gcs.Client(credentials=creds, project=cred_info['project_id'])
        print(f"[OK] Cliente criado com sucesso!")
        
        # 4. Verificar se bucket existe
        print(f"\n[4/5] Verificando bucket...")
        print(f"   Nome do bucket: {bucket_name}")
        
        try:
            bucket = client.bucket(bucket_name)
            
            # Tentar acessar o bucket
            if bucket.exists():
                print(f"[OK] Bucket encontrado: {bucket_name}")
            else:
                print(f"[AVISO] Bucket nao encontrado. Precisa ser criado.")
                print(f"   Acesse: https://console.cloud.google.com/storage/browser?project=gestaosolicitacao")
                return False
                
        except Exception as e:
            print(f"[ERRO] Erro ao acessar bucket: {e}")
            return False
        
        # 5. Testar permissões - listar arquivos
        print(f"\n[5/5] Testando permissoes (listando arquivos)...")
        try:
            blobs = list(bucket.list_blobs(max_results=5))
            print(f"[OK] Permissoes OK! Arquivos encontrados no bucket: {len(blobs)}")
            
            if blobs:
                print(f"\n   Primeiros arquivos:")
                for blob in blobs:
                    print(f"      - {blob.name} ({blob.size} bytes)")
            
        except Exception as e:
            print(f"[ERRO] Erro ao listar arquivos: {e}")
            print(f"\n[ACAO NECESSARIA]")
            print(f"   O email da service account precisa ter permissao no bucket!")
            print(f"   1. Acesse: https://console.cloud.google.com/storage/browser/{bucket_name}?project=gestaosolicitacao")
            print(f"   2. Clique em 'PERMISSOES'")
            print(f"   3. Adicione: gestsolicitacao@gestaosolicitacao.iam.gserviceaccount.com")
            print(f"   4. Role: 'Storage Object Creator' e 'Storage Object Viewer'")
            return False
        
        # 6. Testar upload de arquivo de teste
        print(f"\n[6/6] Testando upload de arquivo de teste...")
        try:
            test_content = b"TESTE DE PDF - Cloud Storage"
            test_blob = bucket.blob("TESTE_CONEXAO.txt")
            test_blob.upload_from_string(test_content, content_type='text/plain')
            print(f"[OK] Arquivo de teste enviado com sucesso!")
            
            # Deletar arquivo de teste
            test_blob.delete()
            print(f"[OK] Arquivo de teste removido")
            
        except Exception as e:
            print(f"[ERRO] Erro ao fazer upload de teste: {e}")
            print(f"   Verifique as permissoes do bucket")
            return False
        
        # Resumo final
        print(f"\n" + "=" * 60)
        print(f"[SUCESSO] TESTE CONCLUIDO COM SUCESSO!")
        print(f"=" * 60)
        print(f"[OK] Credenciais validas")
        print(f"[OK] Cliente GCS criado")
        print(f"[OK] Bucket acessivel")
        print(f"[OK] Permissoes configuradas corretamente")
        print(f"[OK] Upload funcionando")
        print(f"=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n[ERRO] ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    sucesso = testar_cloud_storage()
    exit(0 if sucesso else 1)

