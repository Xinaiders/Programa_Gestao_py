#!/usr/bin/env python3
"""
Módulo para geração de PDF e integração com Google Drive
"""

import os
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import tempfile

def gerar_pdf_romaneio(romaneio_data, itens_data, is_reprint=False):
    """
    Gera PDF do romaneio de separação - LAYOUT IDÊNTICO ao formulario_impressao.html
    
    Args:
        romaneio_data: Dados do romaneio (id, data, usuario, etc.)
        itens_data: Lista de itens do romaneio
        is_reprint: Se é uma reimpressão/cópia
    
    Returns:
        bytes: Conteúdo do PDF em bytes
    """
    buffer = io.BytesIO()
    
    # Configurar documento em paisagem A4 (igual ao @media print do HTML)
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), 
                          rightMargin=0.5*cm, leftMargin=0.5*cm,
                          topMargin=0.5*cm, bottomMargin=0.5*cm)
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Conteúdo do PDF
    story = []
    
    # Cabeçalho EXATAMENTE igual ao formulario_impressao.html
    # Título principal no canto esquerdo (font-size: 16px no print)
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Normal'],
        fontSize=16,  # Igual ao @media print .formulario-title
        alignment=TA_LEFT,
        spaceAfter=5,
        fontName='Helvetica-Bold'
    )
    
    story.append(Paragraph("LINE FLEX - Gestão de Estoque", title_style))
    
    # Subtítulo abaixo do título (font-size: 12px no print)
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,  # Igual ao @media print .formulario-subtitle
        alignment=TA_LEFT,
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )
    
    story.append(Paragraph("Romaneio de Separação", subtitle_style))
    
    # Adicionar marca d'água para cópia (sutil)
    if is_reprint:
        watermark_style = ParagraphStyle(
            'Watermark',
            parent=styles['Normal'],
            fontSize=18,
            textColor=colors.lightgrey,
            alignment=TA_CENTER,
            spaceAfter=5
        )
        story.append(Paragraph("CÓPIA", watermark_style))
    
    # Informações do lado direito (igual ao formulario_impressao.html)
    info_style = ParagraphStyle(
        'Info',
        parent=styles['Normal'],
        fontSize=12,  # Igual ao @media print .formulario-subtitle
        alignment=TA_RIGHT,
        spaceAfter=5,
        fontName='Helvetica-Bold'
    )
    
    # ROM-ID (igual ao HTML)
    rom_id = romaneio_data.get('id_impressao', 'N/A')
    if '-' in rom_id:
        rom_id = f"ROM-{rom_id.split('-')[-1]}"
    else:
        rom_id = f"ROM-{rom_id}"
    
    story.append(Paragraph(rom_id, info_style))
    story.append(Paragraph(f"{romaneio_data.get('data_impressao', 'N/A')}", info_style))
    story.append(Paragraph(f"{romaneio_data.get('total_itens', 0)} itens | 1 páginas", info_style))
    
    # Linha separadora (igual ao HTML)
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph("_" * 100, title_style))
    story.append(Spacer(1, 0.3*cm))
    
    # Tabela EXATAMENTE igual ao formulario_impressao.html
    if itens_data:
        # Cabeçalho da tabela (igual ao HTML)
        table_data = [["Data e Hora", "Solicitante", "Código", "Descrição", "Alta Demanda", 
                      "Localização", "Saldo Estoque", "Média Consumo", "Saldo que Ficou", "Qtd. Pendente", "Qtd. Separada"]]
        
        # Dados dos itens
        for item in itens_data:
            # Formatar data e hora
            data_hora = item.get('data', '')
            
            # Ícone de alta demanda (estrela) - igual ao HTML
            alta_demanda = "★" if item.get('quantidade', 0) > 50 else ""
            
            row = [
                data_hora,
                item.get('solicitante', ''),
                item.get('codigo', ''),
                item.get('descricao', ''),
                alta_demanda,
                item.get('locacao_matriz', '1 E5 E03/F03'),  # Valor padrão igual ao HTML
                str(item.get('saldo_estoque', 600)),  # Valor padrão igual ao HTML
                str(item.get('media_mensal', 41)),    # Valor padrão igual ao HTML
                "_____",  # Saldo que ficou (igual ao HTML)
                str(item.get('qtd_pendente', 0)),
                "_____"   # Qtd separada (igual ao HTML)
            ]
            table_data.append(row)
        
        # Criar tabela com larguras EXATAS do HTML (@media print)
        # Larguras em cm baseadas no HTML: col-data-hora: 80px, col-solicitante: 70px, etc.
        items_table = Table(table_data, colWidths=[2.2*cm, 1.9*cm, 1.4*cm, 4.2*cm, 1.7*cm, 
                                                  2.2*cm, 1.9*cm, 1.9*cm, 2.2*cm, 1.9*cm, 2.2*cm])
        
        items_table.setStyle(TableStyle([
            # Cabeçalho (igual ao @media print do HTML)
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # #f0f0f0
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),  # font-size: 9px no print
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),  # padding: 4px 2px no print
            ('TOPPADDING', (0, 0), (-1, 0), 4),
            ('LEFTPADDING', (0, 0), (-1, 0), 2),
            ('RIGHTPADDING', (0, 0), (-1, 0), 2),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),  # border: 1px solid #000
            
            # Dados (igual ao @media print do HTML)
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),  # font-size: 9px no print
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 3),  # padding: 3px 2px no print
            ('TOPPADDING', (0, 1), (-1, -1), 3),
            ('LEFTPADDING', (0, 1), (-1, -1), 2),
            ('RIGHTPADDING', (0, 1), (-1, -1), 2),
            
            # Destaques específicos (igual ao HTML)
            ('FONTNAME', (2, 1), (2, -1), 'Helvetica-Bold'),  # Código em negrito
            ('BACKGROUND', (2, 1), (2, -1), colors.lightblue),  # Código com fundo azul
            ('FONTNAME', (5, 1), (5, -1), 'Helvetica-Bold'),  # Localização em negrito
            ('BACKGROUND', (5, 1), (5, -1), colors.yellow),   # Localização com fundo amarelo
            ('TEXTCOLOR', (6, 1), (6, -1), colors.orange),    # Saldo Estoque em laranja
            ('TEXTCOLOR', (9, 1), (9, -1), colors.red),       # Qtd Pendente em vermelho
            ('BACKGROUND', (8, 1), (8, -1), colors.lightgrey),  # Saldo que ficou com fundo cinza
            ('BACKGROUND', (10, 1), (10, -1), colors.lightgrey),  # Qtd separada com fundo cinza
        ]))
        
        story.append(items_table)
    
    # Rodapé (igual ao formulario_impressao.html)
    story.append(Spacer(1, 1*cm))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.grey
    )
    story.append(Paragraph("Sistema v4.0.0 - Romaneios de Separação", footer_style))
    
    # Construir PDF
    doc.build(story)
    
    # Retornar bytes
    buffer.seek(0)
    return buffer.getvalue()

