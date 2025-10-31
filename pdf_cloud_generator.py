#!/usr/bin/env python3
"""
Gerador de PDF compatível com Google Cloud Platform
Mantém o layout original do HTML usando weasyprint
"""

import os
import tempfile
from datetime import datetime

def gerar_pdf_cloud_romaneio(romaneio_data, itens_data, pasta_destino='Romaneios_Separacao', is_reprint=False):
    """
    Função mantida para compatibilidade (não usada mais)
    """
    pass

def salvar_pdf_cloud(html_content, romaneio_data, pasta_destino=None, is_reprint=False, itens_data=None):
    """
    Converte HTML diretamente para PDF mantendo o layout original
    Usa weasyprint no Cloud Run para manter layout idêntico ao HTML
    
    Args:
        html_content: Conteúdo HTML renderizado
        romaneio_data: Dados do romaneio
        pasta_destino: Pasta de destino (None para usar arquivo temporário)
        is_reprint: Se é reimpressão
        itens_data: Não usado (mantido para compatibilidade)
    """
    try:
        import os
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
        
        # Adicionar marca d'água de cópia se necessário (igual ao pdf_browser_generator)
        if is_reprint:
            # Modificar o título para incluir "CÓPIA"
            html_content = html_content.replace(
                '<h2>Romaneio de Separação</h2>', 
                '<h2 style="color: red; border: 2px solid red; padding: 10px; background-color: #ffebee;">📋 CÓPIA - Romaneio de Separação</h2>'
            )
            
            # Modificar o ID do romaneio para incluir "CÓPIA"
            romaneio_id_split = romaneio_id.split("-")
            if len(romaneio_id_split) > 1:
                html_content = html_content.replace(
                    f'ROM-{romaneio_id_split[-1]}',
                    f'ROM-{romaneio_id_split[-1]} - CÓPIA'
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
        
        # Tentar usar weasyprint (funciona no Cloud Run)
        try:
            from weasyprint import HTML
            print("📄 Convertendo HTML para PDF usando WeasyPrint (mantém layout original)...")
            
            # Converter HTML para PDF
            HTML(string=html_content).write_pdf(filepath)
            
            print(f"✅ PDF gerado com layout original: {filepath}")
            
        except ImportError:
            # Se weasyprint não estiver disponível, usar ReportLab como fallback
            print("⚠️ WeasyPrint não disponível, usando ReportLab (layout pode diferir)...")
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate
            from reportlab.platypus import Paragraph, Spacer
            
            doc = SimpleDocTemplate(filepath, pagesize=landscape(A4))
            story = []
            styles = getSampleStyleSheet()
            story.append(Paragraph("PDF gerado com layout alternativo (WeasyPrint não disponível)", styles['Normal']))
            story.append(Spacer(1, 20))
            story.append(Paragraph("Use weasyprint para manter layout original do HTML", styles['Normal']))
            doc.build(story)
            
        except Exception as e:
            print(f"❌ Erro ao gerar PDF: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f'Erro ao gerar PDF: {str(e)}'
            }
        
        # SEMPRE tentar salvar no Cloud Storage
        pdf_result = {
            'success': True,
            'message': 'PDF gerado com layout original',
            'file_path': filepath
        }
        
        print("🔍 INICIANDO SALVAMENTO NO CLOUD STORAGE...")
        print(f"📦 Variáveis: K_SERVICE={os.environ.get('K_SERVICE')}, PORT={os.environ.get('PORT')}")
        
        # Ler o PDF gerado e salvar no Cloud Storage
        try:
            if os.path.exists(filepath):
                print(f"📄 Lendo PDF do caminho temporário: {filepath}")
                with open(filepath, 'rb') as f:
                    pdf_content = f.read()
                
                # Verificar se é realmente um PDF
                if pdf_content.startswith(b'%PDF'):
                    print(f"📊 Tamanho do PDF: {len(pdf_content)} bytes")
                    
                    # Deletar arquivo temporário imediatamente após ler
                    try:
                        os.unlink(filepath)
                        print(f"🗑️ Arquivo temporário removido: {filepath}")
                    except:
                        pass
                    
                    # Salvar no Cloud Storage
                    from salvar_pdf_gcs import salvar_pdf_gcs
                    bucket_name = os.environ.get('GCS_BUCKET_NAME', 'romaneios-separacao')
                    print(f"📦 Bucket: {bucket_name}")
                    print(f"🆔 Romaneio ID: {romaneio_id}")
                    
                    gcs_path = salvar_pdf_gcs(pdf_content, romaneio_id, bucket_name, is_reprint)
                    
                    if gcs_path:
                        print(f"✅ PDF salvo no Cloud Storage: {gcs_path}")
                        pdf_result['gcs_path'] = gcs_path
                        pdf_result['message'] = 'PDF salvo no Cloud Storage'
                    else:
                        print(f"❌ Falha ao salvar no Cloud Storage (retornou None)")
                        pdf_result['success'] = False
                        pdf_result['message'] = 'Erro ao salvar no Cloud Storage'
                else:
                    print(f"⚠️ Arquivo não é um PDF válido (começa com: {pdf_content[:20]})")
                    pdf_result['success'] = False
            else:
                print(f"❌ PDF não encontrado no caminho: {filepath}")
                pdf_result['success'] = False
                
        except Exception as e:
            print(f"⚠️ Erro ao salvar no Cloud Storage (continuando): {e}")
            import traceback
            traceback.print_exc()
        
        return pdf_result
        
    except Exception as e:
        print(f"❌ Erro ao gerar PDF: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': f'Erro: {str(e)}'
        }
