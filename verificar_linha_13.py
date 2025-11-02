#!/usr/bin/env python3
"""
Script para verificar especificamente a linha 13 que tem data de hoje
"""

from datetime import datetime, date
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import get_google_sheets_connection

def verificar_linha_13():
    """Verifica especificamente a linha 13 da planilha"""
    try:
        print("=" * 60)
        print("🔍 VERIFICAÇÃO ESPECÍFICA DA LINHA 13")
        print("=" * 60)
        
        hoje_obj = datetime.now().date()
        hoje_str = hoje_obj.strftime('%d/%m/%Y')
        
        print(f"\n📅 Data de hoje: {hoje_str}\n")
        
        # Conectar diretamente com Google Sheets
        sheet = get_google_sheets_connection()
        if not sheet:
            print("❌ Não foi possível conectar com Google Sheets")
            return
        
        # Acessar a primeira aba (Solicitações)
        worksheet = sheet.get_worksheet(0)
        all_values = worksheet.get_all_values()
        
        print(f"📋 Total de linhas na planilha: {len(all_values)}")
        print(f"📋 Cabeçalho: {all_values[0] if all_values else 'VAZIO'}\n")
        
        # Verificar linha 13 especificamente (índice 12, pois começa em 0)
        if len(all_values) >= 13:
            linha_13 = all_values[12]  # Linha 13 (índice 12)
            print("=" * 60)
            print("📋 DADOS DA LINHA 13 (RAW)")
            print("=" * 60)
            for i, valor in enumerate(linha_13):
                header = all_values[0][i] if i < len(all_values[0]) else f"Coluna {i+1}"
                print(f"   {header}: '{valor}'")
            
            # Verificar se tem dados válidos
            print("\n" + "=" * 60)
            print("🔍 ANÁLISE DE FILTROS")
            print("=" * 60)
            
            # Verificar colunas necessárias
            headers = all_values[0]
            idx_data = headers.index('Data') if 'Data' in headers else None
            idx_codigo = headers.index('Código') if 'Código' in headers else None
            idx_solicitante = headers.index('Solicitante') if 'Solicitante' in headers else None
            
            if idx_data is not None:
                data_raw = linha_13[idx_data] if idx_data < len(linha_13) else ''
                print(f"✅ Data encontrada: '{data_raw}'")
                
                # Tentar parsear a data
                try:
                    data_obj = pd.to_datetime(data_raw, errors='coerce')
                    if pd.notna(data_obj):
                        data_date = data_obj.date()
                        print(f"   Data parseada: {data_date}")
                        print(f"   É de hoje? {data_date == hoje_obj}")
                        
                        if data_date == hoje_obj:
                            print("\n✅✅✅ ESTA LINHA DEVERIA SER CONTADA COMO 'DE HOJE' ✅✅✅\n")
                        else:
                            print(f"\n⚠️ Esta linha NÃO é de hoje (data: {data_date})\n")
                    else:
                        print("   ❌ Erro ao parsear data (resultou em NaT)")
                except Exception as e:
                    print(f"   ❌ Erro ao parsear data: {e}")
            else:
                print("❌ Coluna 'Data' não encontrada no cabeçalho")
            
            if idx_codigo is not None:
                codigo = linha_13[idx_codigo] if idx_codigo < len(linha_13) else ''
                print(f"📦 Código: '{codigo}'")
                if not codigo or codigo.strip() == '':
                    print("   ⚠️ Código vazio - linha pode ser filtrada!")
            
            if idx_solicitante is not None:
                solicitante = linha_13[idx_solicitante] if idx_solicitante < len(linha_13) else ''
                print(f"👤 Solicitante: '{solicitante}'")
                if not solicitante or solicitante.strip() == '':
                    print("   ⚠️ Solicitante vazio - linha pode ser filtrada!")
            
            # Verificar se passaria pelo filtro do get_google_sheets_data
            print("\n" + "=" * 60)
            print("🔍 TESTE DO FILTRO get_google_sheets_data")
            print("=" * 60)
            
            # Simular o filtro que é aplicado em get_google_sheets_data
            codigo_valido = idx_codigo is not None and idx_codigo < len(linha_13) and linha_13[idx_codigo] and linha_13[idx_codigo].strip() != ''
            solicitante_valido = idx_solicitante is not None and idx_solicitante < len(linha_13) and linha_13[idx_solicitante] and linha_13[idx_solicitante].strip() != ''
            
            print(f"   Código válido? {codigo_valido}")
            print(f"   Solicitante válido? {solicitante_valido}")
            
            if codigo_valido and solicitante_valido:
                print("   ✅ Esta linha PASSA pelo filtro e deveria aparecer no DataFrame")
            else:
                print("   ❌ Esta linha É FILTRADA e NÃO aparece no DataFrame")
                print("      (O filtro remove linhas sem código OU sem solicitante)")
        else:
            print("❌ Linha 13 não existe na planilha")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verificar_linha_13()
