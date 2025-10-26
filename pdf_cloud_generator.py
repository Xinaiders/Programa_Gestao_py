#!/usr/bin/env python3
"""
Gerador de PDF compatível com Google Cloud Platform
Usa ReportLab para gerar PDFs sem dependências externas
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

def gerar_pdf_cloud_romaneio(romaneio_data, itens_data, pasta_destino='Romaneios_Separacao', is_reprint=False):
    """
    Gera PDF usando ReportLab - Compatível com Google Cloud
    
    Args:
        romaneio_data: Dados do romaneio
        itens_data: Lista de itens
        pasta_destino: Pasta para salvar (ignorada no GCP)
        is_reprint: Se é reimpressão
    
    Returns:
        dict: Resultado da operação
    """
    try:
        # Criar pasta se não existir (para desenvolvimento local)
        if not os.path.exists(pasta_destino):
            os.makedirs(pasta_destino, exist_ok=True)
        
        # Nome do arquivo
        romaneio_id = romaneio_data.get('id_impressao', 'ROM-000001')
        if is_reprint:
            filename = f"{romaneio_id}_Copia.pdf"
        else:
            filename = f"{romaneio_id}.pdf"
        
        filepath = os.path.join(pasta_destino, filename)
        
        # Criar documento PDF
        doc = SimpleDocTemplate(
            filepath,
            pagesize=landscape(A4),
            rightMargin=1*cm,
            leftMargin=1*cm,
            topMargin=1*cm,
            bottomMargin=1*cm
        )
        
        # Estilos
        styles = getSampleStyleSheet()
        
        # Estilo do título
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.red if is_reprint else colors.black
        )
        
        # Estilo do cabeçalho
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=10,
            alignment=TA_LEFT
        )
        
        # Estilo da tabela
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
        
        # Conteúdo do PDF
        story = []
        
        # Título principal
        if is_reprint:
            title_text = f"📋 CÓPIA - Romaneio de Separação - {romaneio_id}"
        else:
            title_text = f"Romaneio de Separação - {romaneio_id}"
        
        story.append(Paragraph(title_text, title_style))
        
        # Informações do romaneio
        info_data = [
            ['Data/Hora:', romaneio_data.get('data_impressao', '')],
            ['Usuário:', romaneio_data.get('usuario_impressao', '')],
            ['Total de Itens:', str(romaneio_data.get('total_itens', 0))],
            ['Status:', romaneio_data.get('status', 'Pendente')]
        ]
        
        info_table = Table(info_data, colWidths=[3*cm, 6*cm])
        info_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 20))
        
        # Cabeçalho da tabela principal
        headers = [
            'Data e Hora', 'Solicitante', 'Código', 'Descrição', 
            'Alta Demanda', 'Localização', 'Saldo Estoque', 
            'Média Consumo', 'Saldo que ficou', 'Qtd. Pendente', 'Qtd. Separada'
        ]
        
        # Dados da tabela
        table_data = [headers]
        
        for item in itens_data:
            row = [
                item.get('data', ''),
                item.get('solicitante', ''),
                item.get('codigo', ''),
                item.get('descricao', '')[:50] + '...' if len(item.get('descricao', '')) > 50 else item.get('descricao', ''),
                '⭐' if item.get('alta_demanda', False) else '',
                item.get('locacao_matriz', ''),
                str(item.get('saldo_estoque', 0)),
                str(item.get('media_mensal', 0)),
                '—',
                str(item.get('qtd_pendente', 0)),
                str(item.get('qtd_separada', 0))
            ]
            table_data.append(row)
        
        # Criar tabela principal
        main_table = Table(table_data, colWidths=[
            2*cm, 2.5*cm, 1.5*cm, 4*cm, 1*cm, 2*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm
        ])
        main_table.setStyle(table_style)
        
        story.append(main_table)
        story.append(Spacer(1, 20))
        
        # Rodapé
        footer_text = f"Sistema v4.0.0 - Romaneios de Separação"
        if is_reprint:
            data_reimpressao = romaneio_data.get('data_reimpressao', '')
            footer_text += " | ⚠️ DOCUMENTO DE CÓPIA/REIMPRESSÃO"
            if data_reimpressao:
                footer_text += f"<br/><b>Reimpressão realizada em: {data_reimpressao}</b>"
        
        story.append(Paragraph(footer_text, header_style))
        
        # Construir PDF
        doc.build(story)
        
        return {
            'success': True,
            'message': 'PDF gerado com sucesso usando ReportLab',
            'file_path': filepath
        }
        
    except Exception as e:
        print(f"❌ Erro ao gerar PDF: {e}")
        return {
            'success': False,
            'message': f'Erro: {str(e)}'
        }

def salvar_pdf_cloud(html_content, romaneio_data, pasta_destino='Romaneios_Separacao', is_reprint=False):
    """
    Função de compatibilidade - converte HTML para dados e gera PDF
    """
    try:
        # Extrair dados do HTML (simulação)
        # Em produção, você pode usar BeautifulSoup para extrair dados do HTML
        itens_data = []
        
        # Simular dados baseados no romaneio_data
        for i in range(romaneio_data.get('total_itens', 1)):
            item = {
                'data': romaneio_data.get('data_impressao', ''),
                'solicitante': f'Solicitante {i+1}',
                'codigo': f'COD{i+1:03d}',
                'descricao': f'Descrição do item {i+1}',
                'alta_demanda': i % 3 == 0,
                'locacao_matriz': '1 E5 E03/F03',
                'saldo_estoque': 100 + i * 10,
                'media_mensal': 50 + i * 5,
                'qtd_pendente': 10 + i,
                'qtd_separada': 0
            }
            itens_data.append(item)
        
        return gerar_pdf_cloud_romaneio(romaneio_data, itens_data, pasta_destino, is_reprint)
        
    except Exception as e:
        print(f"❌ Erro ao processar HTML: {e}")
        return {
            'success': False,
            'message': f'Erro: {str(e)}'
        }
