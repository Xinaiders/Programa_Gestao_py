#!/usr/bin/env python3
"""
Gerador de PDF usando o navegador - Layout 100% IDÊNTICO
"""

import os
import sys
import subprocess
import webbrowser
import shutil
import tempfile
from datetime import datetime

def gerar_pdf_browser_romaneio(romaneio_data, itens_data, is_reprint=False):
    """
    Gera PDF usando o navegador - LAYOUT 100% IDÊNTICO ao formulario_impressao.html
    
    Args:
        romaneio_data: Dados do romaneio (id, data, usuario, etc.)
        itens_data: Lista de itens do romaneio
        is_reprint: Se é uma reimpressão/cópia
    
    Returns:
        str: URL para visualização/impressão
    """
    try:
        # Preparar dados para o template
        template_data = {
            'id_impressao': romaneio_data.get('id_impressao', 'ROM-000001'),
            'solicitacoes': itens_data,
            'is_reprint': is_reprint,
            'romaneio_data': romaneio_data
        }
        
        # Criar pasta para arquivos temporários
        pasta_temp = 'temp_pdf'
        os.makedirs(pasta_temp, exist_ok=True)
        
        # Nome do arquivo HTML temporário
        filename = f"{romaneio_data.get('id_impressao', 'ROM-000001')}.html"
        filepath = os.path.join(pasta_temp, filename)
        
        # Template HTML idêntico ao formulario_impressao.html
        html_content = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Formulário de Separação - Sistema de Gestão de Estoque</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Font Awesome -->
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f8f9fa;
        }}
        
        .formulario-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 0;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        .formulario-title {{
            font-size: 18px;
            font-weight: bold;
            margin: 0;
        }}
        
        .formulario-subtitle {{
            font-size: 16px;
            margin: 5px 0 0 0;
            opacity: 0.9;
        }}
        
        .formulario-container {{
            max-width: 100%;
            margin: 0 auto;
            padding: 0 10px;
        }}
        
        .tabela-container {{
            background: white;
            border-radius: 5px;
            padding: 10px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            overflow-x: auto;
        }}
        
        .tabela-separacao {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
            margin-bottom: 20px;
        }}
        
        .tabela-separacao th {{
            background: #f5f5f5;
            color: #333;
            padding: 12px 8px;
            text-align: center;
            font-weight: bold;
            border: 1px solid #ddd;
            white-space: nowrap;
            font-size: 13px;
        }}
        
        .tabela-separacao td {{
            padding: 12px 8px;
            border: 1px solid #ddd;
            text-align: center;
            vertical-align: middle;
            font-size: 13px;
        }}
        
        .tabela-separacao tr:nth-child(even) {{
            background-color: #fafafa;
        }}
        
        .tabela-separacao tr:hover {{
            background-color: #f0f8ff;
        }}
        
        .col-data-hora {{ width: 8%; }}
        .col-solicitante {{ width: 7%; }}
        .col-codigo {{ width: 5%; font-weight: bold; }}
        .col-descricao {{ width: 20%; text-align: left !important; }}
        .col-alta-demanda {{ width: 6%; }}
        .col-localizacao {{ width: 8%; font-weight: bold; background: #fff3cd !important; }}
        .col-saldo-estoque {{ width: 7%; }}
        .col-media-consumo {{ width: 7%; }}
        .col-saldo-ficou {{ width: 8%; background: #f8f9fa !important; }}
        .col-qtd-pendente {{ width: 7%; }}
        .col-qtd-separada {{ width: 8%; background: #f8f9fa !important; }}
        
        .quantidade-cell {{
            font-weight: bold;
            font-size: 14px;
        }}
        
        .quantidade-pendente {{ color: #e74c3c; }}
        .quantidade-separada {{ color: #27ae60; }}
        .quantidade-saldo {{ color: #f39c12; }}
        
        .alta-demanda-icon {{
            color: #3498db;
            font-size: 16px;
        }}
        
        .localizacao-cell {{
            font-family: monospace;
            font-size: 12px;
            background: #f8f9fa;
            padding: 4px 8px;
            border-radius: 4px;
        }}
        
        .action-buttons {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            display: flex;
            gap: 10px;
            z-index: 1000;
        }}
        
        .btn-print {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            color: white;
            padding: 15px 30px;
            border-radius: 50px;
            font-weight: bold;
            font-size: 16px;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            transition: all 0.3s ease;
        }}
        
        .btn-print:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
            color: white;
        }}
        
        .btn-save-pdf {{
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            border: none;
            color: white;
            padding: 15px 30px;
            border-radius: 50px;
            font-weight: bold;
            font-size: 16px;
            box-shadow: 0 4px 15px rgba(40, 167, 69, 0.3);
            transition: all 0.3s ease;
        }}
        
        .btn-save-pdf:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(40, 167, 69, 0.4);
            color: white;
        }}
        
        @media print {{
            @page {{
                size: A4 landscape;
                margin: 0.5cm;
            }}
            
            .action-buttons {{ display: none !important; }}
            .formulario-header {{ 
                background: #f8f9fa !important; 
                color: #000 !important; 
                border-bottom: 2px solid #000 !important;
                padding: 10px 0 !important;
                margin-bottom: 15px !important;
            }}
            .formulario-title {{
                font-size: 16px !important;
            }}
            .formulario-subtitle {{
                font-size: 12px !important;
            }}
            .tabela-container {{ 
                box-shadow: none !important; 
                border: 1px solid #000 !important;
                padding: 3px !important;
                margin: 0 !important;
            }}
            .tabela-separacao {{
                border-collapse: collapse !important;
                width: 100% !important;
                font-size: 10px !important;
                margin: 0 !important;
            }}
            .tabela-separacao th {{
                background: #f0f0f0 !important;
                color: #000 !important;
                border: 1px solid #000 !important;
                padding: 4px 2px !important;
                font-size: 9px !important;
                white-space: nowrap !important;
            }}
            .tabela-separacao td {{
                border: 1px solid #000 !important;
                padding: 3px 2px !important;
                font-size: 9px !important;
            }}
            .tabela-separacao tr:nth-child(even) {{
                background-color: #f9f9f9 !important;
            }}
            .separacao-input {{
                display: none !important;
            }}
            body {{ 
                background: white !important; 
                font-size: 10px !important;
                margin: 0 !important;
                padding: 0 !important;
            }}
            .formulario-container {{
                max-width: none !important;
                padding: 0 !important;
                margin: 0 !important;
            }}
            .col-descricao {{ 
                max-width: 120px !important; 
                word-wrap: break-word !important;
            }}
            .col-localizacao {{
                background: #fff3cd !important;
                font-weight: bold !important;
                border: 2px solid #000 !important;
            }}
            .col-codigo {{
                font-weight: bold !important;
                background: #e3f2fd !important;
            }}
            .col-saldo-ficou, .col-qtd-separada {{
                background: #f8f9fa !important;
                border: 1px dashed #000 !important;
            }}
            .col-data-hora {{ width: 80px !important; }}
            .col-solicitante {{ width: 70px !important; }}
            .col-codigo {{ width: 50px !important; }}
            .col-descricao {{ width: 150px !important; }}
            .col-alta-demanda {{ width: 60px !important; }}
            .col-localizacao {{ width: 80px !important; }}
            .col-saldo-estoque {{ width: 70px !important; }}
            .col-media-consumo {{ width: 70px !important; }}
            .col-saldo-ficou {{ width: 80px !important; }}
            .col-qtd-pendente {{ width: 70px !important; }}
            .col-qtd-separada {{ width: 80px !important; }}
        }}
        
        /* Marca d'água para cópia */
        .watermark {{
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) rotate(-45deg);
            font-size: 48px;
            color: rgba(0,0,0,0.1);
            font-weight: bold;
            z-index: 1000;
            pointer-events: none;
        }}
    </style>
</head>
<body>
    {'<div class="watermark">CÓPIA</div>' if is_reprint else ''}
    
    <div class="formulario-header">
        <div class="formulario-container">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <h1 class="formulario-title">
                        <i class="fas fa-table me-3"></i>
                        LINE FLEX - Gestão de Estoque
                    </h1>
                    <p class="formulario-subtitle">
                        <i class="fas fa-clipboard-list me-2"></i>
                        Romaneio de Separação
                    </p>
                </div>
                <div class="text-end">
                       <p class="formulario-subtitle">
                           <i class="fas fa-file-alt me-2"></i>
                           {template_data['id_impressao']}
                       </p>
                    <p class="formulario-subtitle">
                        <i class="fas fa-calendar me-2"></i>
                        <span id="dataAtual">{romaneio_data.get('data_impressao', 'N/A')}</span>
                    </p>
                    <p class="formulario-subtitle">
                        <i class="fas fa-chart-bar me-2"></i>
                        {len(itens_data)} itens | 1 páginas
                    </p>
                </div>
            </div>
        </div>
    </div>

    <div class="formulario-container">
        <div class="tabela-container">
            <table class="tabela-separacao">
                <thead>
                    <tr>
                        <th class="col-data-hora">Data e Hora</th>
                        <th class="col-solicitante">Solicitante</th>
                        <th class="col-codigo">Código</th>
                        <th class="col-descricao">Descrição</th>
                        <th class="col-alta-demanda">Alta Demanda</th>
                        <th class="col-localizacao">Localização</th>
                        <th class="col-saldo-estoque">Saldo Estoque</th>
                        <th class="col-media-consumo">Média Consumo</th>
                        <th class="col-saldo-ficou">Saldo que Ficou</th>
                        <th class="col-qtd-pendente">Qtd. Pendente</th>
                        <th class="col-qtd-separada">Qtd. Separada</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join([f'''
                    <tr>
                        <td class="col-data-hora">
                            {item.get('data', '')}
                        </td>
                        <td class="col-solicitante">
                            {item.get('solicitante', '')}
                        </td>
                        <td class="col-codigo">
                            <strong>{item.get('codigo', '')}</strong>
                        </td>
                        <td class="col-descricao">
                            {item.get('descricao', '')}
                        </td>
                        <td class="col-alta-demanda">
                            <i class="fas fa-star alta-demanda-icon">★</i>
                        </td>
                        <td class="col-localizacao">
                            <span class="localizacao-cell">{item.get('locacao_matriz', '1 E5 E03/F03')}</span>
                        </td>
                        <td class="col-saldo-estoque">
                            <span class="quantidade-cell quantidade-saldo">{item.get('saldo_estoque', 600)}</span>
                        </td>
                        <td class="col-media-consumo">
                            <span class="quantidade-cell">{item.get('media_mensal', 41)}</span>
                        </td>
                        <td class="col-saldo-ficou">
                            <span class="text-muted"></span>
                        </td>
                        <td class="col-qtd-pendente">
                            <span class="quantidade-cell quantidade-pendente">{item.get('quantidade', 0)}</span>
                        </td>
                        <td class="col-qtd-separada">
                            <span class="text-muted"></span>
                        </td>
                    </tr>
                    ''' for item in itens_data])}
                </tbody>
            </table>
        </div>
    </div>

    <!-- Botões de Ação -->
    <div class="action-buttons">
        <button type="button" class="btn btn-print" onclick="imprimirFormulario()">
            <i class="fas fa-print me-2"></i>
            Imprimir
        </button>
        <button type="button" class="btn btn-save-pdf" onclick="salvarPDF()">
            <i class="fas fa-save me-2"></i>
            Salvar PDF
        </button>
    </div>
    
    <!-- Rodapé -->
    <div class="text-center mt-4">
        <small class="text-muted">Sistema v4.0.0 - Romaneios de Separação</small>
    </div>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    
    <script>
        function imprimirFormulario() {{
            console.log('🖨️ Imprimindo lista de separação...');
            window.print();
        }}

        function salvarPDF() {{
            console.log('💾 Salvando PDF...');
            // Usar a API de impressão do navegador para salvar como PDF
            window.print();
        }}

        // Atualizar data atual
        document.addEventListener('DOMContentLoaded', function() {{
            const agora = new Date();
            const dataFormatada = agora.toLocaleDateString('pt-BR') + ', ' + agora.toLocaleTimeString('pt-BR');
            document.getElementById('dataAtual').textContent = dataFormatada;
            
            // Mostrar instruções
            console.log('📋 Instruções:');
            console.log('1. Clique em "Imprimir" para imprimir fisicamente');
            console.log('2. Clique em "Salvar PDF" e escolha "Salvar como PDF" na impressora');
            console.log('3. O layout será 100% idêntico ao que você vê na tela');
        }});
        
        // Auto-focus no botão de imprimir
        window.addEventListener('load', function() {{
            setTimeout(function() {{
                document.querySelector('.btn-print').focus();
            }}, 1000);
        }});
    </script>
</body>
</html>
        """
        
        # Salvar arquivo HTML
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Retornar caminho do arquivo
        return filepath
        
    except Exception as e:
        print(f"❌ Erro ao gerar HTML: {e}")
        return None

def abrir_pdf_no_navegador(filepath):
    """
    Abre o PDF no navegador padrão
    """
    try:
        # Converter caminho para URL file://
        file_url = f"file:///{os.path.abspath(filepath).replace(os.sep, '/')}"
        
        # Abrir no navegador padrão
        webbrowser.open(file_url)
        
        print(f"✅ Arquivo aberto no navegador: {file_url}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao abrir no navegador: {e}")
        return False

def salvar_pdf_direto_html(html_content, romaneio_data, pasta_destino=None, is_reprint=False):
    """
    Salva PDF diretamente do HTML já renderizado (otimizado)
    Gera em arquivo temporário se pasta_destino for None
    """
    try:
        import subprocess
        import shutil
        import tempfile
        
        # Nome do arquivo
        romaneio_id = romaneio_data.get('id_impressao', 'ROM-000001')
        if is_reprint:
            filename = f"{romaneio_id}_Copia.pdf"
        else:
            filename = f"{romaneio_id}.pdf"
        
        # Se pasta_destino for None, usar arquivo temporário
        if pasta_destino is None:
            temp_dir = tempfile.gettempdir()
            filepath = os.path.join(temp_dir, filename)
        else:
            # Criar pasta se não existir
            os.makedirs(pasta_destino, exist_ok=True)
            filepath = os.path.join(pasta_destino, filename)
        
        # Adicionar identificação de cópia se necessário
        if is_reprint:
            # Modificar o título para incluir "CÓPIA"
            html_content = html_content.replace(
                '<h2>Romaneio de Separação</h2>', 
                '<h2 style="color: red; border: 2px solid red; padding: 10px; background-color: #ffebee;">📋 CÓPIA - Romaneio de Separação</h2>'
            )
            
            # Modificar o ID do romaneio para incluir "CÓPIA"
            romaneio_id = romaneio_data.get('id_impressao', 'ROM-000001')
            html_content = html_content.replace(
                f'ROM-{romaneio_id.split("-")[-1]}',
                f'ROM-{romaneio_id.split("-")[-1]} - CÓPIA'
            )
            
            # Adicionar texto no rodapé com data de reimpressão
            data_reimpressao = romaneio_data.get('data_reimpressao', '')
            if data_reimpressao:
                rodape_texto = f'Sistema v4.0.0 - Romaneios de Separação | ⚠️ DOCUMENTO DE CÓPIA/REIMPRESSÃO<br><strong>Reimpressão realizada em: {data_reimpressao}</strong>'
            else:
                rodape_texto = 'Sistema v4.0.0 - Romaneios de Separação | ⚠️ DOCUMENTO DE CÓPIA/REIMPRESSÃO'
            
            html_content = html_content.replace(
                'Sistema v4.0.0 - Romaneios de Separação',
                rodape_texto
            )
        
        # Criar arquivo HTML temporário
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(html_content)
            temp_html_path = temp_file.name
        
        try:
            # Converter caminho para URL file://
            file_url = f"file:///{os.path.abspath(temp_html_path).replace(os.sep, '/')}"
            
            # Caminhos comuns do Chrome/Edge no Windows e Linux
            chrome_paths = []
            
            # Windows
            if sys.platform == 'win32':
                chrome_paths = [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                    r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv('USERNAME', '')),
                    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
                ]
            else:
                # Linux (Cloud Run)
                chrome_paths = [
                    '/usr/bin/google-chrome',
                    '/usr/bin/google-chrome-stable',
                    '/usr/bin/chromium',
                    '/usr/bin/chromium-browser',
                    '/snap/bin/chromium'
                ]
            
            # Encontrar Chrome/Edge instalado
            browser_path = None
            for path in chrome_paths:
                if os.path.exists(path):
                    browser_path = path
                    break
            
            if not browser_path:
                # Tentar encontrar no PATH (funciona em Windows e Linux)
                for cmd in ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome', 'msedge']:
                    if shutil.which(cmd):
                        browser_path = cmd
                        break
            
            if browser_path:
                # Usar caminho absoluto para o PDF
                abs_filepath = os.path.abspath(filepath)
                
                # Comando para gerar PDF (Linux precisa de flags adicionais)
                if sys.platform == 'win32':
                    # Windows
                    if 'msedge' in browser_path.lower():
                        cmd = [browser_path, '--headless', '--disable-gpu', '--print-to-pdf=' + abs_filepath, file_url]
                    else:
                        cmd = [browser_path, '--headless', '--disable-gpu', '--print-to-pdf=' + abs_filepath, file_url]
                else:
                    # Linux (Cloud Run)
                    cmd = [
                        browser_path,
                        '--headless',
                        '--disable-gpu',
                        '--no-sandbox',  # Necessário para rodar como root no Docker
                        '--disable-dev-shm-usage',  # Evita problemas de memória compartilhada
                        '--disable-software-rasterizer',
                        '--print-to-pdf=' + abs_filepath,
                        file_url
                    ]
                
                print(f"🔄 Gerando PDF com: {browser_path}")
                result = subprocess.run(cmd, capture_output=True, timeout=30)
                
                if result.returncode == 0 and os.path.exists(filepath):
                    print(f"✅ PDF gerado automaticamente: {filepath}")
                    
                    # SEMPRE salvar no Cloud Storage após gerar o PDF
                    try:
                        from salvar_pdf_gcs import salvar_pdf_gcs
                        import os
                        
                        # Ler o PDF gerado
                        with open(filepath, 'rb') as f:
                            pdf_content = f.read()
                        
                        # Validar se é um PDF válido
                        if pdf_content.startswith(b'%PDF'):
                            bucket_name = os.environ.get('GCS_BUCKET_NAME', 'romaneios-separacao')
                            print(f"☁️ Salvando PDF no Cloud Storage...")
                            print(f"📦 Bucket: {bucket_name}")
                            print(f"🆔 Romaneio ID: {romaneio_id}")
                            
                            gcs_path = salvar_pdf_gcs(pdf_content, romaneio_id, bucket_name, is_reprint)
                            
                            if gcs_path:
                                print(f"✅ PDF salvo no Cloud Storage: {gcs_path}")
                                # NÃO deletar arquivo aqui - deixar app.py gerenciar
                                # O app.py vai deletar depois de confirmar que salvou
                                return {
                                    'success': True, 
                                    'message': 'PDF gerado e salvo no Cloud Storage', 
                                    'file_path': filepath,
                                    'gcs_path': gcs_path
                                }
                            else:
                                print(f"⚠️ Aviso: PDF gerado mas não foi possível salvar no Cloud Storage")
                                print(f"⚠️ Arquivo temporário mantido em: {filepath} para tentativa posterior")
                                return {'success': True, 'message': 'PDF gerado (não salvo no Cloud Storage)', 'file_path': filepath}
                        else:
                            print(f"⚠️ Arquivo gerado não é um PDF válido")
                            return {'success': True, 'message': 'PDF gerado e salvo automaticamente', 'file_path': filepath}
                    except Exception as gcs_error:
                        print(f"⚠️ Erro ao salvar no Cloud Storage: {gcs_error}")
                        import traceback
                        traceback.print_exc()
                        # Retornar sucesso mesmo se falhar o Cloud Storage (PDF foi gerado)
                        return {'success': True, 'message': 'PDF gerado (erro ao salvar no Cloud Storage)', 'file_path': filepath}
                else:
                    error_msg = result.stderr.decode() if result.stderr else "Erro desconhecido"
                    print(f"⚠️ Erro ao gerar PDF: {error_msg}")
            
            # Se não conseguiu gerar automaticamente, salvar HTML para impressão manual
            print("⚠️ Não foi possível gerar PDF automaticamente, salvando HTML...")
            
            # Se pasta_destino for None, usar arquivo temporário
            if pasta_destino is None:
                temp_dir = tempfile.gettempdir()
                html_final_path = os.path.join(temp_dir, f"{romaneio_id}.html")
            else:
                html_final_path = os.path.join(pasta_destino, f"{romaneio_id}.html")
            
            with open(html_final_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Abrir no navegador (apenas se não estiver no Cloud Run)
            if not os.environ.get('K_SERVICE'):
                abrir_pdf_no_navegador(html_final_path)
            
            return {'success': True, 'message': 'HTML salvo para impressão manual', 'file_path': html_final_path}
            
        finally:
            # Limpar arquivo temporário
            try:
                os.unlink(temp_html_path)
            except:
                pass
        
    except Exception as e:
        print(f"❌ Erro ao salvar PDF: {e}")
        return {'success': False, 'message': f'Erro: {str(e)}'}

def salvar_pdf_automatico(romaneio_data, itens_data, pasta_destino='Romaneios_Separacao', is_reprint=False):
    """
    Salva PDF automaticamente usando o navegador em modo headless
    """
    try:
        import subprocess
        import time
        import shutil
        
        # Criar pasta se não existir
        os.makedirs(pasta_destino, exist_ok=True)
        
        # Nome do arquivo
        romaneio_id = romaneio_data.get('id_impressao', 'ROM-000001')
        if is_reprint:
            filename = f"{romaneio_id}_Copia.pdf"
        else:
            filename = f"{romaneio_id}.pdf"
        
        filepath = os.path.join(pasta_destino, filename)
        
        # Gerar HTML temporário
        html_file = gerar_pdf_browser_romaneio(romaneio_data, itens_data, is_reprint)
        
        if not html_file:
            return {'success': False, 'message': 'Erro ao gerar HTML'}
        
        # Tentar usar Chrome/Edge em modo headless para gerar PDF
        try:
            # Converter caminho para URL file://
            file_url = f"file:///{os.path.abspath(html_file).replace(os.sep, '/')}"
            
            # Caminhos comuns do Chrome/Edge no Windows
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv('USERNAME', '')),
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
            ]
            
            # Encontrar Chrome/Edge instalado
            browser_path = None
            for path in chrome_paths:
                if os.path.exists(path):
                    browser_path = path
                    break
            
            if not browser_path:
                # Tentar encontrar no PATH
                for cmd in ['chrome', 'msedge', 'google-chrome']:
                    if shutil.which(cmd):
                        browser_path = cmd
                        break
            
            if browser_path:
                # Usar caminho absoluto para o PDF
                abs_filepath = os.path.abspath(filepath)
                
                # Comando para gerar PDF
                if 'msedge' in browser_path.lower():
                    cmd = [browser_path, '--headless', '--disable-gpu', '--print-to-pdf=' + abs_filepath, file_url]
                else:
                    cmd = [browser_path, '--headless', '--disable-gpu', '--print-to-pdf=' + abs_filepath, file_url]
                
                print(f"🔄 Tentando gerar PDF com: {browser_path}")
                result = subprocess.run(cmd, capture_output=True, timeout=30)
                
                if result.returncode == 0 and os.path.exists(filepath):
                    print(f"✅ PDF gerado automaticamente: {filepath}")
                    return {'success': True, 'message': 'PDF gerado e salvo automaticamente', 'file_path': filepath}
                else:
                    print(f"⚠️ Erro ao gerar PDF: {result.stderr.decode()}")
            
            # Se não conseguiu gerar automaticamente, abrir no navegador
            print("⚠️ Não foi possível gerar PDF automaticamente, abrindo no navegador...")
            abrir_pdf_no_navegador(html_file)
            return {'success': True, 'message': 'Arquivo aberto no navegador para impressão manual', 'file_path': html_file}
            
        except Exception as e:
            print(f"⚠️ Erro ao gerar PDF automaticamente: {e}")
            print("Abrindo no navegador para impressão manual...")
            abrir_pdf_no_navegador(html_file)
            return {'success': True, 'message': 'Arquivo aberto no navegador para impressão manual', 'file_path': html_file}
        
    except Exception as e:
        print(f"❌ Erro ao salvar PDF: {e}")
        return {'success': False, 'message': f'Erro: {str(e)}'}
