#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para testar as credenciais do Google Sheets
"""

import os
import json
import sys
import gspread
from google.oauth2.service_account import Credentials

def testar_credenciais():
    """Testa conexao com Google Sheets usando as novas credenciais"""
    
    print("=" * 60)
    print("[TESTE] TESTE DE CREDENCIAIS - GOOGLE SHEETS")
    print("=" * 60)
    
    # Configurar escopos
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # ID da planilha
    spreadsheet_id = '1lh__GpPF_ZyCidLskYDf48aQEwv5Z8P2laelJN9aPuE'
    
    try:
        # 1. Verificar se o arquivo existe
        credential_file = 'gestaosolicitacao-fe66ad097590.json'
        print(f"\n[1/6] Verificando arquivo de credenciais...")
        
        if not os.path.exists(credential_file):
            print(f"[ERRO] Arquivo nao encontrado: {credential_file}")
            return False
        
        print(f"[OK] Arquivo encontrado: {credential_file}")
        
        # 2. Carregar credenciais
        print(f"\n[2/6] Carregando credenciais...")
        creds = Credentials.from_service_account_file(credential_file, scopes=scope)
        print(f"[OK] Credenciais carregadas com sucesso!")
        
        # Verificar informacoes da conta
        with open(credential_file, 'r', encoding='utf-8') as f:
            cred_info = json.load(f)
            print(f"   Email: {cred_info.get('client_email')}")
            print(f"   Project ID: {cred_info.get('project_id')}")
        
        # 3. Autorizar cliente
        print(f"\n[3/6] Autorizando cliente gspread...")
        client = gspread.authorize(creds)
        print(f"[OK] Cliente autorizado com sucesso!")
        
        # 4. Abrir planilha
        print(f"\n[4/6] Abrindo planilha...")
        print(f"   ID: {spreadsheet_id}")
        sheet = client.open_by_key(spreadsheet_id)
        print(f"[OK] Planilha aberta: {sheet.title}")
        
        # 5. Listar abas
        print(f"\n[5/6] Listando abas disponiveis...")
        worksheets = sheet.worksheets()
        for i, ws in enumerate(worksheets, 1):
            print(f"   {i}. {ws.title} (ID: {ws.id}, Linhas: {ws.row_count})")
        
        # 6. Testar leitura de dados (primeira aba)
        print(f"\n[6/6] Testando leitura de dados...")
        primeira_aba = worksheets[0]
        print(f"   Aba: {primeira_aba.title}")
        
        # Ler algumas linhas
        try:
            valores = primeira_aba.get_all_values()
            print(f"   [OK] Total de linhas encontradas: {len(valores)}")
            
            if len(valores) > 0:
                print(f"\n   Primeiras linhas:")
                for i, linha in enumerate(valores[:5], 1):
                    print(f"      Linha {i}: {linha[:3]}...")  # Mostrar apenas 3 primeiras colunas
            else:
                print(f"   [AVISO] Planilha vazia")
                
        except Exception as e:
            print(f"   [AVISO] Erro ao ler valores: {e}")
        
        # 7. Resumo final
        print(f"\n" + "=" * 60)
        print(f"[SUCESSO] TESTE CONCLUIDO COM SUCESSO!")
        print(f"=" * 60)
        print(f"[OK] Credenciais validas")
        print(f"[OK] Conexao estabelecida")
        print(f"[OK] Planilha acessivel")
        print(f"[OK] Permissoes configuradas corretamente")
        print(f"=" * 60)
        
        return True
        
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"\n[ERRO] Planilha nao encontrada!")
        print(f"   Verifique se o ID esta correto: {spreadsheet_id}")
        print(f"   Verifique se a planilha foi compartilhada com:")
        print(f"   gestsolicitacao@gestaosolicitacao.iam.gserviceaccount.com")
        return False
        
    except gspread.exceptions.APIError as e:
        print(f"\n[ERRO] ERRO DE API: {e}")
        if hasattr(e, 'response'):
            print(f"   Codigo: {e.response.status_code}")
            print(f"   Mensagem: {e.response.reason}")
        
        # Verificar se é erro de API não habilitada
        error_str = str(e)
        if 'has not been used' in error_str or 'is disabled' in error_str:
            print(f"\n[ACAO NECESSARIA]")
            print(f"   A API do Google Sheets precisa ser habilitada no projeto!")
            print(f"   Acesse o Console do Google Cloud:")
            print(f"   https://console.cloud.google.com/apis/library/sheets.googleapis.com?project=gestaosolicitacao")
            print(f"   Ou habilite via: https://console.developers.google.com/apis/api/sheets.googleapis.com/overview?project=gestaosolicitacao")
        
        return False
        
    except PermissionError as e:
        print(f"\n[ERRO] ERRO DE PERMISSAO!")
        print(f"   A API do Google Sheets precisa ser habilitada no projeto 'gestaosolicitacao'!")
        print(f"\n[ACAO NECESSARIA]")
        print(f"   1. Acesse: https://console.cloud.google.com/apis/library/sheets.googleapis.com?project=gestaosolicitacao")
        print(f"   2. Clique em 'HABILITAR'")
        print(f"   3. Aguarde alguns minutos para propagacao")
        print(f"   4. Execute este teste novamente")
        return False
        
    except Exception as e:
        error_str = str(e)
        print(f"\n[ERRO] ERRO: {e}")
        
        # Verificar se é erro de API não habilitada
        if 'has not been used' in error_str or 'is disabled' in error_str or 'SERVICE_DISABLED' in error_str:
            print(f"\n[ACAO NECESSARIA]")
            print(f"   A API do Google Sheets precisa ser habilitada no projeto!")
            print(f"   Acesse: https://console.cloud.google.com/apis/library/sheets.googleapis.com?project=gestaosolicitacao")
        
        # Verificar se é erro de permissão na planilha
        if 'PERMISSION_DENIED' in error_str or '403' in error_str:
            if 'sheets.googleapis.com' not in error_str:
                print(f"\n[ACAO NECESSARIA]")
                print(f"   Verifique se a planilha foi compartilhada com:")
                print(f"   gestsolicitacao@gestaosolicitacao.iam.gserviceaccount.com")
                print(f"   Permissao necessaria: 'Editor' ou 'Visualizador'")
        
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    sucesso = testar_credenciais()
    exit(0 if sucesso else 1)
