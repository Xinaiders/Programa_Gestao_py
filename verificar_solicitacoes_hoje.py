#!/usr/bin/env python3
"""
Script para verificar quantas solicitações existem de hoje no Google Sheets
"""

from datetime import datetime, date
import pandas as pd
import sys
import os

# Adicionar o diretório raiz ao path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import get_google_sheets_data, process_google_sheets_data

def verificar_solicitacoes_hoje():
    """Verifica quantas solicitações foram criadas hoje"""
    try:
        print("=" * 60)
        print("🔍 VERIFICAÇÃO DE SOLICITAÇÕES DE HOJE")
        print("=" * 60)
        
        hoje_obj = datetime.now().date()
        hoje_str = hoje_obj.strftime('%d/%m/%Y')
        
        print(f"\n📅 Data de hoje: {hoje_str} ({hoje_obj})")
        print(f"📅 Tipo da data de referência: {type(hoje_obj)}\n")
        
        # Buscar dados do Google Sheets
        print("📥 Buscando dados do Google Sheets...")
        df = get_google_sheets_data()
        
        if df is None or df.empty:
            print("❌ Erro: Não foi possível obter dados do Google Sheets")
            return
        
        print(f"✅ DataFrame obtido: {len(df)} linhas")
        print(f"📋 Colunas: {list(df.columns)}\n")
        
        # Verificar coluna de Data
        if 'Data' not in df.columns:
            print("⚠️ Coluna 'Data' não encontrada!")
            print(f"   Colunas disponíveis: {list(df.columns)}")
            return
        
        # Processar dados usando a mesma função do app
        print("🔄 Processando dados...")
        solicitacoes_list = process_google_sheets_data(df)
        
        print(f"✅ {len(solicitacoes_list)} solicitações processadas\n")
        print("=" * 60)
        print("📊 ANÁLISE DETALHADA DAS DATAS")
        print("=" * 60)
        
        solicitacoes_hoje = 0
        total_itens_hoje = 0
        problemas = []
        
        for i, s in enumerate(solicitacoes_list):
            try:
                data_solicitacao = None
                
                # Tentar acessar a data
                if hasattr(s, 'data') and s.data is not None:
                    data_solicitacao = s.data
                elif hasattr(s, '__dict__') and 'data' in s.__dict__:
                    data_solicitacao = s.__dict__['data']
                
                if not data_solicitacao:
                    problemas.append(f"Solicitação {i+1}: SEM DATA")
                    continue
                
                # Converter para date
                data_formatada = None
                
                # Timestamp do pandas
                if hasattr(data_solicitacao, 'to_pydatetime'):
                    try:
                        data_formatada = data_solicitacao.to_pydatetime().date()
                    except:
                        try:
                            data_formatada = data_solicitacao.date()
                        except:
                            pass
                # datetime
                elif isinstance(data_solicitacao, datetime):
                    data_formatada = data_solicitacao.date()
                # date
                elif isinstance(data_solicitacao, date):
                    data_formatada = data_solicitacao
                # string
                elif isinstance(data_solicitacao, str) and data_solicitacao.strip():
                    try:
                        if '/' in data_solicitacao:
                            data_parte = data_solicitacao.split(' ')[0]
                            try:
                                data_formatada = datetime.strptime(data_parte, '%d/%m/%Y').date()
                            except:
                                try:
                                    data_formatada = datetime.strptime(data_parte, '%d/%m/%y').date()
                                except:
                                    pass
                        elif '-' in data_solicitacao:
                            data_parte = data_solicitacao.split(' ')[0]
                            data_formatada = datetime.strptime(data_parte, '%Y-%m-%d').date()
                    except:
                        pass
                
                # Mostrar primeiras 10 solicitações
                if i < 10:
                    status = "✅ HOJE" if data_formatada == hoje_obj else "❌"
                    print(f"{status} Solicitação {i+1}:")
                    print(f"   Tipo original: {type(data_solicitacao)}")
                    print(f"   Valor original: {data_solicitacao}")
                    print(f"   Data formatada: {data_formatada}")
                    print(f"   É de hoje? {data_formatada == hoje_obj if data_formatada else 'N/A'}")
                    if hasattr(s, 'codigo'):
                        print(f"   Código: {s.codigo}")
                    print()
                
                # Contar se é de hoje
                if data_formatada and data_formatada == hoje_obj:
                    solicitacoes_hoje += 1
                    quantidade = int(s.quantidade) if hasattr(s, 'quantidade') and s.quantidade else 0
                    total_itens_hoje += quantidade
                    
            except Exception as e:
                problemas.append(f"Solicitação {i+1}: ERRO - {e}")
                continue
        
        print("=" * 60)
        print("📈 RESULTADO FINAL")
        print("=" * 60)
        print(f"✅ Solicitações de hoje: {solicitacoes_hoje}")
        print(f"📦 Total de itens de hoje: {total_itens_hoje}")
        print(f"📊 Total de solicitações analisadas: {len(solicitacoes_list)}")
        
        if problemas:
            print(f"\n⚠️ Problemas encontrados: {len(problemas)}")
            for problema in problemas[:10]:  # Mostrar apenas primeiros 10
                print(f"   - {problema}")
            if len(problemas) > 10:
                print(f"   ... e mais {len(problemas) - 10} problemas")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"❌ Erro ao verificar solicitações: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verificar_solicitacoes_hoje()
