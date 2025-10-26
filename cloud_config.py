#!/usr/bin/env python3
"""
Configurações específicas para Google Cloud Platform
"""

import os

def is_google_cloud():
    """Verifica se está rodando no Google Cloud"""
    return os.getenv('GAE_APPLICATION') is not None

def get_storage_config():
    """Retorna configuração de armazenamento baseada no ambiente"""
    if is_google_cloud():
        return {
            'type': 'cloud_storage',
            'bucket_name': os.getenv('GCS_BUCKET_NAME', 'romaneios-separacao'),
            'local_fallback': False
        }
    else:
        return {
            'type': 'local',
            'local_path': 'Romaneios_Separacao',
            'local_fallback': True
        }

def get_pdf_generator():
    """Retorna o gerador de PDF apropriado para o ambiente"""
    if is_google_cloud():
        from pdf_cloud_generator import salvar_pdf_cloud
        return salvar_pdf_cloud
    else:
        from pdf_browser_generator import salvar_pdf_direto_html
        return salvar_pdf_direto_html

def get_database_config():
    """Retorna configuração do banco de dados para o ambiente"""
    if is_google_cloud():
        # No GCP, usar Cloud SQL ou manter SQLite em memória
        return {
            'type': 'sqlite',
            'url': 'sqlite:///:memory:',  # Banco em memória para GCP
            'persistent': False
        }
    else:
        # Desenvolvimento local
        return {
            'type': 'sqlite',
            'url': 'sqlite:///estoque.db',
            'persistent': True
        }


