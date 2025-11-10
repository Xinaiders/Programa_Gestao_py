#!/usr/bin/env python3
"""
Configurações para geração de PDF
"""

# Configurações de pasta para PDFs
PDF_CONFIG = {
    # Pasta local para salvar PDFs
    'PASTA_DESTINO': "Romaneios_Separacao",  # Pasta local no projeto
    
    # Se True, cria a pasta se não existir
    'CRIAR_PASTA_AUTO': True,
    
    # Nome da pasta padrão (usado quando PASTA_DESTINO é None)
    'NOME_PASTA_PADRAO': "Romaneios_Separacao",
    
    # Tipo de armazenamento: 'local' ou 'google_drive'
    'TIPO_ARMAZENAMENTO': 'local'
}

def obter_configuracao_pasta():
    """
    Retorna a configuração da pasta de destino
    
    Returns:
        str: Nome da pasta ou None para usar padrão
    """
    return PDF_CONFIG['PASTA_DESTINO']

def obter_nome_pasta_padrao():
    """
    Retorna o nome da pasta padrão
    
    Returns:
        str: Nome da pasta padrão
    """
    return PDF_CONFIG['NOME_PASTA_PADRAO']

def deve_criar_pasta_auto():
    """
    Retorna se deve criar pasta automaticamente
    
    Returns:
        bool: True se deve criar automaticamente
    """
    return PDF_CONFIG['CRIAR_PASTA_AUTO']

def obter_tipo_armazenamento():
    """
    Retorna o tipo de armazenamento configurado
    
    Returns:
        str: 'local' ou 'google_drive'
    """
    return PDF_CONFIG['TIPO_ARMAZENAMENTO']
