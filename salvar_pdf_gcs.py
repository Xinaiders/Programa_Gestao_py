#!/usr/bin/env python3
"""
Funções para salvar PDFs no Google Cloud Storage
"""

import os
from google.cloud import storage as gcs
from google.oauth2.service_account import Credentials
import json
import io

def get_gcs_client():
    """Cria cliente do Google Cloud Storage"""
    try:
        creds = None
        project_id = None
        
        # Opção 1: Ler de variável de ambiente (Cloud Run/Produção)
        service_account_info = os.environ.get('GOOGLE_SERVICE_ACCOUNT_INFO')
        if service_account_info:
            print("📋 Carregando credenciais da variável de ambiente...")
            info = json.loads(service_account_info)
            creds = Credentials.from_service_account_info(info)
            project_id = info.get('project_id')
            print("✅ Credenciais carregadas da variável de ambiente")
        
        # Opção 2: Ler de arquivo local (Desenvolvimento)
        if not creds:
            credential_file = 'gestaosolicitacao-fe66ad097590.json'
            if os.path.exists(credential_file):
                print(f"📋 Carregando credenciais do arquivo: {credential_file}")
                with open(credential_file, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                    creds = Credentials.from_service_account_info(info)
                    project_id = info.get('project_id')
                print("✅ Credenciais carregadas do arquivo")
            else:
                print(f"⚠️ Arquivo de credenciais não encontrado: {credential_file}")
                print("⚠️ Tentando usar Application Default Credentials...")
        
        # Criar cliente
        if creds and project_id:
            client = gcs.Client(credentials=creds, project=project_id)
            print(f"✅ Cliente GCS criado com credenciais (Projeto: {project_id})")
            return client
        else:
            # Fallback: Application Default Credentials
            print("⚠️ Usando Application Default Credentials")
            client = gcs.Client()
            return client
            
    except Exception as e:
        print(f"❌ Erro ao criar cliente GCS: {e}")
        import traceback
        traceback.print_exc()
        return None

def salvar_pdf_gcs(pdf_content, romaneio_id, bucket_name='romaneios-separacao', is_reprint=False):
    """
    Salva PDF no Google Cloud Storage
    
    Args:
        pdf_content: Conteúdo do PDF em bytes
        romaneio_id: ID do romaneio (ex: ROM-000001)
        bucket_name: Nome do bucket
        is_reprint: Se é uma reimpressão/cópia
    
    Returns:
        str: Caminho do arquivo no GCS (gs://bucket/file.pdf) ou None se erro
    """
    try:
        print(f"☁️ Salvando PDF no Cloud Storage: {romaneio_id}")
        
        # Criar cliente
        client = get_gcs_client()
        if not client:
            print("❌ Não foi possível criar cliente GCS")
            return None
        
        # Obter bucket
        bucket = client.bucket(bucket_name)
        
        # Nome do arquivo
        if is_reprint:
            filename = f"{romaneio_id}_Copia.pdf"
        else:
            filename = f"{romaneio_id}.pdf"
        
        # Caminho completo no GCS
        blob = bucket.blob(filename)
        
        # Upload do arquivo
        print(f"📤 Fazendo upload de {len(pdf_content)} bytes...")
        blob.upload_from_string(pdf_content, content_type='application/pdf')
        
        gcs_path = f"gs://{bucket_name}/{filename}"
        print(f"✅ PDF salvo no Cloud Storage: {gcs_path}")
        
        return gcs_path
        
    except Exception as e:
        print(f"❌ Erro ao salvar PDF no Cloud Storage: {e}")
        import traceback
        traceback.print_exc()
        return None

def buscar_pdf_gcs(romaneio_id, bucket_name='romaneios-separacao'):
    """
    Busca PDF do Google Cloud Storage
    
    Args:
        romaneio_id: ID do romaneio
        bucket_name: Nome do bucket
    
    Returns:
        bytes: Conteúdo do PDF ou None se não encontrado
    """
    try:
        print(f"🔍 Buscando PDF no Cloud Storage: {romaneio_id}")
        
        # Criar cliente
        client = get_gcs_client()
        if not client:
            return None
        
        # Obter bucket
        bucket = client.bucket(bucket_name)
        
        # Tentar arquivo original
        blob = bucket.blob(f"{romaneio_id}.pdf")
        if blob.exists():
            print(f"✅ PDF original encontrado: {romaneio_id}.pdf")
            return blob.download_as_bytes()
        
        # Tentar arquivo de cópia
        blob_copia = bucket.blob(f"{romaneio_id}_Copia.pdf")
        if blob_copia.exists():
            print(f"✅ PDF de cópia encontrado: {romaneio_id}_Copia.pdf")
            return blob_copia.download_as_bytes()
        
        print(f"❌ PDF não encontrado: {romaneio_id}")
        return None
        
    except Exception as e:
        print(f"❌ Erro ao buscar PDF no Cloud Storage: {e}")
        return None

def verificar_pdf_existe_gcs(romaneio_id, bucket_name='romaneios-separacao'):
    """
    Verifica se PDF existe no Cloud Storage
    
    Args:
        romaneio_id: ID do romaneio
        bucket_name: Nome do bucket
    
    Returns:
        bool: True se existe, False caso contrário
    """
    try:
        client = get_gcs_client()
        if not client:
            return False
        
        bucket = client.bucket(bucket_name)
        
        # Verificar arquivo original
        if bucket.blob(f"{romaneio_id}.pdf").exists():
            return True
        
        # Verificar arquivo de cópia
        if bucket.blob(f"{romaneio_id}_Copia.pdf").exists():
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ Erro ao verificar PDF: {e}")
        return False


