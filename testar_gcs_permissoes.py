#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para testar conexao e permissoes com Google Cloud Storage
"""

import os
import sys
from datetime import datetime

# Configurar encoding para evitar problemas com emojis no Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def testar_gcs():
    """Testa conexao e permissoes com Google Cloud Storage"""
    
    print("=" * 60)
    print("TESTE DE CONEXAO E PERMISSOES - GOOGLE CLOUD STORAGE")
    print("=" * 60)
    
    # Importar função de salvar_pdf_gcs
    try:
        from salvar_pdf_gcs import get_gcs_client
        print("OK: Modulo salvar_pdf_gcs importado com sucesso")
    except Exception as e:
        print(f"ERRO ao importar salvar_pdf_gcs: {e}")
        return False
    
    # Verificar variáveis de ambiente
    print("\nVerificando variaveis de ambiente...")
    k_service = os.environ.get('K_SERVICE')
    gcs_bucket = os.environ.get('GCS_BUCKET_NAME', 'romaneios-separacao')
    google_service_account = os.environ.get('GOOGLE_SERVICE_ACCOUNT_INFO')
    
    print(f"   - K_SERVICE: {k_service if k_service else 'NAO DEFINIDA (ambiente local)'}")
    print(f"   - GCS_BUCKET_NAME: {gcs_bucket}")
    print(f"   - GOOGLE_SERVICE_ACCOUNT_INFO: {'DEFINIDA' if google_service_account else 'NAO DEFINIDA'}")
    
    # Teste 1: Criar cliente GCS
    print("\nTeste 1: Criando cliente GCS...")
    try:
        client = get_gcs_client()
        if client:
            print("OK: Cliente GCS criado com sucesso!")
        else:
            print("ERRO: Nao foi possivel criar cliente GCS")
            return False
    except Exception as e:
        print(f"ERRO ao criar cliente GCS: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Teste 2: Acessar bucket
    print(f"\nTeste 2: Acessando bucket '{gcs_bucket}'...")
    try:
        bucket = client.bucket(gcs_bucket)
        
        # Tentar acessar metadados do bucket (melhor método)
        try:
            bucket.reload()
            print(f"OK: Bucket '{gcs_bucket}' existe e e acessivel!")
            print(f"   Localizacao: {bucket.location if hasattr(bucket, 'location') else 'N/A'}")
        except Exception as reload_error:
            # Fallback: tentar exists()
            error_msg = str(reload_error).lower()
            if '404' in error_msg or 'not found' in error_msg:
                print(f"ERRO: Bucket '{gcs_bucket}' nao encontrado!")
                print(f"   Verifique se o bucket existe no projeto")
                return False
            elif '403' in error_msg or 'permission denied' in error_msg or 'forbidden' in error_msg:
                print(f"ERRO: Sem permissao para acessar bucket '{gcs_bucket}'!")
                print(f"   Verifique as permissoes da service account")
                return False
            else:
                # Tentar método exists() como fallback
                if bucket.exists():
                    print(f"OK: Bucket '{gcs_bucket}' existe e e acessivel!")
                else:
                    print(f"ERRO: Bucket '{gcs_bucket}' nao existe ou nao e acessivel")
                    return False
    except Exception as e:
        print(f"ERRO ao acessar bucket: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Teste 3: Listar arquivos (verificar permissão de leitura)
    print(f"\nTeste 3: Listando arquivos no bucket (teste de leitura)...")
    try:
        blobs = list(bucket.list_blobs(max_results=5))
        print(f"OK: Permissao de LEITURA OK! Encontrados {len(blobs)} arquivos (mostrando ate 5)")
        if blobs:
            print("   Arquivos encontrados:")
            for blob in blobs:
                print(f"   - {blob.name} ({blob.size} bytes)")
    except Exception as e:
        print(f"ERRO ao listar arquivos (sem permissao de leitura?): {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Teste 4: Fazer upload de arquivo de teste (verificar permissão de escrita)
    print(f"\nTeste 4: Fazendo upload de arquivo de teste (teste de escrita)...")
    try:
        from google.cloud import storage as gcs
        
        # Criar um arquivo de teste em memória
        test_content = b"TESTE DE PERMISSAO - " + datetime.now().isoformat().encode()
        test_filename = "TESTE_PERMISSAO.txt"
        
        blob = bucket.blob(test_filename)
        blob.upload_from_string(test_content, content_type='text/plain')
        
        print(f"OK: Permissao de ESCRITA OK! Arquivo '{test_filename}' enviado com sucesso!")
        
        # Verificar se o arquivo foi realmente salvo
        if blob.exists():
            print(f"OK: Arquivo confirmado no bucket: {blob.name}")
            
            # Deletar arquivo de teste
            try:
                blob.delete()
                print(f"OK: Arquivo de teste removido: {test_filename}")
            except Exception as e:
                print(f"Aviso: Nao foi possivel remover arquivo de teste: {e}")
        
    except Exception as e:
        print(f"ERRO ao fazer upload (sem permissao de escrita?): {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Resumo
    print("\n" + "=" * 60)
    print("TODOS OS TESTES PASSARAM!")
    print("=" * 60)
    print("\nResumo:")
    print("   OK: Cliente GCS criado")
    print("   OK: Bucket acessivel")
    print("   OK: Permissao de LEITURA confirmada")
    print("   OK: Permissao de ESCRITA confirmada")
    print("\nO Cloud Storage esta configurado corretamente!")
    
    return True

if __name__ == '__main__':
    sucesso = testar_gcs()
    sys.exit(0 if sucesso else 1)