def conectar_google_drive():
    """
    Conecta com Google Drive API
    
    Returns:
        service: Serviço do Google Drive ou None se erro
    """
    try:
        # Usar as mesmas credenciais do Google Sheets
        from app import get_google_sheets_connection
        
        # Obter credenciais do gspread
        sheet = get_google_sheets_connection()
        if not sheet:
            print("❌ Não foi possível conectar com Google Sheets")
            return None
        
        # Obter credenciais do cliente
        credentials = sheet.auth
        
        # Criar serviço do Google Drive
        service = build('drive', 'v3', credentials=credentials)
        
        return service
        
    except Exception as e:
        print(f"❌ Erro ao conectar com Google Drive: {e}")
        return None

def criar_pasta_romaneios(service, pasta_pai_id=None):
    """
    Cria pasta para romaneios no Google Drive se não existir
    
    Args:
        service: Serviço do Google Drive
        pasta_pai_id: ID da pasta pai (opcional)
    
    Returns:
        str: ID da pasta ou None se erro
    """
    try:
        # Nome da pasta
        folder_name = "Romaneios de Separação"
        
        # Construir query de busca
        if pasta_pai_id:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false and '{pasta_pai_id}' in parents"
        else:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        # Verificar se pasta já existe
        results = service.files().list(q=query).execute()
        
        if results['files']:
            # Pasta já existe
            folder_id = results['files'][0]['id']
            print(f"✅ Pasta '{folder_name}' já existe: {folder_id}")
            return folder_id
        
        # Criar pasta
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        # Adicionar pasta pai se especificada
        if pasta_pai_id:
            folder_metadata['parents'] = [pasta_pai_id]
        
        folder = service.files().create(body=folder_metadata, fields='id').execute()
        folder_id = folder.get('id')
        
        print(f"✅ Pasta '{folder_name}' criada: {folder_id}")
        return folder_id
        
    except Exception as e:
        print(f"❌ Erro ao criar pasta no Google Drive: {e}")
        return None

