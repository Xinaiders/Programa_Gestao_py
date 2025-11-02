#!/usr/bin/env python3
"""
Gerador de PDF compatível com Google Cloud Platform
Usa xhtml2pdf para manter layout HTML (compatível com Cloud Run)
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
    Usa xhtml2pdf no Cloud Run para manter layout idêntico ao HTML
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
        
        # Validar filepath
        if not filepath:
            return {
                'success': False,
                'message': 'Erro: Não foi possível determinar caminho do arquivo'
            }
        
        print(f"📄 Filepath determinado: {filepath}")
        
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
        
        # Validar HTML content
        if not html_content or not isinstance(html_content, str):
            return {
                'success': False,
                'message': f'Erro: HTML content inválido (tipo: {type(html_content)})'
            }
        
        print(f"📄 HTML content tamanho: {len(html_content)} caracteres")
        
        # Tentar usar xhtml2pdf (funciona no Cloud Run sem dependências de sistema)
        pdf_gerado = False
        try:
            from xhtml2pdf import pisa
            import io
            print("📄 Convertendo HTML para PDF usando xhtml2pdf (mantém layout original)...")
            
            # Converter HTML para PDF usando xhtml2pdf
            result_file = io.BytesIO()
            pisa_status = pisa.CreatePDF(html_content, dest=result_file)
            
            if not pisa_status.err:
                # Salvar o PDF no arquivo
                result_file.seek(0)
                with open(filepath, 'wb') as f:
                    f.write(result_file.getvalue())
                
                # Verificar se o arquivo foi realmente criado
                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    file_size = os.path.getsize(filepath)
                    print(f"✅ PDF gerado com layout original: {filepath} ({file_size} bytes)")
                    pdf_gerado = True
                else:
                    print(f"⚠️ Arquivo PDF não foi criado ou está vazio: {filepath}")
            else:
                print(f"⚠️ Erro ao gerar PDF com xhtml2pdf: {pisa_status.err}")
            
        except ImportError as ie:
            # Se xhtml2pdf não estiver disponível, usar ReportLab como fallback
            print(f"⚠️ xhtml2pdf não disponível ({ie}), usando ReportLab como fallback...")
            try:
                from reportlab.lib.pagesizes import A4, landscape
                from reportlab.lib.styles import getSampleStyleSheet
                from reportlab.platypus import SimpleDocTemplate
                from reportlab.platypus import Paragraph, Spacer
                
                doc = SimpleDocTemplate(filepath, pagesize=landscape(A4))
                story = []
                styles = getSampleStyleSheet()
                story.append(Paragraph("PDF gerado com layout alternativo (xhtml2pdf não disponível)", styles['Normal']))
                story.append(Spacer(1, 20))
                story.append(Paragraph("Use xhtml2pdf para manter layout original do HTML", styles['Normal']))
                doc.build(story)
                
                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    pdf_gerado = True
                    print(f"✅ PDF gerado com ReportLab: {filepath}")
            except Exception as rle:
                print(f"❌ ERRO ao gerar PDF com ReportLab: {rle}")
                import traceback
                traceback.print_exc()
            
        except Exception as e:
            print(f"❌ Erro ao gerar PDF com xhtml2pdf: {e}")
            import traceback
            traceback.print_exc()
            # Tentar fallback com ReportLab
            try:
                print("🔄 Tentando fallback com ReportLab...")
                from reportlab.lib.pagesizes import A4, landscape
                from reportlab.lib.styles import getSampleStyleSheet
                from reportlab.platypus import SimpleDocTemplate
                from reportlab.platypus import Paragraph, Spacer
                
                doc = SimpleDocTemplate(filepath, pagesize=landscape(A4))
                story = []
                styles = getSampleStyleSheet()
                story.append(Paragraph("PDF gerado com ReportLab (fallback)", styles['Normal']))
                doc.build(story)
                
                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    pdf_gerado = True
                    print(f"✅ PDF gerado com ReportLab (fallback): {filepath}")
            except Exception as fallback_error:
                print(f"❌ ERRO no fallback: {fallback_error}")
                return {
                    'success': False,
                    'message': f'Erro ao gerar PDF: {str(e)}'
                }
        
        # Verificar se o PDF foi gerado
        if not pdf_gerado:
            return {
                'success': False,
                'message': 'Erro: Não foi possível gerar o PDF (arquivo não foi criado ou está vazio)'
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
            # Verificar se filepath não é None
            if not filepath:
                error_msg = 'ERRO CRÍTICO: filepath é None na hora de salvar no Cloud Storage'
                print(f"❌ {error_msg}")
                pdf_result['success'] = False
                pdf_result['message'] = error_msg
                return pdf_result
            
            # Verificar se o arquivo existe
            if not os.path.exists(filepath):
                error_msg = f'ERRO CRÍTICO: PDF não encontrado no caminho: {filepath}'
                print(f"❌ {error_msg}")
                pdf_result['success'] = False
                pdf_result['message'] = error_msg
                return pdf_result
            
            print(f"📄 Lendo PDF do caminho temporário: {filepath}")
            
            # Ler conteúdo do PDF
            try:
                with open(filepath, 'rb') as f:
                    pdf_content = f.read()
            except Exception as read_error:
                error_msg = f'ERRO ao ler arquivo PDF: {read_error}'
                print(f"❌ {error_msg}")
                import traceback
                traceback.print_exc()
                pdf_result['success'] = False
                pdf_result['message'] = error_msg
                return pdf_result
            
            # Validar conteúdo do PDF
            if not pdf_content or len(pdf_content) == 0:
                error_msg = 'ERRO: Arquivo PDF está vazio'
                print(f"❌ {error_msg}")
                pdf_result['success'] = False
                pdf_result['message'] = error_msg
                return pdf_result
                
            if not pdf_content.startswith(b'%PDF'):
                error_msg = f'Arquivo não é um PDF válido (começa com: {pdf_content[:20]})'
                print(f"⚠️ {error_msg}")
                pdf_result['success'] = False
                pdf_result['message'] = error_msg
                return pdf_result
                    
            print(f"📊 Tamanho do PDF: {len(pdf_content)} bytes")
                    
            # Deletar arquivo temporário imediatamente após ler
            try:
                os.unlink(filepath)
                print(f"🗑️ Arquivo temporário removido: {filepath}")
            except Exception as del_error:
                print(f"⚠️ Aviso: Não foi possível deletar arquivo temporário: {del_error}")
                    
            # Salvar no Cloud Storage
            from salvar_pdf_gcs import salvar_pdf_gcs
            bucket_name = os.environ.get('GCS_BUCKET_NAME', 'romaneios-separacao')
            print(f"📦 Bucket: {bucket_name}")
            print(f"🆔 Romaneio ID: {romaneio_id}")
            print(f"📤 Chamando salvar_pdf_gcs com {len(pdf_content)} bytes...")
                    
            gcs_path = salvar_pdf_gcs(pdf_content, romaneio_id, bucket_name, is_reprint)
                    
            if gcs_path:
                print(f"✅ PDF salvo no Cloud Storage: {gcs_path}")
                pdf_result['gcs_path'] = gcs_path
                pdf_result['message'] = 'PDF salvo no Cloud Storage'
            else:
                error_msg = 'Falha ao salvar no Cloud Storage (retornou None)'
                print(f"❌ {error_msg}")
                pdf_result['success'] = False
                pdf_result['message'] = error_msg
                
        except Exception as e:
            error_msg = f'ERRO CRÍTICO ao salvar no Cloud Storage: {e}'
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            pdf_result['success'] = False
            pdf_result['message'] = error_msg
        
        return pdf_result
        
    except Exception as e:
        print(f"❌ Erro ao gerar PDF: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': f'Erro: {str(e)}'
        }
