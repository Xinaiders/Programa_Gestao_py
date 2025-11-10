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
        
        # Debug: verificar ambiente
        is_cloud_run = os.environ.get('K_SERVICE') is not None
        print(f"🌐 Ambiente detectado: {'Cloud Run' if is_cloud_run else 'Local'}")
        print(f"🔍 Variáveis de ambiente disponíveis:")
        print(f"   - K_SERVICE: {os.environ.get('K_SERVICE', 'NÃO DEFINIDA')}")
        print(f"   - GOOGLE_SERVICE_ACCOUNT_INFO: {'DEFINIDA' if os.environ.get('GOOGLE_SERVICE_ACCOUNT_INFO') else 'NÃO DEFINIDA'}")
        print(f"   - GCS_BUCKET_NAME: {os.environ.get('GCS_BUCKET_NAME', 'NÃO DEFINIDA')}")
        
        # Opção 1: Ler de variável de ambiente (Cloud Run/Produção)
        service_account_info = os.environ.get('GOOGLE_SERVICE_ACCOUNT_INFO')
        if service_account_info:
            print("📋 Carregando credenciais da variável de ambiente...")
            try:
                # Limpar e preparar JSON (remover quebras de linha extras, espaços)
                # Pode estar como string JSON dentro de string (double encoding)
                cleaned_info = service_account_info.strip()
                
                # Tentar fazer decode se estiver como string escapada
                if cleaned_info.startswith('"') and cleaned_info.endswith('"'):
                    print("📋 Detectado JSON como string escapada, fazendo decode...")
                    cleaned_info = json.loads(cleaned_info)
                
                # Tentar fazer parse do JSON
                if isinstance(cleaned_info, str):
                    info = json.loads(cleaned_info)
                else:
                    info = cleaned_info
                
                # Validar campos obrigatórios
                required_fields = ['type', 'project_id', 'private_key', 'client_email']
                missing_fields = [field for field in required_fields if field not in info]
                if missing_fields:
                    print(f"❌ ERRO: Campos obrigatórios faltando: {missing_fields}")
                    return None
                
                creds = Credentials.from_service_account_info(info)
                project_id = info.get('project_id')
                client_email = info.get('client_email', 'N/A')
                print(f"✅ Credenciais carregadas da variável de ambiente")
                print(f"   Projeto: {project_id}")
                print(f"   Service Account: {client_email}")
            except json.JSONDecodeError as e:
                print(f"❌ ERRO: JSON inválido na variável GOOGLE_SERVICE_ACCOUNT_INFO")
                print(f"   Erro: {e}")
                print(f"   Tamanho da string: {len(service_account_info)} caracteres")
                print(f"   Primeiros 200 caracteres: {service_account_info[:200]}")
                print(f"   Últimos 100 caracteres: {service_account_info[-100:]}")
                return None
            except KeyError as e:
                print(f"❌ ERRO: Campo obrigatório faltando no JSON: {e}")
                print(f"   Campos disponíveis: {list(info.keys()) if 'info' in locals() else 'N/A'}")
                return None
            except Exception as e:
                print(f"❌ ERRO ao processar credenciais da variável: {e}")
                import traceback
                traceback.print_exc()
                return None
        
        # Opção 2: Ler de arquivo local (Desenvolvimento)
        if not creds:
            credential_file = 'gestaosolicitacao-fe66ad097590.json'
            if os.path.exists(credential_file):
                print(f"📋 Carregando credenciais do arquivo: {credential_file}")
                try:
                    with open(credential_file, 'r', encoding='utf-8') as f:
                        info = json.load(f)
                        creds = Credentials.from_service_account_info(info)
                        project_id = info.get('project_id')
                    print(f"✅ Credenciais carregadas do arquivo (Projeto: {project_id})")
                except Exception as e:
                    print(f"❌ ERRO ao ler arquivo de credenciais: {e}")
                    return None
            else:
                if is_cloud_run:
                    print(f"⚠️ ATENÇÃO: No Cloud Run e arquivo {credential_file} não encontrado")
                    print(f"⚠️ Verifique se a variável GOOGLE_SERVICE_ACCOUNT_INFO está configurada!")
                else:
                    print(f"⚠️ Arquivo de credenciais não encontrado: {credential_file}")
                    print("⚠️ Tentando usar Application Default Credentials...")
        
        # Criar cliente
        if creds and project_id:
            try:
                client = gcs.Client(credentials=creds, project=project_id)
                print(f"✅ Cliente GCS criado com credenciais (Projeto: {project_id})")
                return client
            except Exception as e:
                print(f"❌ ERRO ao criar cliente GCS com credenciais: {e}")
                import traceback
                traceback.print_exc()
                return None
        else:
            # Fallback: Application Default Credentials (só funciona se a service account do Cloud Run tiver permissões)
            if is_cloud_run:
                print("⚠️ ATENÇÃO: Tentando usar Application Default Credentials no Cloud Run")
                print("⚠️ Certifique-se que a service account do Cloud Run tem permissões no bucket!")
            else:
                print("⚠️ Usando Application Default Credentials")
            try:
                client = gcs.Client()
                print("✅ Cliente GCS criado com Application Default Credentials")
                return client
            except Exception as e:
                print(f"❌ ERRO ao criar cliente GCS com Application Default Credentials: {e}")
                import traceback
                traceback.print_exc()
                return None
            
    except Exception as e:
        print(f"❌ ERRO CRÍTICO ao criar cliente GCS: {e}")
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
        print(f"☁️ === INÍCIO: Salvando PDF no Cloud Storage ===")
        print(f"☁️ Romaneio ID: {romaneio_id}")
        print(f"☁️ Bucket: {bucket_name}")
        print(f"☁️ Tamanho do PDF: {len(pdf_content)} bytes")
        
        # Criar cliente
        client = get_gcs_client()
        if not client:
            print("❌ ERRO: Não foi possível criar cliente GCS")
            return None
        
        # Verificar se bucket existe e temos acesso
        try:
            bucket = client.bucket(bucket_name)
            # Tentar acessar metadados do bucket para verificar permissões
            print(f"🔍 Verificando acesso ao bucket: {bucket_name}")
            bucket.reload()
            print(f"✅ Bucket encontrado e acessível: {bucket_name}")
        except Exception as bucket_error:
            error_msg = str(bucket_error).lower()
            if '404' in error_msg or 'not found' in error_msg:
                print(f"❌ ERRO: Bucket '{bucket_name}' não encontrado!")
                print(f"   Verifique se o bucket existe no projeto")
            elif '403' in error_msg or 'permission denied' in error_msg or 'forbidden' in error_msg:
                print(f"❌ ERRO: Sem permissão para acessar o bucket '{bucket_name}'!")
                print(f"   Verifique as permissões da service account no bucket")
                print(f"   Permissões necessárias: Storage Object Creator, Storage Object Viewer")
            else:
                print(f"❌ ERRO ao acessar bucket: {bucket_error}")
            import traceback
            traceback.print_exc()
            return None
        
        # Nome do arquivo
        if is_reprint:
            filename = f"{romaneio_id}_Copia.pdf"
        else:
            filename = f"{romaneio_id}.pdf"
        
        # Caminho completo no GCS
        blob = bucket.blob(filename)
        
        # Upload do arquivo
        print(f"📤 Fazendo upload de {len(pdf_content)} bytes para {filename}...")
        try:
            blob.upload_from_string(pdf_content, content_type='application/pdf')
            
            # Verificar se o upload foi bem-sucedido
            if not blob.exists():
                print(f"⚠️ ATENÇÃO: Upload completado mas arquivo não encontrado no bucket")
                return None
            
            gcs_path = f"gs://{bucket_name}/{filename}"
            file_size = blob.size
            print(f"✅ === SUCESSO: PDF salvo no Cloud Storage ===")
            print(f"✅ Caminho: {gcs_path}")
            print(f"✅ Tamanho confirmado: {file_size} bytes")
            return gcs_path
        except Exception as upload_error:
            error_msg = str(upload_error).lower()
            if '403' in error_msg or 'permission denied' in error_msg or 'forbidden' in error_msg:
                print(f"❌ ERRO: Sem permissão para fazer upload no bucket!")
                print(f"   Verifique se a service account tem permissão 'Storage Object Creator'")
            elif '404' in error_msg or 'not found' in error_msg:
                print(f"❌ ERRO: Bucket não encontrado durante upload")
            else:
                print(f"❌ ERRO durante upload: {upload_error}")
            import traceback
            traceback.print_exc()
            return None
        
    except Exception as e:
        print(f"❌ === ERRO CRÍTICO ao salvar PDF no Cloud Storage ===")
        print(f"❌ Erro: {e}")
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