def salvar_pdf_google_drive(service, folder_id, romaneio_id, pdf_content):
    """
    Salva PDF no Google Drive
    
    Args:
        service: Serviço do Google Drive
        folder_id: ID da pasta
        romaneio_id: ID do romaneio
        pdf_content: Conteúdo do PDF em bytes
    
    Returns:
        str: ID do arquivo salvo ou None se erro
    """
    try:
        # Nome do arquivo
        filename = f"{romaneio_id}.pdf"
        
        # Criar arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(pdf_content)
            temp_file_path = temp_file.name
        
        try:
            # Metadados do arquivo
            file_metadata = {
                'name': filename,
                'parents': [folder_id]
            }
            
            # Upload do arquivo
            media = MediaIoBaseUpload(io.BytesIO(pdf_content), mimetype='application/pdf')
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            print(f"✅ PDF salvo no Google Drive: {filename} (ID: {file_id})")
            
            return file_id
            
        finally:
            # Limpar arquivo temporário
            os.unlink(temp_file_path)
        
    except Exception as e:
        print(f"❌ Erro ao salvar PDF no Google Drive: {e}")
        return None

def buscar_pasta_por_nome(service, nome_pasta, pasta_pai_id=None):
    """
    Busca pasta no Google Drive por nome
    
    Args:
        service: Serviço do Google Drive
        nome_pasta: Nome da pasta a buscar
        pasta_pai_id: ID da pasta pai (opcional)
    
    Returns:
        str: ID da pasta ou None se não encontrada
    """
    try:
        # Construir query de busca
        if pasta_pai_id:
            query = f"name='{nome_pasta}' and mimeType='application/vnd.google-apps.folder' and trashed=false and '{pasta_pai_id}' in parents"
        else:
            query = f"name='{nome_pasta}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        results = service.files().list(q=query).execute()
        
        if results['files']:
            folder_id = results['files'][0]['id']
            print(f"✅ Pasta '{nome_pasta}' encontrada: {folder_id}")
            return folder_id
        
        print(f"❌ Pasta '{nome_pasta}' não encontrada")
        return None
        
    except Exception as e:
        print(f"❌ Erro ao buscar pasta: {e}")
        return None

def salvar_pdf_local(pasta_destino, romaneio_id, pdf_content, is_reprint=False):
    """
    Salva PDF localmente no sistema de arquivos
    
    Args:
        pasta_destino: Caminho da pasta de destino
        romaneio_id: ID do romaneio
        pdf_content: Conteúdo do PDF em bytes
        is_reprint: Se é uma reimpressão/cópia
    
    Returns:
        str: Caminho do arquivo salvo ou None se erro
    """
    try:
        # Criar pasta se não existir
        os.makedirs(pasta_destino, exist_ok=True)
        
        # Nome do arquivo com sufixo para cópia
        if is_reprint:
            # Verificar se já existe cópia para determinar número
            contador = 1
            while True:
                if contador == 1:
                    filename = f"{romaneio_id}_Copia.pdf"
                else:
                    filename = f"{romaneio_id}_Copia_{contador}.pdf"
                
                filepath = os.path.join(pasta_destino, filename)
                if not os.path.exists(filepath):
                    break
                contador += 1
        else:
            filename = f"{romaneio_id}.pdf"
            filepath = os.path.join(pasta_destino, filename)
        
        # Salvar arquivo
        with open(filepath, 'wb') as f:
            f.write(pdf_content)
        
        print(f"✅ PDF salvo localmente: {filepath}")
        return filepath
        
    except Exception as e:
        print(f"❌ Erro ao salvar PDF localmente: {e}")
        return None

def gerar_e_salvar_romaneio_pdf(romaneio_data, itens_data, pasta_destino=None, is_reprint=False):
    """
    Função principal: gera PDF e salva (local ou Google Drive)
    
    Args:
        romaneio_data: Dados do romaneio
        itens_data: Lista de itens
        pasta_destino: Nome da pasta de destino (opcional)
        is_reprint: Se é uma reimpressão/cópia
    
    Returns:
        dict: Resultado da operação
    """
    try:
        print(f"🔄 Gerando PDF para romaneio: {romaneio_data.get('id_impressao', 'N/A')}")
        
        # Gerar PDF
        pdf_content = gerar_pdf_romaneio(romaneio_data, itens_data, is_reprint)
        print(f"✅ PDF gerado: {len(pdf_content)} bytes")
        
        # Determinar tipo de armazenamento
        try:
            from config_pdf import obter_tipo_armazenamento, obter_configuracao_pasta
            tipo_armazenamento = obter_tipo_armazenamento()
            if not pasta_destino:
                pasta_destino = obter_configuracao_pasta()
        except ImportError:
            tipo_armazenamento = 'local'
            if not pasta_destino:
                pasta_destino = 'Romaneios_Separacao'
        
        if tipo_armazenamento == 'local':
            # Salvar localmente
            filepath = salvar_pdf_local(pasta_destino, romaneio_data.get('id_impressao'), pdf_content, is_reprint)
            if not filepath:
                return {'success': False, 'message': 'Erro ao salvar PDF localmente'}
            
            return {
                'success': True,
                'message': 'PDF gerado e salvo localmente',
                'file_path': filepath,
                'tipo': 'local'
            }
        
        else:
            # Salvar no Google Drive
            service = conectar_google_drive()
            if not service:
                return {'success': False, 'message': 'Erro ao conectar com Google Drive'}
            
            # Determinar pasta de destino
            folder_id = None
            
            if pasta_destino:
                # Buscar pasta específica
                folder_id = buscar_pasta_por_nome(service, pasta_destino)
                if not folder_id:
                    return {'success': False, 'message': f'Pasta "{pasta_destino}" não encontrada no Google Drive'}
            else:
                # Usar pasta padrão
                folder_id = criar_pasta_romaneios(service)
                if not folder_id:
                    return {'success': False, 'message': 'Erro ao criar/obter pasta no Google Drive'}
            
            # Salvar PDF
            file_id = salvar_pdf_google_drive(service, folder_id, romaneio_data.get('id_impressao'), pdf_content)
            if not file_id:
                return {'success': False, 'message': 'Erro ao salvar PDF no Google Drive'}
            
            return {
                'success': True,
                'message': 'PDF gerado e salvo no Google Drive',
                'file_id': file_id,
                'folder_id': folder_id,
                'tipo': 'google_drive'
            }
        
    except Exception as e:
        print(f"❌ Erro ao gerar e salvar PDF: {e}")
        return {'success': False, 'message': f'Erro: {str(e)}'}

def buscar_pdf_romaneio_local(pasta_destino, romaneio_id):
    """
    Busca PDF do romaneio no armazenamento local
    
    Args:
        pasta_destino: Caminho da pasta
        romaneio_id: ID do romaneio
    
    Returns:
        bytes: Conteúdo do PDF ou None se não encontrado
    """
    try:
        # Caminho do arquivo
        filename = f"{romaneio_id}.pdf"
        filepath = os.path.join(pasta_destino, filename)
        
        # Verificar se arquivo existe
        if not os.path.exists(filepath):
            print(f"❌ PDF não encontrado: {filepath}")
            return None
        
        # Ler arquivo
        with open(filepath, 'rb') as f:
            file_content = f.read()
        
        print(f"✅ PDF encontrado localmente: {filepath}")
        return file_content
        
    except Exception as e:
        print(f"❌ Erro ao buscar PDF local: {e}")
        return None

def buscar_pdf_romaneio(romaneio_id):
    """
    Busca PDF do romaneio (local ou Google Drive)
    
    Args:
        romaneio_id: ID do romaneio
    
    Returns:
        bytes: Conteúdo do PDF ou None se não encontrado
    """
    try:
        # Determinar tipo de armazenamento
        try:
            from config_pdf import obter_tipo_armazenamento, obter_configuracao_pasta
            tipo_armazenamento = obter_tipo_armazenamento()
            pasta_destino = obter_configuracao_pasta()
        except ImportError:
            tipo_armazenamento = 'local'
            pasta_destino = 'Romaneios_Separacao'
        
        if tipo_armazenamento == 'local':
            # Buscar localmente
            return buscar_pdf_romaneio_local(pasta_destino, romaneio_id)
        
        else:
            # Buscar no Google Drive
            service = conectar_google_drive()
            if not service:
                return None
            
            # Buscar arquivo
            filename = f"{romaneio_id}.pdf"
            query = f"name='{filename}' and mimeType='application/pdf' and trashed=false"
            results = service.files().list(q=query).execute()
            
            if not results['files']:
                print(f"❌ PDF não encontrado: {filename}")
                return None
            
            # Obter ID do arquivo
            file_id = results['files'][0]['id']
            
            # Baixar arquivo
            request = service.files().get_media(fileId=file_id)
            file_content = request.execute()
            
            print(f"✅ PDF encontrado no Google Drive: {filename}")
            return file_content
        
    except Exception as e:
        print(f"❌ Erro ao buscar PDF: {e}")
        return None
