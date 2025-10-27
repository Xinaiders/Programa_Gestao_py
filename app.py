from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import math
import pandas as pd
import hashlib
import uuid
import requests
import io
import gspread
from google.oauth2.service_account import Credentials
import threading
import time
from functools import lru_cache

app = Flask(__name__)

# Configuração do SECRET_KEY - Usar variável de ambiente no Google Cloud
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuração do banco de dados
# Se estiver no Google Cloud, usar Cloud SQL
if os.environ.get('GAE_ENV'):  # Google App Engine
    db_user = os.environ.get('DB_USER', 'root')
    db_pass = os.environ.get('DB_PASS', '')
    db_name = os.environ.get('DB_NAME', 'estoque')
    cloud_sql_connection_name = os.environ.get('CLOUD_SQL_CONNECTION_NAME')
    
    if cloud_sql_connection_name:
        # Usar Cloud SQL
        app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{db_user}:{db_pass}@/{db_name}?unix_socket=/cloudsql/{cloud_sql_connection_name}'
    else:
        # Fallback para SQLite no Cloud Storage
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///estoque.db')
else:
    # Desenvolvimento local
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///estoque.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Sistema de Cache Inteligente para otimização de performance
class CacheManager:
    def __init__(self):
        self.cache = {}
        self.cache_timestamps = {}
        self.cache_duration = 60  # 1 minuto (reduzido para dados mais frescos)
        self.last_sheets_update = {}  # Controla última atualização do Google Sheets
    
    def get_cache_key(self, func_name, *args, **kwargs):
        """Gera uma chave única para o cache baseada na função e argumentos"""
        key_data = f"{func_name}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key, force_refresh=False):
        """Recupera dados do cache se ainda válidos"""
        if force_refresh:
            self.invalidate_key(key)
            return None
            
        if key in self.cache and key in self.cache_timestamps:
            if time.time() - self.cache_timestamps[key] < self.cache_duration:
                return self.cache[key]
            else:
                # Cache expirado, remover
                del self.cache[key]
                del self.cache_timestamps[key]
        return None
    
    def set(self, key, value):
        """Armazena dados no cache"""
        self.cache[key] = value
        self.cache_timestamps[key] = time.time()
    
    def clear(self):
        """Limpa todo o cache"""
        self.cache.clear()
        self.cache_timestamps.clear()
        self.last_sheets_update.clear()
    
    def invalidate_key(self, key):
        """Invalida uma chave específica do cache"""
        if key in self.cache:
            del self.cache[key]
        if key in self.cache_timestamps:
            del self.cache_timestamps[key]
    
    def invalidate_pattern(self, pattern):
        """Invalida cache que contenha um padrão específico"""
        keys_to_remove = [k for k in self.cache.keys() if pattern in k]
        for key in keys_to_remove:
            self.invalidate_key(key)
    
    def invalidate_sheets_data(self):
        """Invalida todos os dados relacionados ao Google Sheets"""
        print("🔄 Invalidando cache do Google Sheets...")
        self.invalidate_pattern("get_google_sheets")
        self.invalidate_pattern("buscar_solicitacoes")
        self.last_sheets_update.clear()
    
    def should_refresh_sheets(self, func_name):
        """Verifica se deve atualizar dados do Google Sheets"""
        current_time = time.time()
        last_update = self.last_sheets_update.get(func_name, 0)
        
        # Forçar refresh se passou mais de 30 segundos
        if current_time - last_update > 30:
            self.last_sheets_update[func_name] = current_time
            return True
        return False

# Instância global do cache
cache_manager = CacheManager()

# Sistema de status de geração de PDF
pdf_generation_status = {}

def cached_function(cache_duration=60, force_refresh_interval=30):
    """Decorator para cachear resultados de funções com refresh inteligente"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache_key = cache_manager.get_cache_key(func.__name__, *args, **kwargs)
            
            # Verificar se deve forçar refresh
            force_refresh = cache_manager.should_refresh_sheets(func.__name__)
            
            cached_result = cache_manager.get(cache_key, force_refresh=force_refresh)
            
            if cached_result is not None and not force_refresh:
                print(f"🚀 Cache HIT para {func.__name__}")
                return cached_result
            
            if force_refresh:
                print(f"🔄 Refresh forçado para {func.__name__} (dados podem ter mudado)")
            else:
                print(f"⏳ Cache MISS para {func.__name__}, executando...")
                
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result)
            return result
        return wrapper
    return decorator

# Modelos do banco de dados
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    descricao = db.Column(db.Text)
    categoria = db.Column(db.String(50))
    preco = db.Column(db.Float)
    estoque_atual = db.Column(db.Integer, default=0)
    estoque_minimo = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Solicitacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime, nullable=False)
    solicitante = db.Column(db.String(100), nullable=False)
    codigo = db.Column(db.String(50), nullable=False)
    descricao = db.Column(db.String(200), nullable=False)
    unidade = db.Column(db.String(20), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    locacao = db.Column(db.String(50))
    media = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='pendente')
    qtd_separada = db.Column(db.Integer, default=0)
    saldo = db.Column(db.Integer, default=0)
    data_separacao = db.Column(db.DateTime)
    separado_por = db.Column(db.String(100))
    observacoes = db.Column(db.Text)
    alta_demanda = db.Column(db.Boolean, default=False)
    status_2 = db.Column(db.String(20))
    estoque_congelado = db.Column(db.Boolean, default=False)
    prazo_entrega = db.Column(db.String(50))
    fornecedor = db.Column(db.String(100))
    
    # Campos de controle interno
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Impressao(db.Model):
    """Tabela para controle de impressões"""
    id = db.Column(db.Integer, primary_key=True)
    id_impressao = db.Column(db.String(50), unique=True, nullable=False)  # Chave única da impressão
    data_impressao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    usuario_impressao = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='Pendente')  # Pendente, Processada, Cancelada
    total_itens = db.Column(db.Integer, default=0)
    observacoes = db.Column(db.Text)
    data_processamento = db.Column(db.DateTime)
    usuario_processamento = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento com itens da impressão
    itens = db.relationship('ImpressaoItem', backref='impressao', lazy=True, cascade='all, delete-orphan')

class ImpressaoItem(db.Model):
    """Tabela para itens de cada impressão"""
    id = db.Column(db.Integer, primary_key=True)
    id_impressao = db.Column(db.Integer, db.ForeignKey('impressao.id'), nullable=False)
    id_solicitacao = db.Column(db.String(100), nullable=False)  # ID único da solicitação
    data_solicitacao = db.Column(db.DateTime, nullable=False)
    solicitante = db.Column(db.String(100), nullable=False)
    codigo = db.Column(db.String(50), nullable=False)
    descricao = db.Column(db.String(200), nullable=False)
    unidade = db.Column(db.String(20), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    locacao = db.Column(db.String(50))
    saldo_estoque = db.Column(db.Integer, default=0)
    media_consumo = db.Column(db.Float, default=0)
    status_item = db.Column(db.String(20), default='Pendente')  # Pendente, Separado, Parcial, Cancelado
    qtd_separada = db.Column(db.Integer, default=0)
    observacoes_item = db.Column(db.Text)
    data_separacao = db.Column(db.DateTime)
    separado_por = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Tabela MatrizImportada removida - dados agora vêm diretamente do Google Sheets

# ===== FUNÇÕES DE GERAÇÃO DE IDs ÚNICOS =====

def gerar_id_solicitacao(data, solicitante, codigo, quantidade, timestamp=None):
    """Gera ID único para solicitação baseado em seus dados principais"""
    if timestamp is None:
        # Usar microssegundos para garantir unicidade
        now = datetime.now()
        timestamp = now.strftime('%H%M%S%f')[:-3]  # Incluir milissegundos
    
    # Limpar e normalizar nome do solicitante
    solicitante_clean = str(solicitante).strip().upper().replace(' ', '_')[:10]  # Máximo 10 caracteres
    
    # Criar string única combinando todos os campos + timestamp completo
    dados_combinados = f"{data}_{solicitante}_{codigo}_{quantidade}_{timestamp}_{datetime.now().microsecond}"
    
    # Gerar hash MD5 e pegar primeiros 8 caracteres
    hash_obj = hashlib.md5(dados_combinados.encode())
    hash_hex = hash_obj.hexdigest()[:8].upper()
    
    # Formato: SOL_YYYYMMDD_HHMMSSMMM_SOLICITANTE_XXXX (incluindo solicitante)
    data_str = data.strftime('%Y%m%d') if isinstance(data, datetime) else str(data)[:10].replace('-', '')
    return f"SOL_{data_str}_{timestamp}_{solicitante_clean}_{hash_hex}"


def gerar_id_impressao(usuario, timestamp=None):
    """Gera ID único para impressão (formato numérico simples)"""
    try:
        sheet = get_google_sheets_connection()
        if not sheet:
            raise Exception("Não foi possível conectar com Google Sheets")
        
        impressoes_worksheet = sheet.worksheet("IMPRESSOES")
        all_values = impressoes_worksheet.get_all_values()
        
        # Encontrar o próximo número sequencial
        proximo_numero = 1
        
        if len(all_values) > 1:  # Se há dados além do cabeçalho
            # Buscar o maior número existente
            numeros_existentes = []
            for row in all_values[1:]:
                if len(row) > 0 and row[0].startswith('ROM-'):
                    try:
                        # Extrair número do formato ROM-000001
                        numero_str = row[0].split('-')[1]
                        numero = int(numero_str)
                        numeros_existentes.append(numero)
                    except (ValueError, IndexError):
                        continue
            
            if numeros_existentes:
                proximo_numero = max(numeros_existentes) + 1
        
        # Formato: ROM-000001, ROM-000002, etc.
        return f"ROM-{proximo_numero:06d}"
        
    except Exception as e:
        print(f"❌ Erro ao gerar ID de impressão: {e}")
        # Fallback para formato antigo se houver erro
        if timestamp is None:
            timestamp = datetime.now()
        data_str = timestamp.strftime('%Y%m%d_%H%M%S')
        hash_hex = hashlib.md5(f"{usuario}_{timestamp}".encode()).hexdigest()[:6].upper()
        return f"IMP_{data_str}_{hash_hex}"

# ===== FUNÇÕES DE CONTROLE DE IMPRESSÕES NO GOOGLE SHEETS =====

def criar_aba_impressoes():
    """Cria a aba IMPRESSOES no Google Sheets se não existir"""
    try:
        sheet = get_google_sheets_connection()
        if not sheet:
            raise Exception("Não foi possível conectar com Google Sheets")
        
        # Verificar se a aba já existe
        try:
            worksheet = sheet.worksheet("IMPRESSOES")
            print("✅ Aba IMPRESSOES já existe")
            return worksheet
        except gspread.WorksheetNotFound:
            pass
        
        # Criar nova aba
        worksheet = sheet.add_worksheet(title="IMPRESSOES", rows=1000, cols=20)
        
        # Definir cabeçalhos
        headers = [
            "ID_IMPRESSAO", "DATA_IMPRESSAO", "USUARIO_IMPRESSAO", "STATUS", 
            "TOTAL_ITENS", "OBSERVACOES", "DATA_PROCESSAMENTO", "USUARIO_PROCESSAMENTO",
            "CREATED_AT", "UPDATED_AT"
        ]
        
        worksheet.append_row(headers)
        
        # Formatar cabeçalho
        worksheet.format('A1:J1', {
            'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.8},
            'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
        })
        
        print("✅ Aba IMPRESSOES criada com sucesso!")
        return worksheet
        
    except Exception as e:
        print(f"❌ Erro ao criar aba IMPRESSOES: {e}")
        return None

def criar_aba_impressao_itens():
    """Cria a aba IMPRESSAO_ITENS no Google Sheets se não existir"""
    try:
        sheet = get_google_sheets_connection()
        if not sheet:
            raise Exception("Não foi possível conectar com Google Sheets")
        
        # Verificar se a aba já existe
        try:
            worksheet = sheet.worksheet("IMPRESSAO_ITENS")
            print("✅ Aba IMPRESSAO_ITENS já existe")
            return worksheet
        except gspread.WorksheetNotFound:
            pass
        
        # Criar nova aba
        worksheet = sheet.add_worksheet(title="IMPRESSAO_ITENS", rows=5000, cols=25)
        
        # Definir cabeçalhos
        headers = [
            "ID_IMPRESSAO", "ID_SOLICITACAO", "DATA_SOLICITACAO", "SOLICITANTE", 
            "CODIGO", "DESCRICAO", "UNIDADE", "QUANTIDADE", "LOCALIZACAO",
            "SALDO_ESTOQUE", "MEDIA_CONSUMO", "STATUS_ITEM", "QTD_SEPARADA",
            "OBSERVACOES_ITEM", "DATA_SEPARACAO", "SEPARADO_POR", "CREATED_AT", "UPDATED_AT"
        ]
        
        worksheet.append_row(headers)
        
        # Formatar cabeçalho
        worksheet.format('A1:R1', {
            'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.8},
            'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
        })
        
        print("✅ Aba IMPRESSAO_ITENS criada com sucesso!")
        return worksheet
        
    except Exception as e:
        print(f"❌ Erro ao criar aba IMPRESSAO_ITENS: {e}")
        return None

def inicializar_abas_controle():
    """Inicializa as abas de controle de impressões"""
    print("🔄 Inicializando abas de controle de impressões...")
    
    impressoes_worksheet = criar_aba_impressoes()
    itens_worksheet = criar_aba_impressao_itens()
    
    if impressoes_worksheet and itens_worksheet:
        print("✅ Abas de controle inicializadas com sucesso!")
        return True
    else:
        print("❌ Erro ao inicializar abas de controle")
        return False

def criar_impressao(usuario, solicitacoes_selecionadas, observacoes=""):
    """Cria uma nova impressão no Google Sheets"""
    try:
        # Primeiro, garantir que as colunas existem
        if not criar_colunas_impressao_itens():
            raise Exception("Não foi possível criar/verificar colunas IMPRESSAO_ITENS")
            
        sheet = get_google_sheets_connection()
        if not sheet:
            raise Exception("Não foi possível conectar com Google Sheets")
        
        # Gerar ID único da impressão
        id_impressao = gerar_id_impressao(usuario)
        data_impressao = datetime.now()
        
        # Acessar abas
        impressoes_worksheet = sheet.worksheet("IMPRESSOES")
        itens_worksheet = sheet.worksheet("IMPRESSAO_ITENS")
        
        # Criar registro da impressão
        impressao_data = [
            id_impressao,
            data_impressao.strftime('%Y-%m-%d %H:%M:%S'),
            usuario,
            'Pendente',
            len(solicitacoes_selecionadas),
            observacoes,
            '',  # DATA_PROCESSAMENTO
            '',  # USUARIO_PROCESSAMENTO
            data_impressao.strftime('%Y-%m-%d %H:%M:%S'),  # CREATED_AT
            data_impressao.strftime('%Y-%m-%d %H:%M:%S')   # UPDATED_AT
        ]
        
        impressoes_worksheet.append_row(impressao_data)
        
        # Criar registros dos itens e adicionar ID_SOLICITACAO na aba Solicitações
        solicitacoes_worksheet = sheet.worksheet("Solicitações")
        solicitacoes_values = solicitacoes_worksheet.get_all_values()
        header_solicitacoes = solicitacoes_values[0] if solicitacoes_values else []
        
        # ID_SOLICITACAO está na coluna P (índice 15)
        id_solicitacao_col = 15  # Coluna P
        print(f"🔍 Usando coluna P (índice {id_solicitacao_col}) para ID_SOLICITACAO")
        
        # Verificar se a coluna P existe
        if len(header_solicitacoes) <= id_solicitacao_col:
            print(f"❌ Coluna P não existe. Total de colunas: {len(header_solicitacoes)}")
            print(f"🔍 Header completo: {header_solicitacoes}")
            # Adicionar coluna ID_SOLICITACAO se não existir
            print("📝 Adicionando coluna ID_SOLICITACAO na aba Solicitações...")
            solicitacoes_worksheet.insert_cols([["ID_SOLICITACAO"]], 1)
            id_solicitacao_col = 0
            # Atualizar dados
            solicitacoes_values = solicitacoes_worksheet.get_all_values()
            header_solicitacoes = solicitacoes_values[0]
        
        # Encontrar colunas para busca
        codigo_col = None
        solicitante_col = None
        for i, col_name in enumerate(header_solicitacoes):
            col_name_clean = col_name.strip().lower()
            if 'código' in col_name_clean or 'codigo' in col_name_clean:
                codigo_col = i
            elif 'solicitante' in col_name_clean:
                solicitante_col = i
        
        print(f"🔍 Colunas encontradas - Código: {codigo_col}, Solicitante: {solicitante_col}")
        
        atualizacoes_solicitacoes = []
        
        for solicitacao in solicitacoes_selecionadas:
            codigo = solicitacao.get('codigo', '')
            solicitante = solicitacao.get('solicitante', '')
            
            print(f"🔍 Verificando status para: {codigo} - {solicitante}")
            
            # Verificar status da solicitação na aba Solicitações
            status_solicitacao = None
            if codigo_col is not None and solicitante_col is not None:
                for i, row in enumerate(solicitacoes_values[1:], start=2):
                    if (len(row) > max(codigo_col, solicitante_col) and
                        row[codigo_col].strip() == codigo and
                        row[solicitante_col].strip() == solicitante):
                        
                        # Encontrar coluna Status
                        status_col = None
                        for j, col_name in enumerate(header_solicitacoes):
                            if col_name.strip().lower() == 'status':
                                status_col = j
                                break
                        
                        if status_col is not None and len(row) > status_col:
                            status_solicitacao = row[status_col].strip()
                            print(f"   Status encontrado: {status_solicitacao}")
                        break
            
            # Validar se pode imprimir
            if status_solicitacao == 'Em Separação':
                print(f"❌ Solicitação {codigo} já está 'Em Separação' - não pode imprimir novamente!")
                raise Exception(f"Solicitação {codigo} já está sendo processada (Status: Em Separação). Aguarde o processamento atual.")
            elif status_solicitacao == 'Concluída':
                print(f"❌ Solicitação {codigo} já foi totalmente processada (Status: Concluída) - não pode imprimir novamente!")
                raise Exception(f"Solicitação {codigo} já foi totalmente processada (Status: Concluída). Não é possível reimprimir.")
            elif status_solicitacao not in ['Aberto', 'Parcial', '']:
                print(f"⚠️ Status inesperado: {status_solicitacao} para {codigo}")
            
            print(f"✅ Status permitido para impressão: {status_solicitacao}")
            
            # Gerar novo ID_SOLICITACAO apenas se status permitir
            solicitacao['id_solicitacao'] = gerar_id_solicitacao(
                solicitacao.get('data', data_impressao),
                solicitacao.get('solicitante', ''),
                solicitacao.get('codigo', ''),
                solicitacao.get('quantidade', 0)
            )
            print(f"🆕 Gerando novo ID: {solicitacao['id_solicitacao']}")
            
            print(f"🔍 Processando solicitação: {solicitacao.get('codigo', '')} - {solicitacao.get('solicitante', '')}")
            print(f"   ID_SOLICITACAO: {solicitacao['id_solicitacao']}")
            
            # SUBSTITUIR ID_SOLICITACAO na aba Solicitações (SEMPRE)
            if codigo_col is not None and solicitante_col is not None:
                codigo = solicitacao.get('codigo', '')
                solicitante = solicitacao.get('solicitante', '')
                
                print(f"   Buscando na aba Solicitações: Código='{codigo}', Solicitante='{solicitante}'")
                
                # Buscar linha correspondente na aba Solicitações
                encontrado = False
                for i, row in enumerate(solicitacoes_values[1:], start=2):
                    print(f"   Linha {i}: {row[:3]}... (total: {len(row)} colunas)")
                    if (len(row) > max(codigo_col, solicitante_col) and
                        row[codigo_col].strip() == codigo and
                        row[solicitante_col].strip() == solicitante):
                        
                        print(f"   ✅ Linha {i} encontrada!")
                        # SEMPRE substituir o ID_SOLICITACAO (mesmo se já existir)
                        atualizacoes_solicitacoes.append({
                            'range': f'{chr(65 + id_solicitacao_col)}{i}',
                            'values': [[solicitacao['id_solicitacao']]]
                        })
                        print(f"🔄 SUBSTITUINDO ID_SOLICITACAO na linha {i}: {solicitacao['id_solicitacao']}")
                        encontrado = True
                        break
                
                if not encontrado:
                    print(f"❌ Solicitação não encontrada na aba Solicitações!")
            else:
                print(f"❌ Colunas de busca não encontradas!")
            
            # Estrutura correta da aba IMPRESSAO_ITENS
            item_data = [
                id_impressao,  # ID_IMPRESSAO (coluna A)
                solicitacao['id_solicitacao'],  # ID_SOLICITACAO (coluna B)
                solicitacao.get('data', data_impressao).strftime('%Y-%m-%d %H:%M:%S') if hasattr(solicitacao.get('data'), 'strftime') else str(solicitacao.get('data', '')),  # DATA (coluna C)
                solicitacao.get('solicitante', ''),  # SOLICITANTE (coluna D)
                solicitacao.get('codigo', ''),  # CODIGO (coluna E)
                solicitacao.get('descricao', ''),  # DESCRICAO (coluna F)
                solicitacao.get('unidade', ''),  # UNIDADE (coluna G)
                solicitacao.get('quantidade', 0),  # QUANTIDADE (coluna H)
                solicitacao.get('locacao_matriz', '1 E5 E03/F03'),  # LOCACAO_MATRIZ (coluna I)
                solicitacao.get('saldo_estoque', 600),  # SALDO_ESTOQUE (coluna J)
                solicitacao.get('media_mensal', 41),  # MEDIA_MENSAL (coluna K)
                solicitacao.get('alta_demanda', False),  # ALTA_DEMANDA (coluna L)
                'Pendente',  # STATUS_ITEM (coluna M)
                0,  # QTD_SEPARADA (coluna N)
                '',  # OBSERVACOES_ITEM (coluna O)
                '',  # DATA_SEPARACAO (coluna P)
                '',  # SEPARADO_POR (coluna Q)
                '',  # USUARIO_PROCESSAMENTO (coluna R)
                data_impressao.strftime('%Y-%m-%d %H:%M:%S'),  # CREATED_AT (coluna S)
                data_impressao.strftime('%Y-%m-%d %H:%M:%S')   # UPDATED_AT (coluna T)
            ]
            
            print(f"📋 Criando item na IMPRESSAO_ITENS:")
            print(f"   ID_Impressao: {id_impressao}")
            print(f"   ID_Solicitacao: {solicitacao['id_solicitacao']}")
            print(f"   Codigo: {solicitacao.get('codigo', '')}")
            print(f"   Solicitante: {solicitacao.get('solicitante', '')}")
            print(f"   Quantidade: {solicitacao.get('quantidade', 0)}")
            print(f"   Total de colunas: {len(item_data)}")
            
            itens_worksheet.append_row(item_data)
        
        # Executar atualizações de ID_SOLICITACAO na aba Solicitações
        if atualizacoes_solicitacoes:
            print(f"🔄 Executando {len(atualizacoes_solicitacoes)} atualizações de ID_SOLICITACAO...")
            solicitacoes_worksheet.batch_update(atualizacoes_solicitacoes)
            print(f"✅ {len(atualizacoes_solicitacoes)} IDs adicionados na aba Solicitações!")
        
        # Atualizar status das solicitações para "Em Separação" na aba Solicitações
        print("🔄 Atualizando status das solicitações para 'Em Separação'...")
        
        try:
            # Usar índices das linhas (IDs simples) em vez de IDs complexos
            ids_para_atualizar = [sol.get('id', '') for sol in solicitacoes_selecionadas if sol.get('id')]
            
            if ids_para_atualizar:
                # Usar atualização otimizada
                sucesso_status = atualizar_status_rapido(ids_para_atualizar)
                
                if sucesso_status:
                    print(f"✅ Status atualizado para 'Em Separação' - {len(ids_para_atualizar)} solicitações")
                else:
                    print("⚠️ Erro ao atualizar status das solicitações")
            else:
                print("⚠️ Nenhum ID encontrado para atualizar")
        except Exception as e:
            print(f"⚠️ Erro ao atualizar status: {e}")
            import traceback
            traceback.print_exc()
        
        # Gerar PDF usando o HTML já renderizado (otimizado)
        print("🔄 Gerando PDF do romaneio...")
        
        # Detectar se está rodando no Google Cloud
        import os
        import threading
        
        if os.getenv('GAE_APPLICATION'):
            # Google Cloud - usar ReportLab
            from pdf_cloud_generator import salvar_pdf_cloud
            pdf_function = salvar_pdf_cloud
        else:
            # Desenvolvimento local - usar Chrome headless
            from pdf_browser_generator import salvar_pdf_direto_html
            pdf_function = salvar_pdf_direto_html
        
        # Preparar dados do romaneio
        romaneio_data = {
            'id_impressao': id_impressao,
            'data_impressao': data_impressao.strftime('%d/%m/%Y, %H:%M:%S'),
            'usuario_impressao': usuario,
            'status': 'Pendente',
            'total_itens': len(solicitacoes_selecionadas),
            'observacoes': observacoes
        }
        
        # Preparar dados dos itens
        itens_data = []
        for solicitacao in solicitacoes_selecionadas:
            item = {
                'data': solicitacao.get('data', data_impressao).strftime('%d/%m/%Y') if hasattr(solicitacao.get('data'), 'strftime') else str(solicitacao.get('data', '')),
                'solicitante': solicitacao.get('solicitante', ''),
                'codigo': solicitacao.get('codigo', ''),
                'descricao': solicitacao.get('descricao', ''),
                'quantidade': solicitacao.get('quantidade', 0),
                'alta_demanda': getattr(solicitacao, 'alta_demanda', False),
                'locacao_matriz': solicitacao.get('locacao_matriz', '1 E5 E03/F03'),
                'saldo_estoque': solicitacao.get('saldo_estoque', 600),
                'media_mensal': solicitacao.get('media_mensal', 41),
                'qtd_pendente': solicitacao.get('quantidade', 0),
                'qtd_separada': 0
            }
            itens_data.append(item)
        
        # Recuperar tipo_romaneio do cache
        tipo_romaneio = 'Romaneio de Separação'
        if 'romaneio_info' in globals() and id_impressao in globals()['romaneio_info']:
            tipo_romaneio = globals()['romaneio_info'][id_impressao]
        
        # Renderizar o template HTML (igual ao que aparece na tela)
        html_content = render_template('formulario_impressao.html', 
                                     id_impressao=id_impressao,
                                     solicitacoes=itens_data,
                                     tipo_romaneio=tipo_romaneio)
        
        # OTIMIZAÇÃO: Salvar PDF em thread separada para não bloquear a resposta
        def gerar_pdf_async():
            try:
                # Marcar como iniciado
                pdf_generation_status[id_impressao] = {
                    'status': 'gerando',
                    'inicio': datetime.now().strftime('%H:%M:%S'),
                    'progresso': 0
                }
                
                print(f"🔄 Iniciando geração de PDF em background para {id_impressao}...")
                
                # Simular progresso
                pdf_generation_status[id_impressao]['progresso'] = 25
                
                resultado = pdf_function(html_content, romaneio_data, pasta_destino='Romaneios_Separacao', is_reprint=False)
                
                if resultado['success']:
                    pdf_generation_status[id_impressao] = {
                        'status': 'concluido',
                        'inicio': pdf_generation_status[id_impressao]['inicio'],
                        'fim': datetime.now().strftime('%H:%M:%S'),
                        'progresso': 100,
                        'arquivo': resultado.get('file_path', '')
                    }
                    print(f"✅ PDF gerado com sucesso: {resultado['message']}")
                    if 'file_path' in resultado:
                        print(f"📁 Arquivo salvo: {resultado['file_path']}")
                else:
                    pdf_generation_status[id_impressao] = {
                        'status': 'erro',
                        'inicio': pdf_generation_status[id_impressao]['inicio'],
                        'fim': datetime.now().strftime('%H:%M:%S'),
                        'progresso': 0,
                        'erro': resultado['message']
                    }
                    print(f"⚠️ Erro na geração do PDF: {resultado['message']}")
            except Exception as e:
                pdf_generation_status[id_impressao] = {
                    'status': 'erro',
                    'inicio': pdf_generation_status.get(id_impressao, {}).get('inicio', ''),
                    'fim': datetime.now().strftime('%H:%M:%S'),
                    'progresso': 0,
                    'erro': str(e)
                }
                print(f"⚠️ Erro ao gerar PDF em background: {e}")
        
        # Executar geração de PDF em thread separada (NÃO BLOQUEIA)
        pdf_thread = threading.Thread(target=gerar_pdf_async, name=f"PDF-{id_impressao}")
        pdf_thread.daemon = True
        pdf_thread.start()
        
        print(f"✅ Impressão {id_impressao} criada com {len(solicitacoes_selecionadas)} itens")
        print(f"🚀 PDF sendo gerado em background...")
        return id_impressao
        
    except Exception as e:
        print(f"❌ Erro ao criar impressão: {e}")
        return None

def buscar_impressoes_pendentes():
    """Busca impressões com status Pendente"""
    try:
        sheet = get_google_sheets_connection()
        if not sheet:
            raise Exception("Não foi possível conectar com Google Sheets")
        
        impressoes_worksheet = sheet.worksheet("IMPRESSOES")
        all_values = impressoes_worksheet.get_all_values()
        
        if len(all_values) < 2:
            return []
        
        headers = all_values[0]
        impressoes = []
        
        for row in all_values[1:]:
            if len(row) >= 4 and row[3] == 'Pendente':  # STATUS
                impressao = {
                    'id_impressao': row[0],
                    'data_impressao': row[1],
                    'usuario_impressao': row[2],
                    'status': row[3],
                    'total_itens': int(row[4]) if row[4].isdigit() else 0,
                    'observacoes': row[5] if len(row) > 5 else ''
                }
                impressoes.append(impressao)
        
        # Ordenar por ID numérico (mais recente primeiro)
        impressoes.sort(key=lambda x: int(x['id_impressao'].split('-')[1]) if '-' in x['id_impressao'] else 0, reverse=True)
        
        return impressoes
        
    except Exception as e:
        print(f"❌ Erro ao buscar impressões pendentes: {e}")
        return []

def buscar_todas_impressoes():
    """Busca todas as impressões (independente do status)"""
    try:
        sheet = get_google_sheets_connection()
        if not sheet:
            raise Exception("Não foi possível conectar com Google Sheets")
        
        impressoes_worksheet = sheet.worksheet("IMPRESSOES")
        all_values = impressoes_worksheet.get_all_values()
        
        if len(all_values) < 2:
            return []
        
        headers = all_values[0]
        impressoes = []
        
        for row in all_values[1:]:
            if len(row) >= 4:  # Verificar se tem colunas suficientes
                impressao = {
                    'id_impressao': row[0],
                    'data_impressao': row[1],
                    'usuario_impressao': row[2],
                    'status': row[3],
                    'total_itens': int(row[4]) if row[4].isdigit() else 0,
                    'observacoes': row[5] if len(row) > 5 else ''
                }
                impressoes.append(impressao)
        
        # Ordenar por ID numérico (mais recente primeiro)
        impressoes.sort(key=lambda x: int(x['id_impressao'].split('-')[1]) if '-' in x['id_impressao'] else 0, reverse=True)
        
        return impressoes
        
    except Exception as e:
        print(f"❌ Erro ao buscar todas as impressões: {e}")
        return []

def buscar_impressao_por_id(id_impressao):
    """Busca impressão específica por ID"""
    try:
        sheet = get_google_sheets_connection()
        if not sheet:
            raise Exception("Não foi possível conectar com Google Sheets")
        
        impressoes_worksheet = sheet.worksheet("IMPRESSOES")
        all_values = impressoes_worksheet.get_all_values()
        
        if len(all_values) < 2:
            return None
        
        for row in all_values[1:]:
            if len(row) >= 1 and row[0] == id_impressao:
                return {
                    'id_impressao': row[0],
                    'data_impressao': row[1],
                    'usuario_impressao': row[2],
                    'status': row[3],
                    'total_itens': int(row[4]) if row[4].isdigit() else 0,
                    'observacoes': row[5] if len(row) > 5 else '',
                    'data_processamento': row[6] if len(row) > 6 else '',
                    'usuario_processamento': row[7] if len(row) > 7 else ''
                }
        
        return None
        
    except Exception as e:
        print(f"❌ Erro ao buscar impressão por ID: {e}")
        return None

def buscar_itens_impressao(id_impressao):
    """Busca itens de uma impressão específica"""
    try:
        sheet = get_google_sheets_connection()
        if not sheet:
            raise Exception("Não foi possível conectar com Google Sheets")
        
        itens_worksheet = sheet.worksheet("IMPRESSAO_ITENS")
        all_values = itens_worksheet.get_all_values()
        
        if len(all_values) < 2:
            return []
        
        headers = all_values[0]
        itens = []
        
        for row in all_values[1:]:
            if len(row) >= 2 and row[0] == id_impressao:  # ID_IMPRESSAO
                item = {
                    'id_impressao': row[0],
                    'id_solicitacao': row[1],
                    'data_solicitacao': row[2],
                    'solicitante': row[3],
                    'codigo': row[4],
                    'descricao': row[5],
                    'unidade': row[6],
                    'quantidade': int(row[7]) if row[7].isdigit() else 0,
                    'localizacao': row[8],
                    'saldo_estoque': int(row[9]) if row[9].isdigit() else 0,
                    'media_consumo': float(row[10]) if row[10].replace('.', '').isdigit() else 0,
                    'status_item': 'Pendente' if row[12].lower() in ['false', '0', ''] else ('Processado' if row[12].lower() in ['true', '1', 'processado'] else row[12]),
                    'qtd_separada': int(row[13]) if len(row) > 13 and row[13].isdigit() else 0,
                    'observacoes_item': row[14] if len(row) > 14 else '',
                    'data_separacao': row[15] if len(row) > 15 else '',
                    'separado_por': row[16] if len(row) > 16 else ''
                }
                itens.append(item)
        
        return itens
        
    except Exception as e:
        print(f"❌ Erro ao buscar itens da impressão {id_impressao}: {e}")
        return []

def buscar_status_impressao(id_impressao):
    """Busca o status de uma impressão na aba IMPRESSOES"""
    try:
        print(f"🔍 Buscando status da impressão {id_impressao} na aba IMPRESSOES...")
        
        sheet = get_google_sheets_connection()
        if not sheet:
            raise Exception("Não foi possível conectar com Google Sheets")
        
        impressoes_worksheet = sheet.worksheet("IMPRESSOES")
        all_values = impressoes_worksheet.get_all_values()
        
        if len(all_values) < 2:
            return {'status': 'Pendente', 'data_criacao': '', 'total_itens': 0}
        
        # Buscar a linha da impressão
        for row in all_values[1:]:
            if len(row) > 0 and row[0] == id_impressao:  # ID_IMPRESSAO
                print(f"✅ Impressão {id_impressao} encontrada na aba IMPRESSOES")
                print(f"📋 Dados da linha: {row[:5]}...")
                
                # Extrair dados da impressão
                status = row[3] if len(row) > 3 else 'Pendente'  # STATUS (coluna D)
                data_criacao = row[1] if len(row) > 1 else ''  # DATA_IMPRESSAO (coluna B)
                total_itens = int(row[4]) if len(row) > 4 and row[4].isdigit() else 0  # TOTAL_ITENS (coluna E)
                data_processamento = row[6] if len(row) > 6 else ''  # DATA_PROCESSAMENTO (coluna G)
                
                print(f"📊 Status: {status}, Data Criação: {data_criacao}, Data Processamento: {data_processamento}, Total: {total_itens}")
                
                return {
                    'status': status,
                    'data_criacao': data_criacao,
                    'data_processamento': data_processamento,
                    'total_itens': total_itens
                }
        
        print(f"❌ Impressão {id_impressao} não encontrada na aba IMPRESSOES")
        return {'status': 'Pendente', 'data_criacao': '', 'data_processamento': '', 'total_itens': 0}
        
    except Exception as e:
        print(f"❌ Erro ao buscar status da impressão {id_impressao}: {e}")
        return {'status': 'Pendente', 'data_criacao': '', 'data_processamento': '', 'total_itens': 0}

def atualizar_status_impressao(id_impressao, novo_status, usuario_processamento=None):
    """Atualiza status de uma impressão"""
    try:
        sheet = get_google_sheets_connection()
        if not sheet:
            raise Exception("Não foi possível conectar com Google Sheets")
        
        impressoes_worksheet = sheet.worksheet("IMPRESSOES")
        all_values = impressoes_worksheet.get_all_values()
        
        if len(all_values) < 2:
            return False
        
        # Encontrar a linha da impressão
        for i, row in enumerate(all_values[1:], start=2):
            if len(row) >= 1 and row[0] == id_impressao:
                # Atualizar status
                impressoes_worksheet.update_cell(i, 4, novo_status)  # STATUS
                
                if novo_status == 'Processado' and usuario_processamento:
                    impressoes_worksheet.update_cell(i, 6, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))  # DATA_PROCESSAMENTO
                    impressoes_worksheet.update_cell(i, 7, usuario_processamento)  # USUARIO_PROCESSAMENTO
                
                impressoes_worksheet.update_cell(i, 10, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))  # UPDATED_AT
                
                print(f"✅ Status da impressão {id_impressao} atualizado para {novo_status}")
                return True
        
        print(f"❌ Impressão {id_impressao} não encontrada")
        return False
        
    except Exception as e:
        print(f"❌ Erro ao atualizar status da impressão: {e}")
        return False

def verificar_itens_em_impressao_pendente(ids_solicitacoes):
    """Verifica se algum dos IDs já está em impressão pendente (não processada)"""
    try:
        sheet = get_google_sheets_connection()
        if not sheet:
            raise Exception("Não foi possível conectar com Google Sheets")
        
        # Buscar impressões pendentes (apenas status "Pendente")
        impressoes_pendentes = buscar_impressoes_pendentes()
        if not impressoes_pendentes:
            return []
        
        # Buscar todos os itens de impressões pendentes
        itens_worksheet = sheet.worksheet("IMPRESSAO_ITENS")
        all_values = itens_worksheet.get_all_values()
        
        if len(all_values) < 2:
            return []
        
        # IDs das impressões pendentes (apenas status "Pendente")
        ids_impressoes_pendentes = [imp['id_impressao'] for imp in impressoes_pendentes]
        
        # IDs de solicitações já em impressão pendente
        ids_em_impressao = []
        
        for row in all_values[1:]:
            if len(row) >= 2:
                id_impressao = row[0]  # ID_IMPRESSAO
                id_solicitacao = row[1]  # ID_SOLICITACAO
                
                # Se está em impressão pendente (não processada) e é um dos IDs selecionados
                if id_impressao in ids_impressoes_pendentes and id_solicitacao in ids_solicitacoes:
                    ids_em_impressao.append(id_solicitacao)
        
        return ids_em_impressao
        
    except Exception as e:
        print(f"❌ Erro ao verificar itens em impressão pendente: {e}")
        return []

def verificar_itens_em_separacao(ids_solicitacoes):
    """Verifica quais itens já estão com status 'Em Separação'"""
    try:
        sheet = get_google_sheets_connection()
        if not sheet:
            return []
        
        # Acessar a aba "Solicitações"
        worksheet = sheet.get_worksheet(0)
        all_values = worksheet.get_all_values()
        
        if not all_values or len(all_values) < 2:
            return []
        
        # Encontrar coluna de Status
        headers = all_values[0]
        status_col = None
        
        for i, header in enumerate(headers):
            header_lower = header.lower().strip()
            if 'status' in header_lower and status_col is None:
                status_col = i
        
        if status_col is None:
            print("❌ Coluna Status não encontrada")
            return []
        
        # Buscar itens com status "Em Separação" usando índice da linha como ID
        itens_em_separacao = []
        for row_num, row in enumerate(all_values[1:], start=1):
            if len(row) > status_col:
                # Usar índice da linha como ID (row_num)
                item_id = str(row_num)
                status = row[status_col].strip() if len(row) > status_col else ''
                
                if item_id in ids_solicitacoes and status == 'Em Separação':
                    itens_em_separacao.append(item_id)
        
        return itens_em_separacao
        
    except Exception as e:
        print(f"❌ Erro ao verificar itens em separação: {e}")
        return []

def atualizar_status_rapido(ids_solicitacoes):
    """Atualiza status para 'Em Separação' de forma otimizada"""
    try:
        # Conectar com Google Sheets
        sheet = get_google_sheets_connection()
        if not sheet:
            return False
        
        # Acessar a aba "Solicitações"
        worksheet = sheet.get_worksheet(0)
        
        # Encontrar coluna de status
        headers = worksheet.row_values(1)
        status_col = None
        
        for i, header in enumerate(headers):
            if 'status' in header.lower().strip():
                status_col = i
                break
        
        if status_col is None:
            return False
        
        # Preparar atualizações em lote
        updates = []
        
        # Atualizar apenas as linhas necessárias
        for row_id in ids_solicitacoes:
            if row_id.isdigit():
                row_num = int(row_id) + 1  # +1 porque a planilha começa em 1
                status_cell = f"{chr(65 + status_col)}{row_num}"
                updates.append({
                    'range': status_cell,
                    'values': [['Em Separação']]
                })
        
        if updates:
            # Executar todas as atualizações de uma vez
            worksheet.batch_update(updates)
            
            # OTIMIZAÇÃO: Invalidar cache após atualização de status
            print("🔄 Invalidando cache após atualização de status...")
            cache_manager.invalidate_sheets_data()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na atualização rápida: {e}")
        return False

def atualizar_status_para_em_separacao_por_id(ids_solicitacoes):
    """Atualiza status para 'Em Separação' usando IDs únicos das solicitações"""
    try:
        # Conectar com Google Sheets
        sheet = get_google_sheets_connection()
        if not sheet:
            print("❌ Não foi possível conectar com Google Sheets")
            return False
        
        # Acessar a aba "Solicitações"
        worksheet = sheet.get_worksheet(0)
        
        # Obter todos os dados uma única vez
        all_values = worksheet.get_all_values()
        if not all_values or len(all_values) < 2:
            print("❌ Planilha está vazia")
            return False
        
        # Encontrar coluna de status
        headers = all_values[0]
        status_col = None
        
        for i, header in enumerate(headers):
            header_lower = header.lower().strip()
            if 'status' in header_lower and status_col is None:
                status_col = i
        
        if status_col is None:
            print(f"❌ Coluna Status não encontrada")
            return False
        
        # Usar índice da linha como ID (não há coluna ID na planilha)
        print(f"📍 Usando índice da linha como ID, Status na coluna: {status_col}")
        
        print(f"📊 Atualizando status para {len(ids_solicitacoes)} IDs únicos...")
        
        # Preparar atualizações em lote
        updates = []
        ids_encontrados = set()
        
        # Buscar linhas que precisam ser atualizadas
        for row_num, row in enumerate(all_values[1:], start=2):
            if len(row) > status_col:
                # Usar índice da linha como ID
                item_id = str(row_num - 1)  # row_num - 1 porque começamos em start=2
                status_atual = row[status_col].strip() if len(row) > status_col else ''
                
                # Verificar se este ID está na lista e pode ser atualizado
                if item_id in ids_solicitacoes and status_atual not in ['Concluído', 'Excedido', 'Em Separação']:
                    status_cell_address = f"{chr(65 + status_col)}{row_num}"
                    updates.append({
                        'range': status_cell_address,
                        'values': [['Em Separação']]
                    })
                    ids_encontrados.add(item_id)
                    print(f"   ✅ ID {item_id} será atualizado (linha {row_num}) - Status atual: '{status_atual}'")
                elif item_id in ids_solicitacoes:
                    print(f"   ⚠️ ID {item_id} já tem status '{status_atual}' - não será atualizado")
        
        # Executar atualizações em lote se houver alguma
        if updates:
            try:
                worksheet.batch_update(updates)
                print(f"✅ {len(updates)} status atualizados com sucesso!")
                return True
            except Exception as e:
                print(f"❌ Erro ao executar atualizações em lote: {e}")
                return False
        else:
            print("⚠️ Nenhuma linha encontrada para atualizar")
            return True
        
    except Exception as e:
        print(f"❌ Erro ao atualizar status: {e}")
        return False

def validar_selecao_impressao(ids_selecionados):
    """Valida se a seleção pode ser impressa (não há conflitos)"""
    try:
        # Verificar se há itens já em impressão pendente
        ids_em_impressao = verificar_itens_em_impressao_pendente(ids_selecionados)
        
        if ids_em_impressao:
            return {
                'valido': False,
                'mensagem': f'Os seguintes itens já estão em impressão pendente e não podem ser reimpressos até serem processados: {", ".join(ids_em_impressao)}',
                'itens_conflitantes': ids_em_impressao
            }
        
        return {
            'valido': True,
            'mensagem': 'Seleção válida para impressão',
            'itens_conflitantes': []
        }
        
    except Exception as e:
        print(f"❌ Erro ao validar seleção: {e}")
        return {
            'valido': False,
            'mensagem': f'Erro ao validar seleção: {str(e)}',
            'itens_conflitantes': []
        }

def atualizar_item_impressao(id_impressao, id_solicitacao, qtd_separada, observacoes=""):
    """Atualiza item da impressão com quantidade separada"""
    try:
        sheet = get_google_sheets_connection()
        if not sheet:
            raise Exception("Não foi possível conectar com Google Sheets")
        
        itens_worksheet = sheet.worksheet("IMPRESSAO_ITENS")
        all_values = itens_worksheet.get_all_values()
        
        if len(all_values) < 2:
            return False
        
        # Encontrar a linha do item
        for i, row in enumerate(all_values[1:], start=2):
            if len(row) >= 2 and row[0] == id_impressao and row[1] == id_solicitacao:
                # Atualizar quantidade separada (coluna 12)
                itens_worksheet.update_cell(i, 13, qtd_separada)
                
                # Atualizar observações (coluna 14)
                itens_worksheet.update_cell(i, 14, observacoes)
                
                # Atualizar status do item
                if qtd_separada == 0:
                    status_item = 'Pendente'
                elif qtd_separada < int(row[7]):  # qtd_separada < quantidade
                    status_item = 'Parcial'
                else:
                    status_item = 'Separado'
                
                itens_worksheet.update_cell(i, 12, status_item)
                
                # Atualizar data de separação
                itens_worksheet.update_cell(i, 15, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                
                # Atualizar quem separou
                itens_worksheet.update_cell(i, 16, current_user.username)
                
                print(f"✅ Item {id_solicitacao} atualizado: {qtd_separada} unidades separadas")
                return True
        
        print(f"❌ Item {id_solicitacao} não encontrado na impressão {id_impressao}")
        return False
        
    except Exception as e:
        print(f"❌ Erro ao atualizar item da impressão: {e}")
        return False

def atualizar_solicitacao_apos_separacao(id_solicitacao, qtd_separada):
    """Atualiza status da solicitação na aba Solicitações após separação"""
    try:
        sheet = get_google_sheets_connection()
        if not sheet:
            raise Exception("Não foi possível conectar com Google Sheets")
        
        worksheet = sheet.get_worksheet(0)  # Aba Solicitações
        all_values = worksheet.get_all_values()
        
        if len(all_values) < 2:
            return False
        
        # Encontrar a linha da solicitação
        for i, row in enumerate(all_values[1:], start=2):
            # Procurar por ID em qualquer célula da linha
            for cell in row:
                if cell.strip() == id_solicitacao:
                    # Encontrar colunas necessárias
                    headers = all_values[0]
                    qtd_separada_col = None
                    status_col = None
                    
                    for j, header in enumerate(headers):
                        if 'qtd. separada' in header.lower() or 'qtd separada' in header.lower():
                            qtd_separada_col = j
                        elif 'status' in header.lower():
                            status_col = j
                    
                    # Atualizar quantidade separada
                    if qtd_separada_col is not None:
                        worksheet.update_cell(i, qtd_separada_col + 1, qtd_separada)
                    
                    # Atualizar status
                    if status_col is not None:
                        if qtd_separada == 0:
                            novo_status = 'Pendente'
                        elif qtd_separada < int(row[5]) if row[5].isdigit() else 0:  # qtd_separada < quantidade
                            novo_status = 'Parcial'
                        else:
                            novo_status = 'Processada'
                        
                        worksheet.update_cell(i, status_col + 1, novo_status)
                    
                    print(f"✅ Solicitação {id_solicitacao} atualizada: {qtd_separada} unidades separadas")
                    return True
        
        print(f"❌ Solicitação {id_solicitacao} não encontrada na aba Solicitações")
        return False
        
    except Exception as e:
        print(f"❌ Erro ao atualizar solicitação: {e}")
        return False

class MovimentacaoEstoque(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # entrada, saida, ajuste
    quantidade = db.Column(db.Integer, nullable=False)
    motivo = db.Column(db.String(100))
    solicitacao_id = db.Column(db.Integer, db.ForeignKey('solicitacao.id'))
    data_movimentacao = db.Column(db.DateTime, default=datetime.utcnow)
    usuario = db.Column(db.String(100))
    
    # Relacionamentos
    produto = db.relationship('Produto', backref=db.backref('movimentacoes', lazy=True))
    solicitacao = db.relationship('Solicitacao', backref=db.backref('movimentacoes', lazy=True))

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    usuario_nome = db.Column(db.String(80), nullable=False)
    acao = db.Column(db.String(50), nullable=False)  # login, logout, criar, editar, deletar, aprovar, etc.
    entidade = db.Column(db.String(50), nullable=False)  # Solicitacao, Produto, User, etc.
    entidade_id = db.Column(db.Integer, nullable=True)  # ID da entidade afetada
    detalhes = db.Column(db.Text, nullable=True)  # JSON com detalhes da operação
    ip_address = db.Column(db.String(45), nullable=True)  # Suporta IPv6
    user_agent = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), default='sucesso')  # sucesso, erro, aviso
    
    usuario = db.relationship('User', backref=db.backref('logs', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'usuario_nome': self.usuario_nome,
            'acao': self.acao,
            'entidade': self.entidade,
            'entidade_id': self.entidade_id,
            'detalhes': self.detalhes,
            'ip_address': self.ip_address,
            'status': self.status
        }

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Adicionar csrf_token ao contexto do template
@app.context_processor
def inject_csrf_token():
    from flask_wtf.csrf import generate_csrf
    return dict(csrf_token=generate_csrf)

# Classe para compatibilidade com paginação
class CompleteList:
    def __init__(self, items):
        self.items = items
        self.page = 1
        self.pages = 1
        self.per_page = len(items)
        self.total = len(items)
    
    def __iter__(self):
        return iter(self.items)
    
    def __len__(self):
        return len(self.items)

# Função para conectar com Google Sheets
@cached_function(cache_duration=30, force_refresh_interval=15)  # Cache muito curto para dados críticos
def get_google_sheets_connection():
    """Conecta com a planilha do Google Sheets"""
    try:
        print("🔌 Tentando conectar com Google Sheets...")
        
        # Configurar credenciais
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        print("📋 Carregando credenciais...")
        
        # Tentar várias formas de carregar credenciais
        creds = None
        
        # Opção 1: Ler de variável de ambiente JSON (Cloud Run)
        service_account_info = os.environ.get('GOOGLE_SERVICE_ACCOUNT_INFO')
        if service_account_info:
            import json
            print("📋 Carregando credenciais da variável de ambiente...")
            info = json.loads(service_account_info)
            creds = Credentials.from_service_account_info(info, scopes=scope)
            print("✅ Credenciais carregadas da variável de ambiente")
        
        # Opção 2: Ler de arquivo local (desenvolvimento)
        if not creds:
            credential_file = 'sistema-consulta-produtos-2c00b5872af4.json'
            if os.path.exists(credential_file):
                print(f"📋 Carregando credenciais do arquivo: {credential_file}")
                creds = Credentials.from_service_account_file(credential_file, scopes=scope)
                print("✅ Credenciais carregadas do arquivo")
            else:
                print(f"❌ Arquivo de credenciais não encontrado: {credential_file}")
                print("❌ Também não encontrou GOOGLE_SERVICE_ACCOUNT_INFO na variável de ambiente")
                return None
        
        if not creds:
            print("❌ Não foi possível carregar credenciais")
            return None
        
        print("🔐 Autorizando cliente...")
        client = gspread.authorize(creds)
        print("✅ Cliente autorizado")
        
        # Abrir planilha usando ID diretamente
        print("📊 Abrindo planilha...")
        sheet = client.open_by_key('1lh__GpPF_ZyCidLskYDf48aQEwv5Z8P2laelJN9aPuE')
        print("✅ Planilha aberta com sucesso")
        
        # Verificar abas disponíveis
        worksheets = sheet.worksheets()
        print(f"📋 Abas disponíveis: {[ws.title for ws in worksheets]}")
        
        return sheet
        
    except Exception as e:
        print(f"❌ Erro ao conectar com Google Sheets: {e}")
        print(f"❌ Tipo do erro: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return None

def criar_aba_realizar_baixa():
    """Cria a aba 'Realizar baixa' com a estrutura especificada"""
    try:
        print("🚀 CRIANDO ABA 'REALIZAR BAIXA'")
        
        sheet = get_google_sheets_connection()
        if not sheet:
            print("❌ Erro ao conectar com Google Sheets")
            return False
        
        # Verificar se a aba já existe
        try:
            existing_worksheet = sheet.worksheet("Realizar baixa")
            print("⚠️ Aba 'Realizar baixa' já existe")
            return True
        except gspread.WorksheetNotFound:
            print("📋 Aba 'Realizar baixa' não existe, criando...")
        
        # Criar nova aba
        worksheet = sheet.add_worksheet(title="Realizar baixa", rows=1000, cols=20)
        
        # Definir cabeçalhos conforme especificado
        headers = [
            "Carimbo",           # A - Data/hora da baixa
            "Cod",               # B - Código do produto
            "Data",              # C - Data da solicitação
            "Qtd",               # D - Quantidade separada
            "Responsavel",       # E - Usuário que processou
            "Solicitante",       # F - Solicitante
            "ID_IMPRESSAO"       # G - ID do romaneio para busca
        ]
        
        # Adicionar cabeçalhos
        worksheet.update('A1:G1', [headers])
        
        # Formatar cabeçalhos (negrito)
        worksheet.format('A1:G1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
        })
        
        # Ajustar largura das colunas
        worksheet.format('A:G', {
            'columnWidth': 120
        })
        
        print("✅ Aba 'Realizar baixa' criada com sucesso!")
        print(f"📋 Cabeçalhos: {headers}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar aba 'Realizar baixa': {e}")
        return False

def salvar_dados_realizar_baixa(id_romaneio, itens_processados, usuario_processamento):
    """Salva dados do processamento na aba 'Realizar baixa'"""
    try:
        print(f"🚀 SALVANDO DADOS NA ABA 'REALIZAR BAIXA'")
        print(f"📦 Romaneio: {id_romaneio}")
        print(f"📋 Itens processados: {len(itens_processados)}")
        print(f"👤 Usuário: {usuario_processamento}")
        
        sheet = get_google_sheets_connection()
        if not sheet:
            print("❌ Erro ao conectar com Google Sheets")
            return False
        
        # Verificar se a aba existe, se não existir, criar
        try:
            worksheet = sheet.worksheet("Realizar baixa")
        except gspread.WorksheetNotFound:
            print("📋 Aba 'Realizar baixa' não existe, criando...")
            if not criar_aba_realizar_baixa():
                return False
            worksheet = sheet.worksheet("Realizar baixa")
        
        # Buscar dados das solicitações para obter informações completas
        solicitacoes_worksheet = sheet.worksheet("Solicitações")
        solicitacoes_values = solicitacoes_worksheet.get_all_values()
        
        if len(solicitacoes_values) < 2:
            print("❌ Aba Solicitações vazia")
            return False
        
        # Encontrar colunas necessárias
        header_solicitacoes = solicitacoes_values[0]
        col_indices = {}
        for i, col_name in enumerate(header_solicitacoes):
            col_name_clean = col_name.strip().upper()
            print(f"   Coluna {i}: '{col_name_clean}'")
            if 'COD=' in col_name_clean or 'CODIGO' in col_name_clean:
                col_indices['codigo'] = i
            elif 'SOLICITANTE' in col_name_clean:
                col_indices['solicitante'] = i
            elif 'DATA' in col_name_clean and 'CARIMBO' not in col_name_clean:
                col_indices['data'] = i
        
        print(f"📍 Colunas encontradas: {col_indices}")
        print(f"📋 Header completo: {header_solicitacoes}")
        
        # CORREÇÃO: Buscar também na aba IMPRESSAO_ITENS para dados mais completos
        impressao_itens_worksheet = sheet.worksheet("IMPRESSAO_ITENS")
        impressao_itens_values = impressao_itens_worksheet.get_all_values()
        print(f"📊 Total de linhas na IMPRESSAO_ITENS: {len(impressao_itens_values)}")
        
        # Preparar dados para inserção
        data_processamento = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        dados_para_inserir = []
        
        for item in itens_processados:
            id_solicitacao = item.get('id_solicitacao', '')
            qtd_separada = item.get('qtd_separada', 0)
            
            print(f"🔄 Processando item: {id_solicitacao} - Qtd: {qtd_separada}")
            
            # CORREÇÃO: Buscar dados primeiro na IMPRESSAO_ITENS (mais confiável)
            codigo = ''
            solicitante = ''
            data_solicitacao = ''
            
            print(f"   🔍 Buscando dados na IMPRESSAO_ITENS para ID_SOLICITACAO: {id_solicitacao}")
            encontrado_impressao = False
            
            for row in impressao_itens_values[1:]:
                if len(row) > 1 and row[1] == id_solicitacao:  # ID_SOLICITACAO na coluna B
                    codigo = row[4] if len(row) > 4 else ''  # CODIGO na coluna E
                    solicitante = row[3] if len(row) > 3 else ''  # SOLICITANTE na coluna D
                    data_solicitacao = row[2] if len(row) > 2 else ''  # DATA na coluna C
                    print(f"   ✅ Dados encontrados na IMPRESSAO_ITENS: Cod='{codigo}', Sol='{solicitante}', Data='{data_solicitacao}'")
                    encontrado_impressao = True
                    break
            
            # Se não encontrou na IMPRESSAO_ITENS, buscar na aba Solicitações
            if not encontrado_impressao:
                print(f"   🔄 Buscando dados na aba Solicitações para ID_SOLICITACAO: {id_solicitacao}")
                encontrado_solicitacoes = False
                
                for i, row in enumerate(solicitacoes_values[1:], start=2):
                    if len(row) > 15 and row[15] == id_solicitacao:  # ID_SOLICITACAO na coluna P
                        print(f"   ✅ Solicitação encontrada na linha {i}")
                        print(f"   📋 Dados da linha: {row[:5]}...")
                        
                        codigo = row[col_indices['codigo']] if 'codigo' in col_indices and len(row) > col_indices['codigo'] else ''
                        solicitante = row[col_indices['solicitante']] if 'solicitante' in col_indices and len(row) > col_indices['solicitante'] else ''
                        data_solicitacao = row[col_indices['data']] if 'data' in col_indices and len(row) > col_indices['data'] else ''
                        
                        print(f"   📊 Código: '{codigo}', Solicitante: '{solicitante}', Data: '{data_solicitacao}'")
                        encontrado_solicitacoes = True
                        break
                
                if not encontrado_solicitacoes:
                    print(f"   ❌ Solicitação {id_solicitacao} não encontrada em nenhuma aba!")
                    # Usar dados básicos do item processado
                    codigo = item.get('codigo', '')
                    solicitante = item.get('solicitante', '')
                    data_solicitacao = item.get('data', '')
            
            # Adicionar linha de dados
            linha_dados = [
                data_processamento,    # A - Carimbo
                codigo,               # B - Cod
                data_solicitacao,     # C - Data
                str(qtd_separada),    # D - Qtd
                usuario_processamento, # E - Responsavel
                solicitante,          # F - Solicitante
                id_romaneio           # G - ID_IMPRESSAO
            ]
            
            dados_para_inserir.append(linha_dados)
            print(f"   ✅ Dados preparados: {linha_dados}")
        
        # Inserir dados na aba
        if dados_para_inserir:
            # Encontrar próxima linha vazia
            all_values = worksheet.get_all_values()
            proxima_linha = len(all_values) + 1
            
            # Inserir dados
            range_start = f'A{proxima_linha}'
            range_end = f'G{proxima_linha + len(dados_para_inserir) - 1}'
            worksheet.update(f'{range_start}:{range_end}', dados_para_inserir)
            
            print(f"✅ {len(dados_para_inserir)} registros salvos na aba 'Realizar baixa'")
            print(f"📍 Range: {range_start}:{range_end}")
            return True
        else:
            print("⚠️ Nenhum dado para inserir na aba 'Realizar baixa'")
            return False
        
    except Exception as e:
        print(f"❌ Erro ao salvar dados na aba 'Realizar baixa': {e}")
        return False

# Função para consultar planilha do Google Sheets em tempo real
@cached_function(cache_duration=30, force_refresh_interval=15)  # Cache curto para dados que mudam frequentemente
def get_google_sheets_data():
    """Consulta dados da planilha do Google Sheets em tempo real usando API"""
    try:
        # Conectar com Google Sheets usando API
        sheet = get_google_sheets_connection()
        if not sheet:
            print("❌ Não foi possível conectar com Google Sheets API")
            return None
        
        # Acessar a primeira aba (índice 0) - Solicitações
        worksheet = sheet.get_worksheet(0)
        
        # Obter todos os valores da planilha
        print("📥 Consultando planilha via API...")
        all_values = worksheet.get_all_values()
        
        if not all_values:
            print("❌ Planilha está vazia")
            return None
        
        # Converter para DataFrame
        df = pd.DataFrame(all_values[1:], columns=all_values[0])  # Primeira linha como cabeçalho
        
        # Filtrar apenas linhas que têm dados reais (não vazias)
        df = df.dropna(how='all')  # Remove linhas completamente vazias
        # Filtrar apenas linhas que têm código E solicitante (dados reais)
        df = df[
            df['Código'].notna() & (df['Código'] != '') & 
            df['Solicitante'].notna() & (df['Solicitante'] != '')
        ]
        
        # Verificar se o DataFrame não está vazio
        if df.empty:
            print("❌ Planilha está vazia após filtrar dados válidos")
            return None
        
        print(f"✅ Dados obtidos via API: {len(df)} registros")
        return df
        
    except Exception as e:
        print(f"❌ Erro ao consultar planilha via API: {e}")
        return None

# Função para buscar dados da matriz diretamente do Google Sheets
def get_matriz_data_from_sheets():
    """Busca dados da aba MATRIZ_IMPORTADA diretamente do Google Sheets"""
    try:
        # Conectar com Google Sheets
        sheet = get_google_sheets_connection()
        if not sheet:
            print("❌ Não foi possível conectar com Google Sheets")
            return {}
        
        # Acessar a aba MATRIZ_IMPORTADA (índice 5)
        try:
            worksheet = sheet.get_worksheet(5)  # Sexta aba
        except gspread.WorksheetNotFound:
            print("❌ Aba 'MATRIZ_IMPORTADA' não encontrada")
            return {}
        
        # Obter todos os valores da planilha
        print("📥 Consultando dados da aba MATRIZ_IMPORTADA...")
        all_values = worksheet.get_all_values()
        
        if not all_values or len(all_values) < 2:
            print("❌ Aba MATRIZ_IMPORTADA está vazia")
            return {}
        
        # Converter para DataFrame
        df = pd.DataFrame(all_values[1:], columns=all_values[0])
        
        # Filtrar apenas linhas com dados válidos
        df = df.dropna(how='all')
        # Verificar se a coluna COD existe
        if 'COD' in df.columns:
            df = df[df['COD'].notna() & (df['COD'] != '')]
        else:
            print("⚠️ Coluna 'COD' não encontrada. Verificando colunas disponíveis...")
            print(f"Colunas encontradas: {list(df.columns)}")
            # Tentar encontrar coluna similar
            cod_columns = [col for col in df.columns if 'cod' in col.lower()]
            if cod_columns:
                cod_col = cod_columns[0]
                print(f"Usando coluna '{cod_col}' como código")
                df = df[df[cod_col].notna() & (df[cod_col] != '')]
            else:
                print("❌ Nenhuma coluna de código encontrada")
                return {}
        
        if df.empty:
            print("❌ Nenhum dado válido encontrado na aba MATRIZ_IMPORTADA")
            return {}
        
        print(f"📊 Processando {len(df)} registros da aba MATRIZ_IMPORTADA...")
        
        # Criar dicionário com dados da matriz
        matriz_data = {}
        
        # Usar a coluna de código encontrada
        cod_col = 'COD' if 'COD' in df.columns else cod_columns[0] if 'cod_columns' in locals() and cod_columns else None
        
        if not cod_col:
            print("❌ Nenhuma coluna de código válida encontrada")
            return {}
        
        for index, row in df.iterrows():
            try:
                codigo = str(row.get(cod_col, '')).strip()
                if not codigo:
                    continue
                
                # Criar objeto com dados da matriz
                matriz_item = {
                    'codigo': codigo,
                    'descricao': str(row.get('DESCRICAO COMPLETA', '')).strip() if pd.notna(row.get('DESCRICAO COMPLETA', '')) else '',
                    'unidade': str(row.get('UNIDADE MEDIDA', '')).strip() if pd.notna(row.get('UNIDADE MEDIDA', '')) else '',
                    'locacao_matriz': str(row.get('LOCACAO', '')).strip() if pd.notna(row.get('LOCACAO', '')) else '',
                    'saldo_estoque': 0,
                    'media_mensal': 0.0
                }
                
                # Processar saldo de estoque
                try:
                    saldo_str = str(row.get('SALDO ESTOQUE', '')).strip()
                    if saldo_str and saldo_str != '':
                        # Converter vírgula para ponto (formato brasileiro)
                        saldo_str = saldo_str.replace(',', '.')
                        matriz_item['saldo_estoque'] = int(float(saldo_str))
                    else:
                        matriz_item['saldo_estoque'] = 0
                except (ValueError, TypeError):
                    matriz_item['saldo_estoque'] = 0
                
                # Processar média mensal
                try:
                    media_str = str(row.get('MEDIA MENSAL', '')).strip()
                    if media_str and media_str != '':
                        # Converter vírgula para ponto (formato brasileiro)
                        media_str = media_str.replace(',', '.')
                        media_original = float(media_str)
                        # Dividir por 2 e arredondar para cima
                        matriz_item['media_mensal'] = math.ceil(media_original / 2)
                    else:
                        matriz_item['media_mensal'] = 0
                except (ValueError, TypeError):
                    matriz_item['media_mensal'] = 0
                
                # Adicionar ao dicionário
                matriz_data[codigo] = matriz_item
                
            except Exception as e:
                print(f"❌ Erro ao processar linha {index + 2}: {e}")
                continue
        
        print(f"✅ {len(matriz_data)} registros da matriz carregados do Google Sheets!")
        return matriz_data
        
    except Exception as e:
        print(f"❌ Erro ao buscar dados da aba MATRIZ_IMPORTADA: {e}")
        return {}

# Função para salvar log na planilha do Google Sheets
def save_log_to_sheets(acao, entidade, entidade_id=None, detalhes=None, status='sucesso'):
    """Salva log diretamente na planilha do Google Sheets"""
    try:
        # Conectar com a planilha
        sheet = get_google_sheets_connection()
        if not sheet:
            print("❌ Não foi possível conectar com a planilha para salvar log")
            return False
        
        # Acessar a aba "Logs"
        try:
            logs_worksheet = sheet.worksheet("Logs")
        except gspread.WorksheetNotFound:
            # Criar aba "Logs" se não existir
            logs_worksheet = sheet.add_worksheet(title="Logs", rows=1000, cols=10)
            
            # Adicionar cabeçalhos
            headers = [
                "ID", "Data/Hora", "Usuário", "Ação", "Entidade", 
                "ID_Entidade", "Detalhes", "IP_Address", "User_Agent", "Status"
            ]
            logs_worksheet.append_row(headers)
            print("✅ Aba 'Logs' criada com cabeçalhos")
        
        # Obter próximo ID
        try:
            all_records = logs_worksheet.get_all_records()
            next_id = len(all_records) + 1
        except:
            next_id = 1
        
        # Preparar dados do log
        log_data = [
            next_id,
            datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            current_user.username if current_user.is_authenticated else 'Sistema',
            acao,
            entidade,
            entidade_id or '',
            detalhes or '',
            request.remote_addr if hasattr(request, 'remote_addr') else '',
            request.headers.get('User-Agent', '') if hasattr(request, 'headers') else '',
            status
        ]
        
        # Adicionar linha na planilha
        logs_worksheet.append_row(log_data)
        print(f"✅ Log salvo na planilha: {acao} - {entidade}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao salvar log na planilha: {e}")
        return False

# Função para ler logs da planilha do Google Sheets
def get_logs_from_sheets():
    """Lê logs da planilha do Google Sheets"""
    try:
        # Conectar com a planilha
        sheet = get_google_sheets_connection()
        if not sheet:
            print("❌ Não foi possível conectar com a planilha para ler logs")
            return []
        
        # Acessar a aba "Logs"
        try:
            logs_worksheet = sheet.worksheet("Logs")
        except gspread.WorksheetNotFound:
            print("❌ Aba 'Logs' não encontrada na planilha")
            return []
        
        # Obter todos os registros
        all_records = logs_worksheet.get_all_records()
        
        # Converter para objetos de log
        logs = []
        for record in all_records:
            if record.get('ID'):  # Pular linha de cabeçalho
                log_obj = type('Log', (), {})()
                log_obj.id = record.get('ID', '')
                log_obj.timestamp = record.get('Data/Hora', '')
                log_obj.usuario_nome = record.get('Usuário', '')
                log_obj.acao = record.get('Ação', '')
                log_obj.entidade = record.get('Entidade', '')
                log_obj.entidade_id = record.get('ID_Entidade', '')
                log_obj.detalhes = record.get('Detalhes', '')
                log_obj.ip_address = record.get('IP_Address', '')
                log_obj.user_agent = record.get('User_Agent', '')
                log_obj.status = record.get('Status', '')
                logs.append(log_obj)
        
        print(f"✅ {len(logs)} logs lidos da planilha")
        return logs
        
    except Exception as e:
        print(f"❌ Erro ao ler logs da planilha: {e}")
        return []

# Função utilitária para logging (mantida para compatibilidade)
def log_activity(acao, entidade, entidade_id=None, detalhes=None, status='sucesso'):
    """Registra uma atividade no log do sistema"""
    try:
        # Salvar na planilha do Google Sheets
        success = save_log_to_sheets(acao, entidade, entidade_id, detalhes, status)
        
        # Fallback: salvar no banco local se a planilha falhar
        if not success and current_user.is_authenticated:
            log = Log(
                usuario_id=current_user.id,
                usuario_nome=current_user.username,
                acao=acao,
                entidade=entidade,
                entidade_id=entidade_id,
                detalhes=detalhes,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                status=status
            )
            db.session.add(log)
            db.session.commit()
            print("✅ Log salvo no banco local (fallback)")
    except Exception as e:
        print(f"❌ Erro ao registrar log: {e}")
        # Não falha a operação principal se o log falhar

# Rotas principais
@app.route('/')
@login_required
def index():
    try:
        print("🚀 Iniciando carregamento do dashboard...")
        
        # Obter dados das solicitações do Google Sheets
        print("📊 Buscando dados das solicitações...")
        solicitacoes_data = get_google_sheets_data()
        
        if solicitacoes_data is None:
            print("❌ Erro: solicitacoes_data é None")
            raise Exception("Não foi possível obter dados das solicitações")
        
        if isinstance(solicitacoes_data, pd.DataFrame):
            print(f"✅ DataFrame obtido com {len(solicitacoes_data)} linhas")
            print(f"📋 Colunas disponíveis: {list(solicitacoes_data.columns)}")
            
            # Converter DataFrame para lista de dicionários
            solicitacoes_data = solicitacoes_data.to_dict('records')
            print(f"🔄 Convertido para {len(solicitacoes_data)} registros")
        else:
            print(f"✅ Lista obtida com {len(solicitacoes_data)} registros")
        
        # Contar por status com debug
        total_solicitacoes = len(solicitacoes_data)
        print(f"📊 Total de solicitações encontradas: {total_solicitacoes}")
        
        if total_solicitacoes == 0:
            print("⚠️ ATENÇÃO: Nenhuma solicitação encontrada!")
            print("🔍 Verificando se há dados na planilha...")
            # Tentar buscar dados brutos para debug
            try:
                sheet = get_google_sheets_connection()
                if sheet:
                    worksheet = sheet.get_worksheet(0)
                    raw_data = worksheet.get_all_values()
                    print(f"📋 Dados brutos da planilha: {len(raw_data)} linhas")
                    if len(raw_data) > 0:
                        print(f"📋 Primeira linha (cabeçalho): {raw_data[0]}")
                        if len(raw_data) > 1:
                            print(f"📋 Segunda linha (primeiro dado): {raw_data[1]}")
            except Exception as debug_e:
                print(f"❌ Erro no debug: {debug_e}")
        
        # Detectar status de forma mais robusta
        solicitacoes_abertas = 0
        solicitacoes_em_separacao = 0
        solicitacoes_concluidas = 0
        
        for i, s in enumerate(solicitacoes_data):
            status = str(s.get('status', '')).lower().strip()
            if i < 3:  # Log apenas os primeiros 3 para não poluir
                print(f"🔍 Registro {i+1} - Status: '{status}'")
            
            if status in ['aberta', 'aberto', 'pendente', 'nova', '']:
                solicitacoes_abertas += 1
            elif status in ['em separação', 'em_separacao', 'em separacao', 'separando', 'parcial']:
                solicitacoes_em_separacao += 1
            elif status in ['concluida', 'concluído', 'concluido', 'finalizada', 'entregue', 'concluída']:
                solicitacoes_concluidas += 1
        
        print(f"📈 Contagem por status - Abertas: {solicitacoes_abertas}, Em Separação: {solicitacoes_em_separacao}, Concluídas: {solicitacoes_concluidas}")
        
        # Obter dados da matriz
        matriz_data = get_matriz_data_from_sheets()
        total_produtos = len(matriz_data) if matriz_data else 0
        
        # Calcular solicitações de hoje (data atual)
        hoje = datetime.now().strftime('%d/%m/%Y')
        solicitacoes_hoje = 0
        total_itens_hoje = 0
        
        for s in solicitacoes_data:
            data_solicitacao = s.get('data', '')
            if data_solicitacao:
                try:
                    if isinstance(data_solicitacao, str):
                        # Tentar diferentes formatos
                        if '/' in data_solicitacao:
                            # Formato DD/MM/YYYY ou DD/MM/YYYY HH:MM
                            data_parte = data_solicitacao.split(' ')[0]  # Remove hora se existir
                            if data_parte == hoje:
                                solicitacoes_hoje += 1
                                quantidade = int(s.get('quantidade', 0))
                                total_itens_hoje += quantidade
                        elif '-' in data_solicitacao:
                            # Formato YYYY-MM-DD
                            data_obj = datetime.strptime(data_solicitacao.split(' ')[0], '%Y-%m-%d')
                            if data_obj.strftime('%d/%m/%Y') == hoje:
                                solicitacoes_hoje += 1
                                quantidade = int(s.get('quantidade', 0))
                                total_itens_hoje += quantidade
                except:
                    continue
        
        # Calcular produtos em baixo estoque (estoque < 10)
        produtos_baixo_estoque = 0
        if matriz_data:
            for produto in matriz_data:
                try:
                    estoque = int(produto.get('saldo_estoque', 0))
                    if estoque < 10:
                        produtos_baixo_estoque += 1
                except:
                    continue
        
        stats = {
            'total_solicitacoes': total_solicitacoes,
            'solicitacoes_abertas': solicitacoes_abertas,
            'solicitacoes_em_separacao': solicitacoes_em_separacao,
            'solicitacoes_concluidas': solicitacoes_concluidas,
            'total_produtos': total_produtos,
            'solicitacoes_hoje': solicitacoes_hoje,
            'produtos_baixo_estoque': produtos_baixo_estoque,
            'total_itens_hoje': total_itens_hoje,
            'ultima_atualizacao': datetime.now().strftime('%d/%m/%Y %H:%M')
        }
        
        return render_template('index.html', stats=stats)
        
    except Exception as e:
        print(f"❌ Erro ao carregar dashboard: {e}")
        # Fallback com dados básicos
        stats = {
            'total_solicitacoes': 0,
            'solicitacoes_abertas': 0,
            'solicitacoes_em_separacao': 0,
            'solicitacoes_concluidas': 0,
            'total_produtos': 0,
            'solicitacoes_hoje': 0,
            'produtos_baixo_estoque': 0,
            'total_itens_hoje': 0,
            'ultima_atualizacao': datetime.now().strftime('%d/%m/%Y %H:%M')
        }
        return render_template('index.html', stats=stats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            log_activity('login', 'User', user.id, f'Login realizado com sucesso', 'sucesso')
            return redirect(url_for('index'))
        else:
            log_activity('login', 'User', None, f'Tentativa de login falhada para usuário: {username}', 'erro')
            flash('Usuário ou senha inválidos', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    log_activity('logout', 'User', current_user.id, f'Logout realizado', 'sucesso')
    logout_user()
    return redirect(url_for('login'))

@app.route('/usuarios')
@login_required
def listar_usuarios():
    """Lista todos os usuários do sistema"""
    if not current_user.is_admin:
        flash('Apenas administradores podem acessar esta página', 'error')
        return redirect(url_for('index'))
    
    usuarios = User.query.all()
    return render_template('listar_usuarios.html', usuarios=usuarios)

@app.route('/criar-usuario', methods=['POST'])
@login_required
def criar_usuario():
    """Cria um novo usuário"""
    if not current_user.is_admin:
        flash('Apenas administradores podem criar usuários', 'error')
        return redirect(url_for('listar_usuarios'))
    
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        is_admin = request.form.get('is_admin') == '1'
        
        # Validar dados
        if not username or not email or not password:
            flash('Todos os campos são obrigatórios', 'error')
            return redirect(url_for('listar_usuarios'))
        
        if len(password) < 6:
            flash('A senha deve ter no mínimo 6 caracteres', 'error')
            return redirect(url_for('listar_usuarios'))
        
        # Verificar se usuário já existe
        if User.query.filter_by(username=username).first():
            flash('Usuário já existe', 'error')
            return redirect(url_for('listar_usuarios'))
        
        if User.query.filter_by(email=email).first():
            flash('Email já cadastrado', 'error')
            return redirect(url_for('listar_usuarios'))
        
        # Criar novo usuário
        novo_usuario = User(
            username=username,
            email=email,
            is_admin=is_admin
        )
        novo_usuario.set_password(password)
        
        db.session.add(novo_usuario)
        db.session.commit()
        
        log_activity('criar_usuario', 'User', current_user.id, f'Usuário criado: {username}', 'sucesso')
        
        flash(f'✅ Usuário {username} criado com sucesso!', 'success')
        return redirect(url_for('listar_usuarios'))
        
    except Exception as e:
        print(f"❌ Erro ao criar usuário: {e}")
        flash('Erro ao criar usuário', 'error')
        return redirect(url_for('listar_usuarios'))

@app.route('/desativar-usuario', methods=['POST'])
@login_required
def desativar_usuario():
    """Desativa ou ativa um usuário"""
    if not current_user.is_admin:
        flash('Apenas administradores podem gerenciar usuários', 'error')
        return redirect(url_for('listar_usuarios'))
    
    try:
        user_id = request.form.get('user_id')
        action = request.form.get('action')  # 'desativar' ou 'ativar'
        
        if not user_id:
            flash('ID do usuário não fornecido', 'error')
            return redirect(url_for('listar_usuarios'))
        
        usuario = User.query.get(user_id)
        
        if not usuario:
            flash('Usuário não encontrado', 'error')
            return redirect(url_for('listar_usuarios'))
        
        # Não permitir desativar a si mesmo
        if usuario.id == current_user.id and action == 'desativar':
            flash('Você não pode desativar a si mesmo', 'error')
            return redirect(url_for('listar_usuarios'))
        
        username = usuario.username
        
        # Desativar ou ativar
        if action == 'desativar':
            usuario.is_active = False
            log_activity('desativar_usuario', 'User', current_user.id, f'Usuário desativado: {username}', 'sucesso')
            flash(f'✅ Usuário {username} desativado com sucesso!', 'success')
        else:
            usuario.is_active = True
            log_activity('ativar_usuario', 'User', current_user.id, f'Usuário ativado: {username}', 'sucesso')
            flash(f'✅ Usuário {username} ativado com sucesso!', 'success')
        
        db.session.commit()
        return redirect(url_for('listar_usuarios'))
        
    except Exception as e:
        print(f"❌ Erro ao gerenciar usuário: {e}")
        flash('Erro ao gerenciar usuário', 'error')
        return redirect(url_for('listar_usuarios'))

@app.route('/editar-email-usuario', methods=['POST'])
@login_required
def editar_email_usuario():
    """Permite ao admin alterar o email de qualquer usuário"""
    print("📧 Requisição de editar email recebida")
    if not current_user.is_admin:
        flash('Apenas administradores podem editar emails', 'error')
        return redirect(url_for('listar_usuarios'))
    
    try:
        user_id = request.form.get('user_id')
        novo_email = request.form.get('novo_email')
        
        print(f"📧 user_id: {user_id}, novo_email: {novo_email}")
        
        if not user_id or not novo_email:
            flash('Dados incompletos', 'error')
            return redirect(url_for('listar_usuarios'))
        
        usuario = User.query.get(user_id)
        if not usuario:
            flash('Usuário não encontrado', 'error')
            return redirect(url_for('listar_usuarios'))
        
        # Verificar se email já existe em outro usuário
        if User.query.filter(User.email == novo_email, User.id != user_id).first():
            flash('Este email já está em uso por outro usuário', 'error')
            return redirect(url_for('listar_usuarios'))
        
        email_antigo = usuario.email
        usuario.email = novo_email
        db.session.commit()
        
        log_activity('editar_email_usuario', 'User', current_user.id, 
                    f'Email do usuário {usuario.username} alterado de {email_antigo} para {novo_email}', 'sucesso')
        
        print(f"✅ Email alterado com sucesso!")
        flash(f'✅ Email do usuário {usuario.username} alterado com sucesso!', 'success')
        return redirect(url_for('listar_usuarios'))
        
    except Exception as e:
        print(f"❌ Erro ao editar email: {e}")
        import traceback
        traceback.print_exc()
        flash('Erro ao editar email', 'error')
        return redirect(url_for('listar_usuarios'))

@app.route('/alterar-senha-usuario-admin', methods=['POST'])
@login_required
def alterar_senha_usuario_admin():
    """Permite ao admin alterar a senha de qualquer usuário"""
    print("🔑 Requisição de alterar senha recebida")
    if not current_user.is_admin:
        flash('Apenas administradores podem alterar senhas', 'error')
        return redirect(url_for('listar_usuarios'))
    
    try:
        user_id = request.form.get('user_id')
        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')
        
        print(f"🔑 user_id: {user_id}, senhas recebidas: {bool(nova_senha)}")
        
        if not user_id or not nova_senha or not confirmar_senha:
            flash('Dados incompletos', 'error')
            return redirect(url_for('listar_usuarios'))
        
        if nova_senha != confirmar_senha:
            flash('As senhas não coincidem', 'error')
            return redirect(url_for('listar_usuarios'))
        
        if len(nova_senha) < 6:
            flash('A senha deve ter no mínimo 6 caracteres', 'error')
            return redirect(url_for('listar_usuarios'))
        
        usuario = User.query.get(user_id)
        if not usuario:
            flash('Usuário não encontrado', 'error')
            return redirect(url_for('listar_usuarios'))
        
        username = usuario.username
        usuario.set_password(nova_senha)
        db.session.commit()
        
        log_activity('alterar_senha_admin', 'User', current_user.id, 
                    f'Senha do usuário {username} alterada pelo admin', 'sucesso')
        
        print(f"✅ Senha alterada com sucesso!")
        flash(f'✅ Senha do usuário {username} alterada com sucesso!', 'success')
        return redirect(url_for('listar_usuarios'))
        
    except Exception as e:
        print(f"❌ Erro ao alterar senha: {e}")
        import traceback
        traceback.print_exc()
        flash('Erro ao alterar senha', 'error')
        return redirect(url_for('listar_usuarios'))

@app.route('/alterar-senha', methods=['GET', 'POST'])
@login_required
def alterar_senha():
    """Permite ao usuário alterar sua própria senha"""
    print(f"🔄 Requisição recebida: {request.method}")
    if request.method == 'POST':
        try:
            print(f"📋 Dados recebidos do formulário")
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            print(f"👤 Usuário: {current_user.username}")
            print(f"🔑 Senha atual recebida: {'Sim' if current_password else 'Não'}")
            print(f"🔑 Nova senha recebida: {'Sim' if new_password else 'Não'}")
            
            # Validar senha atual
            print(f"🔍 Verificando senha atual...")
            if not current_user.check_password(current_password):
                print(f"❌ Senha atual incorreta!")
                flash('❌ Senha atual incorreta!', 'error')
                return render_template('alterar_senha.html')
            print(f"✅ Senha atual correta!")
            
            # Validar nova senha
            if len(new_password) < 6:
                print(f"❌ Senha muito curta!")
                flash('❌ A nova senha deve ter no mínimo 6 caracteres!', 'error')
                return render_template('alterar_senha.html')
            
            # Verificar se senhas coincidem
            if new_password != confirm_password:
                print(f"❌ Senhas não coincidem!")
                flash('❌ As senhas não coincidem!', 'error')
                return render_template('alterar_senha.html')
            
            # Verificar se nova senha é diferente da atual
            if current_user.check_password(new_password):
                print(f"❌ Nova senha igual à atual!")
                flash('❌ A nova senha deve ser diferente da senha atual!', 'error')
                return render_template('alterar_senha.html')
            
            # Alterar senha
            print(f"💾 Alterando senha no banco de dados...")
            current_user.set_password(new_password)
            db.session.commit()
            print(f"✅ Senha alterada com sucesso!")
            
            # Registrar no log
            log_activity('alterar_senha', 'User', current_user.id, f'Senha alterada com sucesso', 'sucesso')
            
            flash('✅ Senha alterada com sucesso!', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            print(f"❌ Erro ao alterar senha: {e}")
            flash('❌ Erro ao alterar senha. Tente novamente.', 'error')
            return render_template('alterar_senha.html')
    
    return render_template('alterar_senha.html')

@app.route('/api/pdf-status/<id_impressao>')
@login_required
def verificar_status_pdf(id_impressao):
    """Verifica o status da geração do PDF"""
    try:
        status = pdf_generation_status.get(id_impressao, {
            'status': 'nao_iniciado',
            'progresso': 0
        })
        
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/limpar-cache')
@login_required
def limpar_cache():
    """Limpa o cache do sistema"""
    try:
        cache_manager.clear()
        pdf_generation_status.clear()
        return jsonify({
            'success': True,
            'message': 'Cache limpo com sucesso'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/invalidar-cache-sheets')
@login_required
def invalidar_cache_sheets():
    """Invalida apenas o cache do Google Sheets (mantém outros caches)"""
    try:
        cache_manager.invalidate_sheets_data()
        return jsonify({
            'success': True,
            'message': 'Cache do Google Sheets invalidado com sucesso'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/forcar-atualizacao')
@login_required
def forcar_atualizacao():
    """Força atualização de todos os dados do Google Sheets"""
    try:
        cache_manager.invalidate_sheets_data()
        # Forçar refresh imediato
        cache_manager.last_sheets_update.clear()
        return jsonify({
            'success': True,
            'message': 'Atualização forçada - próximas consultas buscarão dados frescos'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# Seção de produtos removida

# Funcionalidade de criação de produtos removida

# Função para processar dados da planilha
def process_google_sheets_data(df, matriz_data=None):
    """Processa dados da planilha do Google Sheets"""
    solicitacoes_list = []
    
    # Buscar dados da matriz do Google Sheets (opcional)
    print("📊 Carregando dados da matriz...")
    try:
        matriz_data = get_matriz_data_from_sheets()
        print(f"📊 Matriz carregada: {len(matriz_data)} itens")
    except Exception as e:
        print(f"⚠️ Erro ao carregar matriz: {e}")
        print("📊 Continuando sem dados da matriz...")
        matriz_data = {}
    
    for index, row in df.iterrows():
        try:
            # Criar objeto Solicitacao a partir da planilha
            solicitacao = type('Solicitacao', (), {})()
            solicitacao.id = index + 1
            
            # Processar data com tratamento de erro
            try:
                if 'Data' in row and pd.notna(row.get('Data', '')) and str(row.get('Data', '')).strip() != '':
                    solicitacao.data = pd.to_datetime(row.get('Data', ''), errors='coerce')
                    # Se a conversão resultou em NaT, usar data atual
                    if pd.isna(solicitacao.data):
                        solicitacao.data = datetime.now()
                else:
                    solicitacao.data = datetime.now()
            except:
                solicitacao.data = datetime.now()
            
            # Processar campos de texto
            solicitacao.solicitante = str(row.get('Solicitante', '')).strip() if pd.notna(row.get('Solicitante', '')) else ''
            solicitacao.codigo = str(row.get('Código', '')).strip() if pd.notna(row.get('Código', '')) else ''
            solicitacao.descricao = str(row.get('Descrição', '')).strip() if pd.notna(row.get('Descrição', '')) else ''
            solicitacao.unidade = str(row.get('Unidade', '')).strip() if pd.notna(row.get('Unidade', '')) else ''
            
            # Processar quantidade com tratamento de erro
            try:
                qtd_str = str(row.get('Quantidade', '')).strip()
                solicitacao.quantidade = int(qtd_str) if qtd_str and qtd_str != '' else 0
            except (ValueError, TypeError):
                solicitacao.quantidade = 0
            
            # Processar locação
            solicitacao.locacao = str(row.get('Locação', '')).strip() if pd.notna(row.get('Locação', '')) and str(row.get('Locação', '')).strip() != '' else None
            solicitacao.status = str(row.get('Status', '')).strip() if pd.notna(row.get('Status', '')) else ''
            
            # Processar quantidade separada da planilha
            try:
                qtd_sep_str = str(row.get('Qtd. Separada', '')).strip()
                solicitacao.qtd_separada = int(qtd_sep_str) if qtd_sep_str and qtd_sep_str != '' else 0
            except (ValueError, TypeError):
                solicitacao.qtd_separada = 0
            
            # Processar Alta Demanda
            try:
                alta_demanda_str = str(row.get('Alta Demanda', '')).strip().lower()
                solicitacao.alta_demanda = alta_demanda_str in ['sim', 's', 'yes', 'y', 'true', '1']
            except (ValueError, TypeError):
                solicitacao.alta_demanda = False
            
            # Calcular saldo baseado na quantidade solicitada e separada (nunca menor que 0)
            solicitacao.saldo = max(0, solicitacao.quantidade - solicitacao.qtd_separada)
            
            # Inicializar atributos necessários para o template
            solicitacao.saldo_estoque = 0
            solicitacao.locacao_matriz = None
            solicitacao.media_mensal = 0
            
            # Enriquecer com dados da matriz do Google Sheets
            if matriz_data and solicitacao.codigo in matriz_data:
                matriz_item = matriz_data[solicitacao.codigo]
                solicitacao.saldo_estoque = matriz_item['saldo_estoque']
                solicitacao.locacao_matriz = matriz_item['locacao_matriz']
                solicitacao.media_mensal = matriz_item['media_mensal']
            
            solicitacoes_list.append(solicitacao)
            
        except Exception as e:
            print(f"Erro ao processar linha {index}: {e}")
            continue
    
    return solicitacoes_list

# Rotas para solicitações
@app.route('/solicitacoes')
@login_required
def solicitacoes():
    status_filter = request.args.get('status', '')
    codigo_search = request.args.get('codigo', '')
    
    print(f"DEBUG: status_filter recebido: '{status_filter}' (tipo: {type(status_filter)})")
    print(f"DEBUG: codigo_search recebido: '{codigo_search}' (tipo: {type(codigo_search)})")
    print(f"DEBUG: status_filter repr: {repr(status_filter)}")
    print(f"DEBUG: codigo_search repr: {repr(codigo_search)}")
    
    # Consultar planilha em tempo real - APENAS ONLINE
    df = get_google_sheets_data()
    
    if df is None or df.empty:
        print("❌ Não foi possível obter dados da planilha, tentando novamente...")
        # Tentar novamente com timeout maior
        try:
            import time
            time.sleep(3)  # Aguardar 3 segundos
            df = get_google_sheets_data()
        except Exception as e:
            print(f"❌ Segunda tentativa falhou: {e}")
        
        if df is None or df.empty:
            print("❌ ERRO: Não foi possível conectar com a planilha do Google Sheets")
            flash('❌ Erro: Não foi possível conectar com a planilha do Google Sheets. A conta de serviço precisa ter acesso à planilha. Verifique as permissões e tente novamente.', 'error')
            return render_template('solicitacoes.html', 
                                 solicitacoes=CompleteList([]), 
                                 codigo_search=codigo_search,
                                 contagens={'aberta': 0, 'pendente': 0, 'aprovada': 0, 'em_separacao': 0, 'entrega_parcial': 0, 'cancelada': 0, 'concluida': 0, 'total': 0})
        else:
            print("✅ Segunda tentativa bem-sucedida!")
            # Processar dados da planilha
            solicitacoes_list = process_google_sheets_data(df)
    else:
        print("✅ Dados da planilha obtidos com sucesso!")
        # Processar dados da planilha
        solicitacoes_list = process_google_sheets_data(df)
    
    # Se ainda não temos dados, criar lista vazia
    if 'solicitacoes_list' not in locals():
        solicitacoes_list = []
    
    
    print(f"DEBUG: Total de registros processados: {len(solicitacoes_list)}")
    
    # Filtrar automaticamente as concluídas, faltas e finalizadas para deixar a interface mais limpa
    solicitacoes_list = [s for s in solicitacoes_list if s.status != 'Concluida' and s.status != 'Falta' and s.status != 'Finalizado']
    print(f"DEBUG: Registros após filtrar concluídas e faltas: {len(solicitacoes_list)}")
    
    # Aplicar busca por código se especificado
    if codigo_search:
        print(f"DEBUG: Aplicando busca por código: '{codigo_search}'")
        codigo_search_clean = codigo_search.strip()
        solicitacoes_list = [s for s in solicitacoes_list if codigo_search_clean in str(s.codigo)]
        print(f"DEBUG: Total de registros após busca por código: {len(solicitacoes_list)}")
    
    # Ordenar por data crescente (mais antigo primeiro)
    solicitacoes_list.sort(key=lambda x: x.data, reverse=False)
    
    # Debug: verificar status dos primeiros registros
    if solicitacoes_list:
        print(f"DEBUG: Primeiros 5 status encontrados:")
        for i, sol in enumerate(solicitacoes_list[:5]):
            print(f"  {i+1}. ID: {sol.id}, Status: '{sol.status}' (repr: {repr(sol.status)})")
    
    # Calcular contagens por status
    status_counts = {}
    for solicitacao in solicitacoes_list:
        status = solicitacao.status
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # Contagens específicas para os botões
    contagens = {
        'aberta': status_counts.get('ABERTA', 0) + status_counts.get('Aberta', 0),
        'pendente': status_counts.get('pendente', 0) + status_counts.get('Pendente', 0),
        'aprovada': status_counts.get('aprovada', 0) + status_counts.get('Aprovada', 0),
        'em_separacao': status_counts.get('Em Separação', 0) + status_counts.get('em separação', 0),
        'entrega_parcial': status_counts.get('Entrega Parcial', 0) + status_counts.get('entrega parcial', 0),
        'cancelada': status_counts.get('cancelada', 0) + status_counts.get('Cancelada', 0),
        'concluida': status_counts.get('Concluida', 0) + status_counts.get('concluida', 0),
        'total': len(solicitacoes_list)
    }
    
    print(f"DEBUG: Contagens por status: {contagens}")
    
    solicitacoes = CompleteList(solicitacoes_list)
    
    print(f"DEBUG: Enviando para template - total: {solicitacoes.total}, items: {len(solicitacoes.items)}")
    print(f"DEBUG: status_filter para template: '{status_filter}' (repr: {repr(status_filter)})")
    
    # Adicionar headers para evitar cache
    response = make_response(render_template('solicitacoes.html', 
                         solicitacoes=solicitacoes, 
                         codigo_search=codigo_search,
                         contagens=contagens))
    
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

# Função otimizada para atualizar status
def atualizar_status_para_em_separacao_otimizada(codigos):
    """Atualiza status para 'Em Separação' - VERSÃO OTIMIZADA"""
    try:
        # Conectar com Google Sheets
        sheet = get_google_sheets_connection()
        if not sheet:
            print("❌ Não foi possível conectar com Google Sheets")
            return False
        
        # Acessar a aba "Solicitações"
        worksheet = sheet.get_worksheet(0)
        
        # Obter todos os dados uma única vez
        all_values = worksheet.get_all_values()
        if not all_values or len(all_values) < 2:
            print("❌ Planilha está vazia")
            return False
        
        # Encontrar colunas
        headers = all_values[0]
        codigo_col = None
        status_col = None
        
        for i, header in enumerate(headers):
            header_lower = header.lower().strip()
            if 'código' in header_lower or 'codigo' in header_lower:
                codigo_col = i
            elif 'status' in header_lower and status_col is None:
                status_col = i
        
        if codigo_col is None or status_col is None:
            print(f"❌ Colunas necessárias não encontradas - Código: {codigo_col}, Status: {status_col}")
            return False
        
        print(f"📊 Atualizando status para {len(codigos)} códigos...")
        
        # Preparar atualizações em lote
        updates = []
        codigos_encontrados = set()
        
        # Buscar linhas que precisam ser atualizadas
        for row_num, row in enumerate(all_values[1:], start=2):
            if len(row) > max(codigo_col, status_col):
                codigo_atual = str(row[codigo_col]).strip()
                status_atual = row[status_col].strip() if len(row) > status_col else ''
                
                # Verificar se este código está na lista e pode ser atualizado
                if codigo_atual in codigos and status_atual not in ['Concluído', 'Excedido', 'Em Separação']:
                    status_cell_address = f"{chr(65 + status_col)}{row_num}"
                    updates.append({
                        'range': status_cell_address,
                        'values': [['Em Separação']]
                    })
                    codigos_encontrados.add(codigo_atual)
                    print(f"   ✅ Código {codigo_atual} será atualizado (linha {row_num}) - Status atual: '{status_atual}'")
                elif codigo_atual in codigos:
                    print(f"   ⚠️ Código {codigo_atual} já tem status '{status_atual}' - não será atualizado")
        
        # Executar atualizações em lote se houver alguma
        if updates:
            try:
                worksheet.batch_update(updates)
                print(f"✅ {len(updates)} status atualizados com sucesso!")
                return True
            except Exception as e:
                print(f"❌ Erro ao executar atualizações em lote: {e}")
                return False
        else:
            print("⚠️ Nenhuma linha encontrada para atualizar")
            return True
        
    except Exception as e:
        print(f"❌ Erro ao atualizar status: {e}")
        return False

# Rota para impressão de solicitações
def atualizar_status_para_em_separacao(codigos):
    """Atualiza status para 'Em Separação' quando solicitações são impressas"""
    try:
        # Conectar com Google Sheets
        sheet = get_google_sheets_connection()
        if not sheet:
            print("❌ Não foi possível conectar com Google Sheets")
            return False
        
        # Acessar a aba "Solicitações"
        worksheet = sheet.get_worksheet(0)
        
        # Obter todos os dados
        all_values = worksheet.get_all_values()
        if not all_values:
            print("❌ Planilha está vazia")
            return False
        
        # Encontrar colunas
        headers = all_values[0]
        codigo_col = None
        status_col = None
        
        for i, header in enumerate(headers):
            header_lower = header.lower().strip()
            if 'código' in header_lower or 'codigo' in header_lower:
                codigo_col = i
            elif 'status' in header_lower and status_col is None:
                status_col = i
        
        if codigo_col is None or status_col is None:
            print("❌ Colunas necessárias não encontradas")
            return False
        
        # Atualizar status para cada código
        for codigo in codigos:
            for row_num, row in enumerate(all_values[1:], start=2):
                if len(row) > codigo_col and str(row[codigo_col]).strip() == str(codigo).strip():
                    # Verificar se não está já concluído ou excedido
                    if len(row) > status_col:
                        status_atual = row[status_col].strip()
                        if status_atual not in ['Concluído', 'Excedido']:
                            # Atualizar para "Em Separação"
                            status_cell_address = f"{chr(65 + status_col)}{row_num}"
                            worksheet.update(status_cell_address, [['Em Separação']])
                            print(f"✅ Status atualizado para 'Em Separação' - Código {codigo}")
                    break
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao atualizar status para Em Separação: {e}")
        return False

@app.route('/solicitacoes/falta')
@login_required
def solicitacoes_falta():
    """Página de solicitações com status FALTA"""
    codigo_search = request.args.get('codigo', '')
    
    print(f"🔍 Página de FALTAS - Busca por código: '{codigo_search}'")
    
    # Consultar planilha em tempo real
    df = get_google_sheets_data()
    
    if df is None or df.empty:
        print("❌ Erro: Não foi possível conectar com Google Sheets")
        flash('❌ Erro: Não foi possível conectar com a planilha do Google Sheets. A conta de serviço precisa ter acesso à planilha. Verifique as permissões e tente novamente.', 'error')
        return render_template('solicitacoes_falta.html', 
                             solicitacoes=CompleteList([]), 
                             codigo_search=codigo_search,
                             contagens={'falta': 0, 'total': 0})
    
    # Processar dados da planilha
    solicitacoes_list = process_google_sheets_data(df)
    
    # Filtrar APENAS itens com status "Falta"
    solicitacoes_list = [s for s in solicitacoes_list if s.status == 'Falta']
    print(f"📊 Total de itens com status FALTA: {len(solicitacoes_list)}")
    
    # Aplicar busca por código se especificado
    if codigo_search:
        codigo_search_clean = codigo_search.strip()
        solicitacoes_list = [s for s in solicitacoes_list if str(s.codigo).strip() == codigo_search_clean]
        print(f"📊 Após filtro por código: {len(solicitacoes_list)} registros")
    
    # Criar objeto CompleteList
    solicitacoes_completas = CompleteList(solicitacoes_list)
    
    # Contagens
    contagens = {
        'falta': len(solicitacoes_list),
        'total': len(solicitacoes_list)
    }
    
    return render_template('solicitacoes_falta.html', 
                         solicitacoes=solicitacoes_completas,
                         codigo_search=codigo_search,
                         contagens=contagens)

@app.route('/solicitacoes/print')
@login_required
def print_solicitacoes():
    """Página de impressão de solicitações"""
    status_filter = request.args.get('status', '')
    codigo_search = request.args.get('codigo', '')
    
    print(f"DEBUG PRINT: status_filter: '{status_filter}', codigo_search: '{codigo_search}'")
    
    # Consultar planilha em tempo real - APENAS ONLINE
    df = get_google_sheets_data()
    
    if df is None or df.empty:
        print("❌ ERRO: Não foi possível conectar com a planilha do Google Sheets")
        flash('❌ Erro: Não foi possível conectar com a planilha do Google Sheets. Verifique sua conexão com a internet e tente novamente.', 'error')
        return render_template('print_solicitacoes.html', 
                             solicitacoes=[],
                             status_filter=status_filter,
                             codigo_search=codigo_search)
    
    # Processar dados da planilha
    solicitacoes_list = process_google_sheets_data(df)
    
    # Debug: mostrar status únicos encontrados
    status_unicos = list(set([s.status for s in solicitacoes_list]))
    print(f"DEBUG PRINT: Status únicos encontrados: {status_unicos}")
    
    # Filtrar automaticamente as concluídas e finalizadas para deixar a interface mais limpa
    solicitacoes_list = [s for s in solicitacoes_list if s.status != 'Concluida' and s.status != 'Finalizado']
    print(f"DEBUG PRINT: Total de registros após filtrar concluídas: {len(solicitacoes_list)}")
    
    # Aplicar filtro por status se especificado
    if status_filter:
        print(f"DEBUG PRINT: Aplicando filtro para status: '{status_filter}'")
        # Fazer comparação flexível para diferentes variações de status
        if status_filter.upper() == 'ABERTA':
            solicitacoes_list = [s for s in solicitacoes_list if s.status.upper() == 'ABERTA' or s.status == 'Aberta']
        else:
            solicitacoes_list = [s for s in solicitacoes_list if s.status == status_filter]
        print(f"DEBUG PRINT: Total de registros após filtro: {len(solicitacoes_list)}")
    
    # Aplicar busca por código se especificado
    if codigo_search:
        print(f"DEBUG PRINT: Aplicando busca por código: '{codigo_search}'")
        codigo_search_clean = codigo_search.strip()
        solicitacoes_list = [s for s in solicitacoes_list if codigo_search_clean in str(s.codigo)]
    
    # Ordenar por data decrescente
    solicitacoes_list.sort(key=lambda x: x.data, reverse=True)
    
    # Atualizar status para "Em Separação" quando impresso
    codigos_para_imprimir = [s.codigo for s in solicitacoes_list if s.status in ['Aberta', 'pendente', 'aprovada']]
    if codigos_para_imprimir:
        print(f"🖨️ Atualizando status para 'Em Separação' para códigos: {codigos_para_imprimir}")
        atualizar_status_para_em_separacao(codigos_para_imprimir)
    
    print(f"DEBUG PRINT: Total de registros para impressão: {len(solicitacoes_list)}")
    
    return render_template('print_solicitacoes.html', 
                         solicitacoes=solicitacoes_list,
                         status_filter=status_filter,
                         codigo_search=codigo_search)

# Rota de teste simples
@app.route('/simple-solicitacoes')
@login_required
def simple_solicitacoes():
    status_filter = request.args.get('status', '')
    
    print(f"DEBUG SIMPLE: status_filter recebido: '{status_filter}'")
    
    query = Solicitacao.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    solicitacoes_list = query.order_by(Solicitacao.data.asc()).all()
    
    # Criar objeto compatível
    
    solicitacoes = CompleteList(solicitacoes_list)
    
    print(f"DEBUG SIMPLE: Enviando para template - total: {solicitacoes.total}")
    
    return render_template('simple_solicitacoes.html', 
                         solicitacoes=solicitacoes, 
                         status_filter=status_filter)

# Rota para sincronizar dados da matriz
@app.route('/sincronizar-matriz')
@login_required
def sincronizar_matriz():
    """Sincroniza dados da aba MATRIZ_IMPORTADA do Google Sheets"""
    print("🔄 Sincronizando dados da aba MATRIZ_IMPORTADA...")
    
    # Buscar dados da matriz do Google Sheets
    matriz_data = get_matriz_data_from_sheets()
    
    # Mensagem de sucesso removida - a barra de progresso já indica a conclusão
    
    return redirect(url_for('solicitacoes'))

@app.route('/formulario-impressao')
@login_required
def formulario_impressao():
    """Exibe formulário de impressão para separação física"""
    try:
        # Obter IDs selecionados da query string
        ids_selecionados = request.args.get('ids', '').split(',')
        ids_selecionados = [id.strip() for id in ids_selecionados if id.strip()]
        
        # Verificar se veio da página de faltas
        origem = request.args.get('origem', '')
        tipo_romaneio = 'Itens em Falta' if origem == 'falta' else 'Romaneio de Separação'
        
        if not ids_selecionados:
            flash('Nenhuma solicitação selecionada', 'warning')
            return redirect(url_for('solicitacoes'))
        
        # Validar se a seleção pode ser impressa
        validacao = validar_selecao_impressao(ids_selecionados)
        if not validacao['valido']:
            flash(f'❌ {validacao["mensagem"]}', 'error')
            return redirect(url_for('solicitacoes'))
        
        # Buscar dados das solicitações selecionadas do Google Sheets
        solicitacoes_selecionadas = buscar_solicitacoes_selecionadas(ids_selecionados)
        
        if not solicitacoes_selecionadas:
            flash('Nenhuma solicitação encontrada', 'error')
            return redirect(url_for('solicitacoes'))
        
        # Criar impressão no sistema de controle
        id_impressao = criar_impressao(
            usuario=current_user.username,
            solicitacoes_selecionadas=solicitacoes_selecionadas,
            observacoes=""  # Deixar vazio - observações serão preenchidas no processamento
        )
        
        # Guardar tipo_romaneio em cache para usar na geração do PDF
        if 'romaneio_info' not in globals():
            globals()['romaneio_info'] = {}
        globals()['romaneio_info'][id_impressao] = tipo_romaneio
        
        if not id_impressao:
            flash('Erro ao criar controle de impressão', 'error')
            return redirect(url_for('solicitacoes'))
        
        return render_template('formulario_impressao.html', 
                             solicitacoes=solicitacoes_selecionadas,
                             ids_selecionados=ids_selecionados,
                             id_impressao=id_impressao,
                             tipo_romaneio=tipo_romaneio,
                             origem=origem)
        
    except Exception as e:
        print(f"❌ Erro ao carregar formulário de impressão: {e}")
        flash('Erro ao carregar formulário de impressão', 'error')
        return redirect(url_for('solicitacoes'))

@app.route('/alterar-status-impressao', methods=['POST'])
@login_required
def alterar_status_impressao():
    """Altera status das solicitações selecionadas para 'Em Separação' após impressão - Apenas Google Sheets"""
    try:
        print("🖨️ Alterando status das solicitações selecionadas para 'Em Separação' após impressão...")
        
        # Obter dados da requisição
        data = request.get_json()
        ids_selecionados = data.get('ids_selecionados', [])
        
        if not ids_selecionados:
            return jsonify({
                'success': False,
                'message': 'Nenhuma solicitação selecionada',
                'count': 0
            })
        
        print(f"📋 IDs selecionados: {ids_selecionados}")
        
        # Atualizar apenas as solicitações selecionadas no Google Sheets
        count = atualizar_status_google_sheets_selecionadas(ids_selecionados)
        
        if count == 0:
            return jsonify({
                'success': True, 
                'message': 'Nenhuma solicitação encontrada para alterar status',
                'count': 0
            })
        
        return jsonify({
            'success': True,
            'message': f'{count} solicitações selecionadas alteradas para "Em Separação" no Google Sheets',
            'count': count
        })
        
    except Exception as e:
        print(f"❌ Erro ao alterar status das solicitações: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao alterar status: {str(e)}',
            'count': 0
        }), 500

@app.route('/controle-impressoes')
@login_required
def controle_impressoes():
    """Página de controle de impressões"""
    try:
        # Obter parâmetros de filtro
        status_filtro = request.args.get('status', '')
        usuario_filtro = request.args.get('usuario', '')
        data_filtro = request.args.get('data', '')
        id_filtro = request.args.get('id', '')
        
        # Buscar todas as impressões (não apenas pendentes)
        todas_impressoes = buscar_todas_impressoes()
        
        # Aplicar filtros
        impressoes_filtradas = todas_impressoes
        
        if status_filtro:
            impressoes_filtradas = [imp for imp in impressoes_filtradas if imp.get('status', '').lower() == status_filtro.lower()]
        
        if usuario_filtro:
            impressoes_filtradas = [imp for imp in impressoes_filtradas if usuario_filtro.lower() in imp.get('usuario_impressao', '').lower()]
        
        if data_filtro:
            impressoes_filtradas = [imp for imp in impressoes_filtradas if data_filtro in imp.get('data_impressao', '')]
        
        if id_filtro:
            impressoes_filtradas = [imp for imp in impressoes_filtradas if id_filtro.lower() in imp.get('id_impressao', '').lower()]
        
        # Adicionar informações sobre PDFs para cada impressão
        for impressao in impressoes_filtradas:
            pdf_info = verificar_pdf_romaneio(impressao.get('id_impressao', ''))
            impressao['pdf_info'] = pdf_info
        
        return render_template('controle_impressoes.html', 
                             impressoes=impressoes_filtradas,
                             filtros={
                                 'status': status_filtro,
                                 'usuario': usuario_filtro,
                                 'data': data_filtro,
                                 'id': id_filtro
                             })
        
    except Exception as e:
        print(f"❌ Erro ao carregar controle de impressões: {e}")
        flash('Erro ao carregar controle de impressões', 'error')
        return redirect(url_for('solicitacoes'))

@app.route('/imprimir-romaneio/<id_impressao>')
@login_required
def imprimir_romaneio(id_impressao):
    """Imprime o PDF salvo do romaneio diretamente da pasta"""
    try:
        import os
        from flask import send_file
        
        print(f"🖨️ Buscando PDF do romaneio: {id_impressao}")
        
        # Caminho da pasta onde os PDFs são salvos
        pasta_pdfs = 'Romaneios_Separacao'
        
        # Nome do arquivo PDF original
        nome_arquivo_original = f"{id_impressao}.pdf"
        caminho_original = os.path.join(pasta_pdfs, nome_arquivo_original)
        
        # Nome do arquivo PDF de cópia (se existir)
        nome_arquivo_copia = f"{id_impressao}_Copia.pdf"
        caminho_copia = os.path.join(pasta_pdfs, nome_arquivo_copia)
        
        # Priorizar o PDF original, mas aceitar cópia se necessário
        if os.path.exists(caminho_original):
            print(f"✅ PDF original encontrado: {caminho_original}")
            return send_file(
                caminho_original,
                as_attachment=False,  # Abrir no navegador em vez de baixar
                mimetype='application/pdf',
                download_name=nome_arquivo_original
            )
        elif os.path.exists(caminho_copia):
            print(f"✅ PDF de cópia encontrado: {caminho_copia}")
            return send_file(
                caminho_copia,
                as_attachment=False,  # Abrir no navegador em vez de baixar
                mimetype='application/pdf',
                download_name=nome_arquivo_copia
            )
        else:
            print(f"❌ PDF não encontrado: {caminho_original} ou {caminho_copia}")
            flash(f'PDF do romaneio {id_impressao} não encontrado', 'error')
            return redirect(url_for('controle_impressoes'))
            
    except Exception as e:
        print(f"❌ Erro ao imprimir romaneio: {e}")
        flash('Erro ao abrir PDF do romaneio', 'error')
        return redirect(url_for('controle_impressoes'))

def verificar_pdf_romaneio(id_impressao):
    """Verifica se existe PDF do romaneio e retorna informações"""
    import os
    from datetime import datetime
    
    pasta_pdfs = 'Romaneios_Separacao'
    
    # Verificar PDF original
    nome_original = f"{id_impressao}.pdf"
    caminho_original = os.path.join(pasta_pdfs, nome_original)
    
    # Verificar PDF de cópia
    nome_copia = f"{id_impressao}_Copia.pdf"
    caminho_copia = os.path.join(pasta_pdfs, nome_copia)
    
    if os.path.exists(caminho_original):
        stat = os.stat(caminho_original)
        return {
            'existe': True,
            'tipo': 'original',
            'caminho': caminho_original,
            'nome': nome_original,
            'tamanho': stat.st_size,
            'data_modificacao': datetime.fromtimestamp(stat.st_mtime)
        }
    elif os.path.exists(caminho_copia):
        stat = os.stat(caminho_copia)
        return {
            'existe': True,
            'tipo': 'copia',
            'caminho': caminho_copia,
            'nome': nome_copia,
            'tamanho': stat.st_size,
            'data_modificacao': datetime.fromtimestamp(stat.st_mtime)
        }
    else:
        return {'existe': False}

@app.route('/processar-romaneio/<id_impressao>')
@login_required
def processar_romaneio(id_impressao):
    """Página para processar um romaneio - preencher quantidades separadas"""
    try:
        print(f"🔄 Processando romaneio: {id_impressao}")
        
        # Buscar dados do romaneio
        sheet = get_google_sheets_connection()
        if not sheet:
            flash('Erro ao conectar com Google Sheets', 'error')
            return redirect(url_for('controle_impressoes'))
        
        # Buscar dados da impressão
        impressoes_worksheet = sheet.worksheet("IMPRESSOES")
        all_values = impressoes_worksheet.get_all_values()
        
        romaneio_data = None
        for row in all_values[1:]:  # Pular cabeçalho
            if len(row) >= 4 and row[0] == id_impressao:
                romaneio_data = {
                    'id_impressao': row[0],
                    'data_impressao': row[1],
                    'usuario_impressao': row[2],
                    'status': row[3],
                    'total_itens': int(row[4]) if row[4].isdigit() else 0,
                    'observacoes': row[5] if len(row) > 5 else ''
                }
                break
        
        if not romaneio_data:
            flash('Romaneio não encontrado', 'error')
            return redirect(url_for('controle_impressoes'))
        
        # Buscar itens da impressão
        itens_worksheet = sheet.worksheet("IMPRESSAO_ITENS")
        itens_values = itens_worksheet.get_all_values()
        
        print(f"📋 Total de linhas na aba IMPRESSAO_ITENS: {len(itens_values)}")
        print(f"🔍 Buscando itens para romaneio: {id_impressao}")
        
        itens_data = []
        # Buscar nas linhas de dados (pular cabeçalho)
        for i, row in enumerate(itens_values[1:], start=2):
            print(f"   Linha {i}: {row[:5]}...")
            if len(row) >= 10 and row[0] == id_impressao:
                print(f"   ✅ Item encontrado: {row[4]} - {row[5]}")
                item = {
                    'id_solicitacao': row[1],
                    'data': row[2],
                    'solicitante': row[3],
                    'codigo': row[4],
                    'descricao': row[5],
                    'quantidade': int(row[7]) if row[7].isdigit() else 0,  # Quantidade na posição 7
                    'unidade': row[6],  # Unidade na posição 6
                    'alta_demanda': row[10].lower() in ['sim', 's', 'yes', 'y', 'true', '1'] if len(row) > 10 else False,
                    'locacao_matriz': row[8],
                    'saldo_estoque': int(row[9]) if row[9].isdigit() else 0,
                    'media_mensal': int(row[10]) if row[10].isdigit() else 0,
                    'qtd_separada_atual': 0,
                    'observacoes_item': '',
                    'status_item': 'Pendente' if len(row) <= 12 or row[12].lower() in ['false', '0', ''] else ('Processado' if row[12].lower() in ['true', '1', 'processado'] else row[12])  # STATUS_ITEM na posição 12
                }
                itens_data.append(item)
        
        print(f"📦 Total de itens encontrados: {len(itens_data)}")
        
        # Buscar quantidades já separadas das solicitações
        worksheets = sheet.worksheets()
        print(f"📋 Abas disponíveis para processamento: {[ws.title for ws in worksheets]}")
        
        solicitacoes_worksheet = None
        possible_names = ["Solicitações", "SOLICITAÇÕES", "Solicitacoes", "SOLICITACOES", "Solicitações", "Solicitacoes"]
        
        for name in possible_names:
            try:
                solicitacoes_worksheet = sheet.worksheet(name)
                print(f"✅ Encontrada aba para processamento: {name}")
                break
            except:
                continue
        
        if not solicitacoes_worksheet:
            print("❌ Nenhuma aba de solicitações encontrada para processamento")
            flash('Aba de solicitações não encontrada', 'error')
            return redirect(url_for('controle_impressoes'))
        
        solicitacoes_values = solicitacoes_worksheet.get_all_values()
        
        # Mapear quantidades separadas e saldos por ID da solicitação
        qtd_separadas = {}
        saldos = {}
        
        # Encontrar colunas necessárias
        header_solicitacoes = solicitacoes_values[0] if solicitacoes_values else []
        id_solicitacao_col = None
        qtd_separada_col = None
        saldo_col = None
        
        for i, col_name in enumerate(header_solicitacoes):
            col_name_clean = col_name.strip()
            if col_name_clean == 'ID_SOLICITACAO':
                id_solicitacao_col = i
            elif col_name_clean == 'Qtd. Separada':
                qtd_separada_col = i
            elif col_name_clean == 'Saldo':
                saldo_col = i
        
        print(f"🔍 Colunas encontradas - ID_SOLICITACAO: {id_solicitacao_col}, Qtd. Separada: {qtd_separada_col}, Saldo: {saldo_col}")
        
        # Se não encontrou as colunas pelos nomes, usar posições fixas conhecidas
        if id_solicitacao_col is None:
            id_solicitacao_col = 15  # Coluna P
            print(f"📍 Usando posição fixa para ID_SOLICITACAO: coluna {id_solicitacao_col}")
        
        if qtd_separada_col is None:
            qtd_separada_col = 10  # Coluna K
            print(f"📍 Usando posição fixa para Qtd. Separada: coluna {qtd_separada_col}")
        
        if saldo_col is None:
            saldo_col = 12  # Coluna M (próxima à Qtd. Separada)
            print(f"📍 Usando posição fixa para Saldo: coluna {saldo_col}")
        
        for row in solicitacoes_values[1:]:  # Pular cabeçalho
            if len(row) > max(id_solicitacao_col, qtd_separada_col, saldo_col):
                try:
                    id_solic = row[id_solicitacao_col].strip()
                    qtd_sep = int(row[qtd_separada_col]) if row[qtd_separada_col].strip() else 0
                    saldo_atual = int(row[saldo_col]) if row[saldo_col].strip() else 0
                    if id_solic:  # Só adicionar se tem ID válido
                        qtd_separadas[id_solic] = qtd_sep
                        saldos[id_solic] = saldo_atual
                        print(f"   ✅ ID: {id_solic} -> Qtd Separada: {qtd_sep}, Saldo: {saldo_atual}")
                except (ValueError, IndexError) as e:
                    print(f"   ❌ Erro ao processar linha: {e}")
                    continue
        
        # Atualizar itens com quantidades separadas e saldos
        print(f"📊 Total de quantidades separadas encontradas: {len(qtd_separadas)}")
        print(f"📊 Total de saldos encontrados: {len(saldos)}")
        print(f"🔍 IDs com quantidade separada: {list(qtd_separadas.keys())[:5]}...")
        
        for item in itens_data:
            qtd_atual = qtd_separadas.get(item['id_solicitacao'], 0)
            saldo_atual = saldos.get(item['id_solicitacao'], 0)
            item['qtd_separada_atual'] = qtd_atual
            item['saldo_atual'] = saldo_atual
            print(f"   📦 Item {item['id_solicitacao']}: Qtd Separada = {qtd_atual}, Saldo = {saldo_atual}")
        
        print(f"✅ Renderizando template com {len(itens_data)} itens")
        return render_template('processar_romaneio.html', 
                             romaneio=romaneio_data,
                             itens=itens_data)
        
    except Exception as e:
        print(f"❌ Erro ao processar romaneio: {e}")
        flash('Erro ao carregar dados do romaneio', 'error')
        return redirect(url_for('controle_impressoes'))

# =============================================================================
# FUNÇÕES OTIMIZADAS PARA PROCESSAMENTO DE ROMANEIOS
# =============================================================================

@cached_function(cache_duration=15, force_refresh_interval=10)  # Cache muito curto para solicitações ativas
def buscar_solicitacoes_ativas(limite=None, offset=0):
    """Busca apenas solicitações com status ativo (Aberto, Em Separação) - OTIMIZADO COM PAGINAÇÃO"""
    try:
        sheet = get_google_sheets_connection()
        if not sheet:
            return None, None
        
        # Buscar aba de solicitações ativas
        solicitacoes_worksheet = None
        possible_names = ["Solicitações", "SOLICITAÇÕES", "Solicitacoes", "SOLICITACOES"]
        
        for name in possible_names:
            try:
                solicitacoes_worksheet = sheet.worksheet(name)
                break
            except:
                continue
        
        if not solicitacoes_worksheet:
            return None, None
        
        # OTIMIZAÇÃO: Buscar apenas linhas necessárias com paginação
        if limite:
            # Usar range específico para paginação
            start_row = offset + 2  # +2 porque a primeira linha é cabeçalho e começamos do 1
            end_row = start_row + limite - 1
            range_name = f"A{start_row}:Z{end_row}"
            print(f"📄 Buscando range: {range_name}")
            all_values = solicitacoes_worksheet.get(range_name)
            # Adicionar cabeçalho
            header = solicitacoes_worksheet.get('A1:Z1')[0] if solicitacoes_worksheet.get('A1:Z1') else []
            all_values = [header] + all_values if header else all_values
        else:
            # Buscar todas as linhas (comportamento original)
            all_values = solicitacoes_worksheet.get_all_values()
        
        if not all_values or len(all_values) < 2:
            return [], all_values[0] if all_values else []
        
        header = all_values[0]
        status_col = None
        id_solicitacao_col = None
        
        # Encontrar colunas necessárias
        for i, col_name in enumerate(header):
            col_name_clean = col_name.strip()
            if col_name_clean == 'Status':
                status_col = i
        
        # ID_SOLICITACAO está na coluna P (índice 15)
        id_solicitacao_col = 15
        
        if status_col is None:
            print("⚠️ Coluna Status não encontrada, retornando todas as solicitações")
            return all_values[1:], header
        
        # Filtrar apenas status ativos - OTIMIZAÇÃO: usar list comprehension
        solicitacoes_ativas = [
            row for row in all_values[1:] 
            if len(row) > status_col and row[status_col].strip() in ['Aberto', 'Em Separação']
        ]
        
        print(f"📊 Encontradas {len(solicitacoes_ativas)} solicitações ativas (de {len(all_values)-1} total)")
        print(f"📍 Coluna ID_SOLICITACAO: {id_solicitacao_col}")
        return solicitacoes_ativas, header
        
    except Exception as e:
        print(f"❌ Erro ao buscar solicitações ativas: {e}")
        return None, None

def processar_baixa_item(id_solicitacao, qtd_separada, observacoes, solicitacoes_ativas, header, status_especial=None):
    """Processa a baixa de um item específico - OTIMIZADO"""
    try:
        # ID_SOLICITACAO está na coluna P (índice 15)
        id_solicitacao_col = 15  # Coluna P
        print(f"🔍 Usando coluna P (índice {id_solicitacao_col}) para ID_SOLICITACAO")
        
        # Verificar se a coluna P existe
        if len(header) <= id_solicitacao_col:
            print(f"❌ Coluna P não existe. Total de colunas: {len(header)}")
            print(f"🔍 Header completo: {header}")
            return None
        
        # OTIMIZAÇÃO: Usar dict para busca O(1) em vez de loop O(n)
        # Usar ID_SOLICITACAO como chave em vez da primeira coluna
        solicitacoes_dict = {}
        print(f"🔍 Processando {len(solicitacoes_ativas)} solicitações ativas...")
        for i, row in enumerate(solicitacoes_ativas):
            print(f"   Linha {i}: {row[:3]}... (total: {len(row)} colunas)")
            if len(row) > id_solicitacao_col and row[id_solicitacao_col].strip():
                id_solic = row[id_solicitacao_col]
                # i é o índice na lista solicitacoes_ativas (0-based)
                # Para converter para linha da planilha: i + 2 (pular cabeçalho + 1)
                linha_planilha = i + 2
                solicitacoes_dict[id_solic] = (i, row, linha_planilha)
                print(f"   ✅ Adicionado ID: {id_solic} (linha {linha_planilha})")
            else:
                print(f"   ❌ Linha {i} não tem ID válido na coluna {id_solicitacao_col}")
        
        print(f"📊 Total de IDs encontrados: {len(solicitacoes_dict)}")
        
        if id_solicitacao not in solicitacoes_dict:
            print(f"❌ Solicitação {id_solicitacao} não encontrada nas ativas")
            print(f"🔍 IDs disponíveis nas solicitações ativas: {list(solicitacoes_dict.keys())[:5]}...")
            print(f"🔍 Total de solicitações ativas: {len(solicitacoes_dict)}")
            return None
        
        i, row, linha_planilha = solicitacoes_dict[id_solicitacao]
        print(f"✅ Processando baixa para {id_solicitacao}: {qtd_separada} unidades (linha {linha_planilha})")
        
        # Encontrar colunas necessárias - OTIMIZAÇÃO: cache de índices
        col_indices = {}
        for j, col_name in enumerate(header):
            col_name_clean = col_name.strip()
            if col_name_clean == 'Qtd. Separada':
                col_indices['qtd_separada'] = j
            elif col_name_clean == 'Status':
                col_indices['status'] = j
            elif col_name_clean == 'Saldo':
                col_indices['saldo'] = j
            elif col_name_clean == 'Quantidade':
                col_indices['quantidade'] = j
        
        # Verificar se todas as colunas foram encontradas
        required_cols = ['qtd_separada', 'status', 'saldo', 'quantidade']
        if not all(col in col_indices for col in required_cols):
            print(f"❌ Colunas necessárias não encontradas: {col_indices}")
            return None
        
        # Obter valores atuais da planilha Solicitações
        qtd_separada_atual = int(row[col_indices['qtd_separada']]) if row[col_indices['qtd_separada']].strip() else 0
        quantidade_solicitada = int(row[col_indices['quantidade']]) if row[col_indices['quantidade']].strip() else 0
        
        print(f"📊 VALORES ATUAIS DA PLANILHA:")
        print(f"   Qtd. Separada atual: {qtd_separada_atual}")
        print(f"   Quantidade solicitada: {quantidade_solicitada}")
        print(f"   Qtd. Separada nova (do formulário): {qtd_separada}")
        
        # CORREÇÃO: Somar o valor existente com o novo valor
        qtd_separada_total = qtd_separada_atual + qtd_separada
        
        # CORREÇÃO: Calcular Saldo = Quantidade - Qtd. Separada Total
        saldo = quantidade_solicitada - qtd_separada_total
        
        print(f"🧮 CÁLCULOS:")
        print(f"   Qtd. Separada Total: {qtd_separada_atual} + {qtd_separada} = {qtd_separada_total}")
        print(f"   Saldo: {quantidade_solicitada} - {qtd_separada_total} = {saldo}")
        
        # Determinar status - OTIMIZAÇÃO: usar operador ternário
        if status_especial:
            status = status_especial
            print(f"🎯 Status especial aplicado: {status}")
        else:
            status = ('Parcial' if qtd_separada_total < quantidade_solicitada else
                     'Concluida' if qtd_separada_total == quantidade_solicitada else 'Excesso')
            print(f"📊 Status calculado automaticamente: {status}")
        
        # Preparar atualização
        atualizacao = {
            'id_solicitacao': id_solicitacao,
            'qtd_separada_total': qtd_separada_total,
            'status': status,
            'saldo': saldo,
            'observacoes': observacoes,
            'col_indices': col_indices,
            'row_index': linha_planilha  # Usar a linha correta da planilha
        }
        
        print(f"✅ RESULTADO FINAL:")
        print(f"   Qtd. Separada Total: {qtd_separada_total}")
        print(f"   Saldo: {saldo}")
        print(f"   Status: {status}")
        print(f"   Linha da planilha: {linha_planilha}")
        
        return atualizacao
        
    except Exception as e:
        print(f"❌ Erro ao processar baixa do item {id_solicitacao}: {e}")
        return None

def criar_colunas_impressao_itens():
    """Cria/verifica as colunas necessárias na aba IMPRESSAO_ITENS"""
    try:
        sheet = get_google_sheets_connection()
        if not sheet:
            return False
            
        impressao_itens_worksheet = sheet.worksheet("IMPRESSAO_ITENS")
        
        # Definir colunas necessárias na ordem correta
        colunas_necessarias = [
            'ID_IMPRESSAO',
            'ID_SOLICITACAO', 
            'DATA',
            'SOLICITANTE',
            'CODIGO',
            'DESCRICAO',
            'UNIDADE',
            'QUANTIDADE',
            'LOCACAO_MATRIZ',
            'SALDO_ESTOQUE',
            'MEDIA_MENSAL',
            'ALTA_DEMANDA',
            'STATUS_ITEM',
            'QTD_SEPARADA',
            'OBSERVACOES_ITEM',
            'DATA_SEPARACAO',
            'SEPARADO_POR',
            'USUARIO_PROCESSAMENTO',
            'CREATED_AT',
            'UPDATED_AT'
        ]
        
        # Verificar se já existe cabeçalho
        all_values = impressao_itens_worksheet.get_all_values()
        
        if not all_values or len(all_values) == 0:
            print("📋 Criando cabeçalho na aba IMPRESSAO_ITENS...")
            impressao_itens_worksheet.append_row(colunas_necessarias)
            print(f"✅ Cabeçalho criado com {len(colunas_necessarias)} colunas")
            return True
        
        # Verificar se cabeçalho está correto
        header_atual = all_values[0] if all_values else []
        print(f"📍 Cabeçalho atual: {header_atual}")
        
        # Verificar se todas as colunas necessárias existem
        colunas_faltando = []
        for coluna in colunas_necessarias:
            if coluna not in header_atual:
                colunas_faltando.append(coluna)
        
        if colunas_faltando:
            print(f"⚠️ Colunas faltando: {colunas_faltando}")
            print("🔄 Adicionando colunas faltantes...")
            
            # Adicionar colunas faltantes no final
            for coluna in colunas_faltando:
                impressao_itens_worksheet.add_cols(1)
                # Encontrar a última coluna preenchida
                ultima_coluna = len(header_atual)
                impressao_itens_worksheet.update(f'{chr(65 + ultima_coluna)}1', [[coluna]])
                header_atual.append(coluna)
                print(f"✅ Adicionada coluna: {coluna}")
        else:
            print("✅ Todas as colunas necessárias já existem")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar colunas IMPRESSAO_ITENS: {e}")
        return False

def atualizar_imprecao_itens(id_romaneio, itens_processados, usuario_processamento):
    """Atualiza a aba IMPRESSAO_ITENS com as baixas processadas - VERSÃO SIMPLIFICADA"""
    try:
        print(f"🚀 ATUALIZANDO IMPRESSAO_ITENS - VERSÃO SIMPLIFICADA")
        print(f"📦 Romaneio: {id_romaneio}")
        print(f"📋 Itens processados: {itens_processados}")
        print(f"👤 Usuário: {usuario_processamento}")
        
        sheet = get_google_sheets_connection()
        if not sheet:
            print("❌ Erro ao conectar com Google Sheets")
            return False
        
        impressao_itens_worksheet = sheet.worksheet("IMPRESSAO_ITENS")
        
        # Buscar TODAS as linhas da planilha
        all_values = impressao_itens_worksheet.get_all_values()
        print(f"📊 Total de linhas na IMPRESSAO_ITENS: {len(all_values)}")
        
        if not all_values or len(all_values) < 2:
            print("❌ Aba IMPRESSAO_ITENS vazia")
            return False
        
        # ABORDAGEM SIMPLIFICADA: Atualizar diretamente usando range específico
        print(f"🔄 ABORDAGEM SIMPLIFICADA - Atualizando diretamente")
        
        # Preparar dados de atualização
        data_processamento = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        atualizacoes = []
        
        # Para cada item processado, atualizar diretamente
        for item in itens_processados:
            id_solicitacao = item.get('id_solicitacao', '')
            qtd_separada = item.get('qtd_separada', 0)
            observacoes = item.get('observacoes', '')
            
            print(f"🔄 Processando item: {id_solicitacao} - Qtd: {qtd_separada}, Obs: '{observacoes}'")
            
            # Buscar a linha correspondente na planilha
            linha_encontrada = None
            for i, row in enumerate(all_values[1:], start=2):
                # Verificar se é o item correto (buscar por ID_Solicitacao)
                if len(row) > 1 and row[1] == id_solicitacao:  # Coluna B = ID_Solicitacao
                    linha_encontrada = i
                    print(f"   ✅ Item encontrado na linha {i}")
                    break
            
            if linha_encontrada:
                # Atualizar QTD_SEPARADA (coluna N = 13)
                atualizacoes.append({
                    'range': f'N{linha_encontrada}',
                    'values': [[str(qtd_separada)]]
                })
                
                # Atualizar OBSERVACOES_ITEM (coluna O = 14)
                atualizacoes.append({
                    'range': f'O{linha_encontrada}',
                    'values': [[observacoes]]
                })
                
                # Atualizar STATUS_ITEM para "Processado" (coluna M = 12)
                atualizacoes.append({
                    'range': f'M{linha_encontrada}',
                    'values': [['Processado']]
                })
                
                # Atualizar DATA_SEPARACAO (coluna P = 15)
                atualizacoes.append({
                    'range': f'P{linha_encontrada}',
                    'values': [[data_processamento]]
                })
                
                # Atualizar USUARIO_PROCESSAMENTO (coluna R = 17)
                atualizacoes.append({
                    'range': f'R{linha_encontrada}',
                    'values': [[usuario_processamento]]
                })
                
                print(f"   ✅ Atualizações preparadas para linha {linha_encontrada}")
            else:
                print(f"   ❌ Item {id_solicitacao} não encontrado na planilha!")
        
        print(f"📊 Total de atualizações preparadas: {len(atualizacoes)}")
        
        # Executar atualizações
        if atualizacoes:
            print(f"🔄 Executando {len(atualizacoes)} atualizações na IMPRESSAO_ITENS:")
            for atualizacao in atualizacoes:
                print(f"   📍 {atualizacao['range']}: {atualizacao['values']}")
            
            try:
                impressao_itens_worksheet.batch_update(atualizacoes)
                print(f"✅ {len(atualizacoes)} itens atualizados na IMPRESSAO_ITENS")
                return True
            except Exception as e:
                print(f"❌ Erro ao executar batch_update: {e}")
                return False
        else:
            print("⚠️ Nenhuma atualização para executar na IMPRESSAO_ITENS")
            return False
        
    except Exception as e:
        print(f"❌ Erro ao atualizar IMPRESSAO_ITENS: {e}")
        return False

@app.route('/criar-colunas-impressao-itens', methods=['POST'])
@login_required
def criar_colunas_impressao_itens_route():
    """Rota para criar/verificar colunas da aba IMPRESSAO_ITENS"""
    try:
        if criar_colunas_impressao_itens():
            return jsonify({
                'success': True,
                'message': 'Colunas da aba IMPRESSAO_ITENS criadas/verificadas com sucesso!'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Erro ao criar/verificar colunas da aba IMPRESSAO_ITENS'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro: {str(e)}'
        }), 500

@app.route('/criar-aba-realizar-baixa', methods=['POST'])
@login_required
def criar_aba_realizar_baixa_route():
    """Rota para criar a aba 'Realizar baixa'"""
    try:
        if criar_aba_realizar_baixa():
            return jsonify({
                'success': True,
                'message': 'Aba "Realizar baixa" criada com sucesso!'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Erro ao criar aba "Realizar baixa"'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro: {str(e)}'
        }), 500

@app.route('/salvar-processamento-romaneio', methods=['POST'])
@login_required
def salvar_processamento_romaneio():
    """Processa romaneio usando arquitetura otimizada"""
    try:
        print("🚀 PROCESSAMENTO OTIMIZADO DE ROMANEIO INICIADO!")
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Dados JSON não encontrados'}), 400
        
        id_romaneio = data.get('id_romaneio')
        itens_processados = data.get('itens', [])
        observacoes_gerais = data.get('observacoes_gerais', '')
        checkbox_data = data.get('checkbox_data', {})
        
        print(f"📦 Processando romaneio {id_romaneio} com {len(itens_processados)} itens")
        print(f"🔍 Dados do formulário recebidos: {itens_processados}")
        print(f"📝 Observações gerais: '{observacoes_gerais}'")
        print(f"📋 Dados dos checkboxes: {checkbox_data}")
        
        # Processar checkboxes primeiro
        if checkbox_data:
            excluir_items = checkbox_data.get('excluir', [])
            falta_items = checkbox_data.get('falta', [])
            
            print(f"🗑️ Processando {len(excluir_items)} itens para EXCLUIR (Finalizado)")
            print(f"⚠️ Processando {len(falta_items)} itens para FALTA")
            
            # Processar itens para excluir (status = Finalizado)
            for item_excluir in excluir_items:
                item_id = item_excluir['id']
                observacao = item_excluir['observacao']
                qtd_separada = int(item_excluir.get('qtd_separada', 0))
                print(f"🗑️ Marcando item {item_id} como FINALIZADO - Obs: '{observacao}', Qtd: {qtd_separada}")
                
                # Verificar se já existe este item nos itens_processados
                item_existente = None
                for item in itens_processados:
                    if item.get('id_solicitacao') == item_id:
                        item_existente = item
                        break
                
                if item_existente:
                    # Atualizar item existente com status especial
                    item_existente['status_especial'] = 'Finalizado'
                    item_existente['observacoes'] = observacao
                else:
                    # Adicionar aos itens processados com status especial
                    item_excluir_data = {
                        'id_solicitacao': item_id,
                        'qtd_separada': qtd_separada,
                        'observacoes': observacao,
                        'excluir': True,
                        'status_especial': 'Finalizado'
                    }
                    itens_processados.append(item_excluir_data)
            
            # Processar itens para falta (status = Falta)
            for item_falta in falta_items:
                item_id = item_falta['id']
                observacao = item_falta['observacao']
                qtd_separada = int(item_falta.get('qtd_separada', 0))
                print(f"⚠️ Marcando item {item_id} como FALTA - Obs: '{observacao}', Qtd: {qtd_separada}")
                
                # Verificar se já existe este item nos itens_processados
                item_existente = None
                for item in itens_processados:
                    if item.get('id_solicitacao') == item_id:
                        item_existente = item
                        break
                
                if item_existente:
                    # Atualizar item existente com status especial
                    item_existente['status_especial'] = 'Falta'
                    if observacao:
                        item_existente['observacoes'] = observacao
                else:
                    # Adicionar aos itens processados com status especial
                    item_falta_data = {
                        'id_solicitacao': item_id,
                        'qtd_separada': qtd_separada,
                        'observacoes': observacao,
                        'falta': True,
                        'status_especial': 'Falta'
                    }
                    itens_processados.append(item_falta_data)
        
        # 1. Buscar apenas solicitações ativas (otimizado)
        solicitacoes_ativas, header = buscar_solicitacoes_ativas()
        if solicitacoes_ativas is None:
            return jsonify({'success': False, 'message': 'Erro ao conectar com Google Sheets'})
        
        print(f"📋 Solicitações ativas encontradas: {len(solicitacoes_ativas)}")
        print(f"📋 Header das solicitações: {header}")
        
        # Debug: mostrar algumas linhas das solicitações ativas
        if solicitacoes_ativas:
            print(f"🔍 Primeiras 3 linhas das solicitações ativas:")
            for i, row in enumerate(solicitacoes_ativas[:3]):
                print(f"   Linha {i}: {row[:5]}... (total: {len(row)} colunas)")
                if len(row) > 15:
                    print(f"      Coluna P (ID_SOLICITACAO): '{row[15]}'")
                else:
                    print(f"      ❌ Linha {i} tem apenas {len(row)} colunas, coluna P não existe")
        else:
            print("❌ Nenhuma solicitação ativa encontrada!")
        
        # 2. Buscar TODOS os itens do romaneio na IMPRESSAO_ITENS
        sheet = get_google_sheets_connection()
        impressao_itens_worksheet = sheet.worksheet("IMPRESSAO_ITENS")
        all_itens_romaneio = impressao_itens_worksheet.get_all_values()
        
        # Encontrar todos os itens deste romaneio
        itens_romaneio = []
        for i, row in enumerate(all_itens_romaneio[1:], start=2):  # Pular cabeçalho
            if len(row) > 0 and row[0] == id_romaneio:  # ID_IMPRESSAO
                itens_romaneio.append({
                    'linha': i,
                    'id_solicitacao': row[1] if len(row) > 1 else '',  # ID_SOLICITACAO
                    'row_data': row
                })
        
        print(f"📋 Encontrados {len(itens_romaneio)} itens do romaneio {id_romaneio} na IMPRESSAO_ITENS")
        
        # 3. Processar TODOS os itens do romaneio (mesmo com quantidade zero)
        itens_atualizados = []
        print(f"🔄 Processando TODOS os {len(itens_romaneio)} itens do romaneio...")
        
        for item_romaneio in itens_romaneio:
            id_solicitacao = item_romaneio['id_solicitacao']
            
            # Buscar dados do formulário para este item
            dados_formulario = None
            for item_form in itens_processados:
                if item_form.get('id_solicitacao') == id_solicitacao:
                    dados_formulario = item_form
                    break
            
            # Se não encontrou no formulário, usar valores padrão
            if not dados_formulario:
                qtd_separada = 0
                observacoes = ''
                status_especial = None
                print(f"⚠️ Item {id_solicitacao} não encontrado no formulário - usando valores padrão (Qtd: 0)")
            else:
                qtd_separada = int(dados_formulario.get('qtd_separada', 0))
                observacoes = dados_formulario.get('observacoes', '')
                status_especial = dados_formulario.get('status_especial')
                print(f"✅ Item {id_solicitacao} encontrado no formulário - Qtd: {qtd_separada}, Obs: '{observacoes}', Status Especial: {status_especial}")
            
            # Processar item (SEMPRE, mesmo com quantidade zero)
            print(f"🔄 Processando item {id_solicitacao} com quantidade {qtd_separada}...")
            resultado = processar_baixa_item(
                id_solicitacao, qtd_separada, observacoes, 
                solicitacoes_ativas, header, status_especial
            )
            
            if resultado:
                itens_atualizados.append(resultado)
                print(f"✅ Item {id_solicitacao} processado com sucesso!")
            else:
                print(f"❌ Erro ao processar item {id_solicitacao}!")
        
        if not itens_atualizados:
            return jsonify({'success': False, 'message': 'Nenhum item válido para processar'})
        
        # 4. Atualizar planilha de solicitações
        solicitacoes_worksheet = sheet.worksheet("Solicitações")
        
        atualizacoes = []
        for item in itens_atualizados:
            col_indices = item['col_indices']
            row_index = item['row_index']
            
            # Converter índices para letras
            def col_index_to_letter(col_index):
                result = ""
                while col_index >= 0:
                    result = chr(65 + (col_index % 26)) + result
                    col_index = col_index // 26 - 1
                return result
            
            atualizacoes.extend([
                {
                    'range': f'{col_index_to_letter(col_indices["qtd_separada"])}{row_index}',
                    'values': [[str(item['qtd_separada_total'])]]
                },
                {
                    'range': f'{col_index_to_letter(col_indices["status"])}{row_index}',
                    'values': [[item['status']]]
                },
                {
                    'range': f'{col_index_to_letter(col_indices["saldo"])}{row_index}',
                    'values': [[str(item['saldo'])]]
                }
            ])
        
        # Executar atualizações em lote
        if atualizacoes:
            print(f"🔄 EXECUTANDO {len(atualizacoes)} ATUALIZAÇÕES NA PLANILHA SOLICITAÇÕES:")
            for atualizacao in atualizacoes:
                print(f"   📍 {atualizacao['range']}: {atualizacao['values']}")
            
            solicitacoes_worksheet.batch_update(atualizacoes)
            print(f"✅ {len(atualizacoes)} atualizações realizadas na planilha Solicitações")
        
        # 5. Atualizar IMPRESSAO_ITENS
        usuario_atual = current_user.username if current_user.is_authenticated else 'Sistema'
        print(f"🔄 Atualizando IMPRESSAO_ITENS com {len(itens_processados)} itens...")
        resultado_impressao_itens = atualizar_imprecao_itens(id_romaneio, itens_processados, usuario_atual)
        if resultado_impressao_itens:
            print("✅ IMPRESSAO_ITENS atualizada com sucesso!")
        else:
            print("❌ Erro ao atualizar IMPRESSAO_ITENS!")
        
        # 5. Marcar romaneio como processado e atualizar dados de processamento
        print(f"🔄 ATUALIZANDO ABA IMPRESSOES...")
        print(f"🔍 Buscando romaneio {id_romaneio} na aba IMPRESSOES...")
        
        impressoes_worksheet = sheet.worksheet("IMPRESSOES")
        impressoes_values = impressoes_worksheet.get_all_values()
        
        print(f"📊 Total de linhas na aba IMPRESSOES: {len(impressoes_values)}")
        print(f"📋 Cabeçalho IMPRESSOES: {impressoes_values[0] if impressoes_values else 'VAZIO'}")
        
        # Encontrar colunas necessárias
        header_impressoes = impressoes_values[0] if impressoes_values else []
        col_indices_impressoes = {}
        for i, col_name in enumerate(header_impressoes):
            col_name_clean = col_name.strip()
            print(f"   Coluna {i}: '{col_name_clean}'")
            if col_name_clean == 'STATUS':
                col_indices_impressoes['status'] = i
            elif col_name_clean == 'DATA_PROCESSAMENTO':
                col_indices_impressoes['data_processamento'] = i
            elif col_name_clean == 'USUARIO_PROCESSAMENTO':
                col_indices_impressoes['usuario_processamento'] = i
            elif col_name_clean == 'OBSERVACOES':
                col_indices_impressoes['observacoes'] = i
                print(f"   ✅ Coluna OBSERVACOES encontrada na posição {i}")
        
        print(f"📍 Colunas IMPRESSOES encontradas: {col_indices_impressoes}")
        
        # Se não encontrou a coluna USUARIO_PROCESSAMENTO, criar
        if 'usuario_processamento' not in col_indices_impressoes:
            print("⚠️ Coluna USUARIO_PROCESSAMENTO não encontrada - criando...")
            impressoes_worksheet.add_cols(1)
            # Adicionar cabeçalho na nova coluna
            ultima_coluna = len(header_impressoes)
            impressoes_worksheet.update(f'{chr(65 + ultima_coluna)}1', [['USUARIO_PROCESSAMENTO']])
            col_indices_impressoes['usuario_processamento'] = ultima_coluna
            print(f"✅ Coluna USUARIO_PROCESSAMENTO criada na posição {ultima_coluna}")
        
        romaneio_encontrado = False
        for i, row in enumerate(impressoes_values[1:], start=2):
            if len(row) > 0 and row[0] == id_romaneio:
                print(f"✅ Romaneio {id_romaneio} encontrado na linha {i}")
                romaneio_encontrado = True
                
                # Atualizar status
                if 'status' in col_indices_impressoes:
                    col_letra = chr(65 + col_indices_impressoes["status"])
                    impressoes_worksheet.update(f'{col_letra}{i}', [['Processado']])
                    print(f"   📋 Status atualizado para 'Processado' -> {col_letra}{i}")
                else:
                    print(f"   ❌ Coluna 'Status' não encontrada!")
                
                # Atualizar data de processamento
                if 'data_processamento' in col_indices_impressoes:
                    data_processamento = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    col_letra = chr(65 + col_indices_impressoes["data_processamento"])
                    impressoes_worksheet.update(f'{col_letra}{i}', [[data_processamento]])
                    print(f"   📅 Data processamento: {data_processamento} -> {col_letra}{i}")
                else:
                    print(f"   ❌ Coluna 'Data_Processamento' não encontrada!")
                
                # Atualizar usuário que processou
                if 'usuario_processamento' in col_indices_impressoes:
                    usuario_atual = current_user.username if current_user.is_authenticated else 'Sistema'
                    col_letra = chr(65 + col_indices_impressoes["usuario_processamento"])
                    impressoes_worksheet.update(f'{col_letra}{i}', [[usuario_atual]])
                    print(f"   👤 Usuário processamento: {usuario_atual} -> {col_letra}{i}")
                else:
                    print(f"   ❌ Coluna 'Usuario_Processamento' não encontrada!")
                
                # Atualizar observações gerais (sempre, mesmo se vazio)
                if 'observacoes' in col_indices_impressoes:
                    col_letra = chr(65 + col_indices_impressoes["observacoes"])
                    # Sempre atualizar, mesmo se observacoes_gerais estiver vazio
                    impressoes_worksheet.update(f'{col_letra}{i}', [[observacoes_gerais]])
                    print(f"   📝 Observações gerais: '{observacoes_gerais}' -> {col_letra}{i}")
                else:
                    print(f"   ⚠️ Coluna OBSERVACOES não encontrada na aba IMPRESSOES!")
                    print(f"   📋 Colunas disponíveis: {list(col_indices_impressoes.keys())}")
                
                print(f"✅ Romaneio {id_romaneio} marcado como processado na linha {i}")
                break
        
        if not romaneio_encontrado:
            print(f"❌ Romaneio {id_romaneio} NÃO encontrado na aba IMPRESSOES!")
            print(f"   Verificando estrutura da planilha...")
            print(f"   Primeiras 5 linhas da aba IMPRESSOES:")
            for j, row in enumerate(impressoes_values[:5]):
                print(f"     Linha {j}: {row}")
            print(f"   🔍 Procurando por ID: '{id_romaneio}'")
            print(f"   📋 IDs encontrados nas primeiras linhas:")
            for j, row in enumerate(impressoes_values[1:6], start=1):
                if len(row) > 0:
                    print(f"     Linha {j+1}: ID = '{row[0]}'")
        
        # 6. Salvar dados na aba "Realizar baixa" para controle externo
        print(f"🔄 SALVANDO DADOS NA ABA 'REALIZAR BAIXA'...")
        usuario_atual = current_user.username if current_user.is_authenticated else 'Sistema'
        resultado_realizar_baixa = salvar_dados_realizar_baixa(id_romaneio, itens_processados, usuario_atual)
        if resultado_realizar_baixa:
            print("✅ Dados salvos na aba 'Realizar baixa' com sucesso!")
        else:
            print("⚠️ Erro ao salvar dados na aba 'Realizar baixa' (não crítico)")
        
        return jsonify({
            'success': True, 
            'message': f'Romaneio {id_romaneio} processado com sucesso!',
            'itens_atualizados': len(itens_atualizados)
        })
        
    except Exception as e:
        print(f"❌ Erro no processamento otimizado: {e}")
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'})

@app.route('/reimprimir-romaneio/<id_impressao>')
@login_required
def reimprimir_romaneio(id_impressao):
    """Reimprime um romaneio existente gerando uma cópia com marca d'água"""
    try:
        from pdf_generator import buscar_pdf_romaneio, gerar_e_salvar_romaneio_pdf
        from datetime import datetime
        
        print(f"🔄 Gerando cópia do romaneio: {id_impressao}")
        
        # Buscar dados do romaneio original
        sheet = get_google_sheets_connection()
        if not sheet:
            flash('Erro ao conectar com Google Sheets', 'error')
            return redirect(url_for('controle_impressoes'))
        
        # Buscar dados da impressão
        impressoes_worksheet = sheet.worksheet("IMPRESSOES")
        all_values = impressoes_worksheet.get_all_values()
        
        romaneio_data = None
        for row in all_values[1:]:  # Pular cabeçalho
            if len(row) >= 4 and row[0] == id_impressao:
                romaneio_data = {
                    'id_impressao': row[0],
                    'data_impressao': row[1],
                    'usuario_impressao': row[2],
                    'status': row[3],
                    'total_itens': int(row[4]) if row[4].isdigit() else 0,
                    'observacoes': row[5] if len(row) > 5 else ''
                }
                break
        
        if not romaneio_data:
            flash('Romaneio não encontrado', 'error')
            return redirect(url_for('controle_impressoes'))
        
        # Buscar itens da impressão
        itens_worksheet = sheet.worksheet("IMPRESSAO_ITENS")
        itens_values = itens_worksheet.get_all_values()
        
        itens_data = []
        for row in itens_values[1:]:  # Pular cabeçalho
            if len(row) >= 10 and row[1] == id_impressao:
                item = {
                    'data': row[2],
                    'solicitante': row[3],
                    'codigo': row[4],
                    'descricao': row[5],
                    'quantidade': int(row[6]) if row[6].isdigit() else 0,
                    'alta_demanda': row[10].lower() in ['sim', 's', 'yes', 'y', 'true', '1'] if len(row) > 10 else False,
                    'locacao_matriz': row[7],
                    'saldo_estoque': int(row[8]) if row[8].isdigit() else 0,
                    'media_mensal': int(row[9]) if row[9].isdigit() else 0,
                    'qtd_pendente': int(row[6]) if row[6].isdigit() else 0,
                    'qtd_separada': 0
                }
                itens_data.append(item)
        
        # Adicionar data e hora da reimpressão aos dados do romaneio
        data_reimpressao = datetime.now()
        romaneio_data['data_reimpressao'] = data_reimpressao.strftime('%d/%m/%Y, %H:%M:%S')
        romaneio_data['is_reprint'] = True
        
        # Renderizar o template HTML (igual ao que aparece na tela)
        html_content = render_template('formulario_impressao.html', 
                                     id_impressao=id_impressao,
                                     solicitacoes=itens_data,
                                     romaneio_data=romaneio_data)
        
        # Gerar PDF com marca d'água de cópia usando o sistema apropriado
        import os
        if os.getenv('GAE_APPLICATION'):
            # Google Cloud - usar ReportLab
            from pdf_cloud_generator import salvar_pdf_cloud
            resultado = salvar_pdf_cloud(html_content, romaneio_data, pasta_destino='Romaneios_Separacao', is_reprint=True)
        else:
            # Desenvolvimento local - usar Chrome headless
            from pdf_browser_generator import salvar_pdf_direto_html
            resultado = salvar_pdf_direto_html(html_content, romaneio_data, pasta_destino='Romaneios_Separacao', is_reprint=True)
        
        if not resultado['success']:
            flash(f'Erro ao gerar cópia: {resultado["message"]}', 'error')
            return redirect(url_for('controle_impressoes'))
        
        # Ler PDF gerado
        if 'file_path' in resultado:
            with open(resultado['file_path'], 'rb') as f:
                pdf_content = f.read()
            filename_for_download = os.path.basename(resultado['file_path'])
        else:
            flash('Erro ao localizar PDF da cópia', 'error')
            return redirect(url_for('controle_impressoes'))
        
        # Retornar PDF para download/visualização
        from flask import Response
        return Response(
            pdf_content,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'inline; filename="{filename_for_download}"'
            }
        )
        
    except Exception as e:
        print(f"❌ Erro ao reimprimir romaneio: {e}")
        flash('Erro ao reimprimir romaneio', 'error')
        return redirect(url_for('controle_impressoes'))

@app.route('/detalhes-impressao/<id_impressao>')
@login_required
def detalhes_impressao(id_impressao):
    """Exibe detalhes de uma impressão específica"""
    try:
        # Buscar itens da impressão
        itens = buscar_itens_impressao(id_impressao)
        
        if not itens:
            flash('Impressão não encontrada', 'error')
            return redirect(url_for('controle_impressoes'))
        
        # Buscar status da impressão na aba IMPRESSOES
        status_impressao = buscar_status_impressao(id_impressao)
        
        return render_template('detalhes_impressao.html', 
                             id_impressao=id_impressao,
                             itens=itens,
                             status_impressao=status_impressao)
        
    except Exception as e:
        print(f"❌ Erro ao carregar detalhes da impressão: {e}")
        flash('Erro ao carregar detalhes da impressão', 'error')
        return redirect(url_for('controle_impressoes'))

# ROTA DESATIVADA - Botão "Marcar como Processada" removido
# @app.route('/processar-impressao/<id_impressao>')
# @login_required
# def processar_impressao(id_impressao):
#     """Exibe tela para processar impressão com quantidades separadas - DESATIVADA"""
#     flash('Funcionalidade desativada', 'warning')
#     return redirect(url_for('controle_impressoes'))

# ROTA DESATIVADA - Botão "Marcar como Processada" removido
# @app.route('/processar-impressao-dados/<id_impressao>', methods=['POST'])
# @login_required
# def processar_impressao_dados(id_impressao):
#     """Processa impressão com dados de separação - DESATIVADA"""
#     return jsonify({'success': False, 'message': 'Funcionalidade desativada'})

@app.route('/verificar-itens-impressao', methods=['POST'])
@login_required
def verificar_itens_impressao():
    """Verifica quais itens já estão em impressão pendente ou com status 'Em Separação'"""
    try:
        data = request.get_json()
        ids = data.get('ids', [])
        
        if not ids:
            return jsonify({
                'success': True,
                'itens_em_impressao': [],
                'itens_em_separacao': []
            })
        
        # Verificar itens em impressão pendente
        itens_em_impressao = verificar_itens_em_impressao_pendente(ids)
        
        # Verificar itens com status "Em Separação"
        itens_em_separacao = verificar_itens_em_separacao(ids)
        
        total_bloqueados = len(itens_em_impressao) + len(itens_em_separacao)
        
        return jsonify({
            'success': True,
            'itens_em_impressao': itens_em_impressao,
            'itens_em_separacao': itens_em_separacao,
            'total_verificados': len(ids),
            'total_bloqueados': total_bloqueados
        })
        
    except Exception as e:
        print(f"❌ Erro ao verificar itens em impressão: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao verificar itens: {str(e)}',
            'itens_em_impressao': [],
            'itens_em_separacao': []
        }), 500

@app.route('/buscar-impressao/<id_impressao>')
@login_required
def buscar_impressao(id_impressao):
    """Busca impressão específica por ID"""
    try:
        impressao = buscar_impressao_por_id(id_impressao)
        
        if impressao:
            return jsonify({
                'success': True,
                'impressao': impressao
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Impressão não encontrada'
            })
        
    except Exception as e:
        print(f"❌ Erro ao buscar impressão: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500

def buscar_solicitacoes_selecionadas(ids_selecionados):
    """Busca dados das solicitações selecionadas do Google Sheets - VERSÃO OTIMIZADA"""
    try:
        print(f"🔍 Buscando {len(ids_selecionados)} solicitações selecionadas...")
        
        # Usar dados já carregados em cache para melhor performance
        df = get_google_sheets_data()
        if df is None or df.empty:
            raise Exception("Não foi possível carregar dados da planilha")
        
        # Carregar dados da matriz (opcional)
        try:
            matriz_data = get_matriz_data_from_sheets()
        except Exception as e:
            print(f"⚠️ Erro ao carregar matriz: {e}")
            matriz_data = {}
        
        # Converter IDs para string para comparação
        ids_selecionados_str = [str(id) for id in ids_selecionados]
        print(f"📋 IDs procurados: {ids_selecionados_str}")
        
        # Buscar apenas as linhas que contêm os IDs selecionados
        solicitacoes_encontradas = []
        
        for index, row in df.iterrows():
            # Verificar se o ID da linha (índice + 1) está na lista de selecionados
            row_id = str(index + 1)
            if row_id in ids_selecionados_str:
                print(f"✅ Encontrada linha {row_id} para processamento")
                try:
                    # Processar data
                    data_str = str(row.get('Data', '')) if pd.notna(row.get('Data', '')) else ''
                    try:
                        if data_str:
                            data_obj = pd.to_datetime(data_str, errors='coerce')
                            if pd.isna(data_obj):
                                data_obj = datetime.now()
                        else:
                            data_obj = datetime.now()
                    except:
                        data_obj = datetime.now()
                    
                    # Gerar ID único para a solicitação
                    try:
                        qtd_str = str(row.get('Quantidade', '')).strip()
                        qtd = int(float(qtd_str)) if qtd_str and qtd_str != '' else 0
                    except (ValueError, TypeError):
                        qtd = 0
                    
                    # Gerar ID único incluindo o índice da linha para garantir unicidade
                    id_solicitacao = gerar_id_solicitacao(
                        data_obj,
                        str(row.get('Solicitante', '')),
                        str(row.get('Código', '')),
                        qtd,
                        timestamp=f"{datetime.now().strftime('%H%M%S%f')[:-3]}_{index}"  # Incluir índice da linha
                    )
                    
                    # Extrair dados da linha
                    solicitacao = {
                        'id': row_id,  # ID da linha selecionada
                        'id_solicitacao': id_solicitacao,
                        'data': data_obj,
                        'solicitante': str(row.get('Solicitante', '')),
                        'codigo': str(row.get('Código', '')),
                        'descricao': str(row.get('Descrição', '')),
                        'unidade': str(row.get('Unidade', '')),
                        'quantidade': qtd,
                        'status': str(row.get('Status', '')),
                        'qtd_separada': 0,  # Será calculado depois
                        'saldo': str(row.get('Saldo', '')),
                        'locacao_matriz': '1 E5 E03/F03',  # Valor padrão
                        'saldo_estoque': 600,  # Valor padrão
                        'media_mensal': 41  # Valor padrão
                    }
                    
                    # Enriquecer com dados da matriz
                    if matriz_data and solicitacao['codigo'] in matriz_data:
                        matriz_item = matriz_data[solicitacao['codigo']]
                        solicitacao['saldo_estoque'] = matriz_item['saldo_estoque']
                        solicitacao['locacao_matriz'] = matriz_item['locacao_matriz']
                        solicitacao['media_mensal'] = matriz_item['media_mensal']
                    
                    solicitacoes_encontradas.append(solicitacao)
                    print(f"   ✅ Encontrada solicitação ID {row_id} -> {id_solicitacao}: {solicitacao['solicitante']} - {solicitacao['codigo']}")
                
                except Exception as e:
                    print(f"   ⚠️ Erro ao processar linha {index + 1}: {e}")
                    continue
        
        print(f"📝 {len(solicitacoes_encontradas)} solicitações encontradas no Google Sheets")
        return solicitacoes_encontradas
        
    except Exception as e:
        print(f"❌ Erro ao buscar solicitações no Google Sheets: {e}")
        return []

def atualizar_status_google_sheets_selecionadas(ids_selecionados):
    """Atualiza status das solicitações selecionadas para 'Em Separação' no Google Sheets"""
    try:
        # Conectar com Google Sheets
        sheet = get_google_sheets_connection()
        if not sheet:
            raise Exception("Não foi possível conectar com Google Sheets")
        
        # Acessar a aba "Solicitações" (índice 0)
        worksheet = sheet.get_worksheet(0)
        
        # Obter todos os dados da planilha
        all_values = worksheet.get_all_values()
        
        if not all_values or len(all_values) < 2:
            raise Exception("Planilha de solicitações está vazia")
        
        # Encontrar as colunas necessárias
        headers = all_values[0]
        status_col_index = None
        id_col_index = None
        
        for i, header in enumerate(headers):
            if 'status' in header.lower():
                status_col_index = i
            elif 'id' in header.lower():
                id_col_index = i
        
        if status_col_index is None:
            raise Exception("Coluna 'Status' não encontrada na planilha")
        
        print(f"📊 Coluna de status encontrada no índice {status_col_index}")
        
        # Converter IDs para string para comparação
        ids_selecionados_str = [str(id) for id in ids_selecionados]
        
        # Atualizar apenas as linhas com IDs selecionados
        updates_count = 0
        statuses_to_change = ['Aberta', 'Pendente', 'Aprovada', 'Parcial', 'Concluida']
        
        for row_index, row in enumerate(all_values[1:], start=2):  # Começar da linha 2 (pular cabeçalho)
            try:
                # Verificar se a linha tem dados suficientes
                if len(row) <= status_col_index:
                    continue
                
                # Procurar por ID na linha (pode estar em qualquer coluna)
                row_id = None
                for cell in row:
                    if cell.strip() in ids_selecionados_str:
                        row_id = cell.strip()
                        break
                
                # Se encontrou um ID selecionado
                if row_id:
                    current_status = row[status_col_index].strip()
                    
                    # Se o status atual pode ser alterado para "Em Separação"
                    if current_status in statuses_to_change:
                        # Atualizar a coluna de status
                        worksheet.update_cell(row_index, status_col_index + 1, 'Em Separação')  # +1 porque update_cell usa índice baseado em 1
                        updates_count += 1
                        print(f"   ✅ Linha {row_index}: ID {row_id} - Status '{current_status}' alterado para 'Em Separação'")
                    else:
                        print(f"   ⚠️ Linha {row_index}: ID {row_id} - Status '{current_status}' não pode ser alterado")
                
            except Exception as e:
                print(f"   ⚠️ Erro ao processar linha {row_index}: {e}")
                continue
        
        print(f"📝 {updates_count} linhas atualizadas no Google Sheets")
        return updates_count
        
    except Exception as e:
        print(f"❌ Erro ao atualizar Google Sheets: {e}")
        raise e

def atualizar_status_google_sheets_impressao():
    """Atualiza status das solicitações para 'Em Separação' diretamente no Google Sheets após impressão"""
    try:
        # Conectar com Google Sheets
        sheet = get_google_sheets_connection()
        if not sheet:
            raise Exception("Não foi possível conectar com Google Sheets")
        
        # Acessar a aba "Solicitações" (índice 0)
        worksheet = sheet.get_worksheet(0)
        
        # Obter todos os dados da planilha
        all_values = worksheet.get_all_values()
        
        if not all_values or len(all_values) < 2:
            raise Exception("Planilha de solicitações está vazia")
        
        # Encontrar as colunas necessárias
        headers = all_values[0]
        status_col_index = None
        
        for i, header in enumerate(headers):
            if 'status' in header.lower():
                status_col_index = i
                break
        
        if status_col_index is None:
            raise Exception("Coluna 'Status' não encontrada na planilha")
        
        print(f"📊 Coluna de status encontrada no índice {status_col_index}")
        
        # Atualizar todas as linhas que não estão em "Em Separação" ou "Falta"
        updates_count = 0
        statuses_to_change = ['Aberta', 'Pendente', 'Aprovada', 'Parcial', 'Concluida']
        
        for row_index, row in enumerate(all_values[1:], start=2):  # Começar da linha 2 (pular cabeçalho)
            try:
                # Verificar se a linha tem dados suficientes
                if len(row) <= status_col_index:
                    continue
                
                current_status = row[status_col_index].strip()
                
                # Se o status atual pode ser alterado para "Em Separação"
                if current_status in statuses_to_change:
                    # Atualizar a coluna de status
                    worksheet.update_cell(row_index, status_col_index + 1, 'Em Separação')  # +1 porque update_cell usa índice baseado em 1
                    updates_count += 1
                    print(f"   ✅ Linha {row_index}: Status '{current_status}' alterado para 'Em Separação'")
                
            except Exception as e:
                print(f"   ⚠️ Erro ao processar linha {row_index}: {e}")
                continue
        
        print(f"📝 {updates_count} linhas atualizadas no Google Sheets")
        return updates_count
        
    except Exception as e:
        print(f"❌ Erro ao atualizar Google Sheets: {e}")
        raise e

def atualizar_status_google_sheets(solicitacoes_alteradas):
    """Atualiza status das solicitações no Google Sheets"""
    try:
        # Conectar com Google Sheets
        sheet = get_google_sheets_connection()
        if not sheet:
            raise Exception("Não foi possível conectar com Google Sheets")
        
        # Acessar a aba "Solicitações" (índice 0)
        worksheet = sheet.get_worksheet(0)
        
        # Obter todos os dados da planilha
        all_values = worksheet.get_all_values()
        
        if not all_values or len(all_values) < 2:
            raise Exception("Planilha de solicitações está vazia")
        
        # Encontrar as colunas necessárias
        headers = all_values[0]
        status_col_index = None
        data_col_index = None
        solicitante_col_index = None
        codigo_col_index = None
        
        for i, header in enumerate(headers):
            if 'status' in header.lower():
                status_col_index = i
            elif 'data' in header.lower():
                data_col_index = i
            elif 'solicitante' in header.lower():
                solicitante_col_index = i
            elif 'código' in header.lower() or 'codigo' in header.lower():
                codigo_col_index = i
        
        if status_col_index is None:
            raise Exception("Coluna 'Status' não encontrada na planilha")
        
        print(f"📊 Colunas encontradas - Status: {status_col_index}, Data: {data_col_index}, Solicitante: {solicitante_col_index}, Código: {codigo_col_index}")
        
        # Criar dicionário para mapear solicitações por chave única (data + solicitante + codigo)
        solicitacoes_map = {}
        for s in solicitacoes_alteradas:
            # Criar chave única baseada em data, solicitante e código
            key = f"{s['data']}_{s['solicitante']}_{s['codigo']}"
            solicitacoes_map[key] = s
        
        print(f"🔍 Procurando {len(solicitacoes_map)} solicitações na planilha...")
        
        # Atualizar cada linha na planilha
        updates_count = 0
        for row_index, row in enumerate(all_values[1:], start=2):  # Começar da linha 2 (pular cabeçalho)
            try:
                # Extrair dados da linha
                if len(row) <= max(status_col_index, data_col_index or 0, solicitante_col_index or 0, codigo_col_index or 0):
                    continue
                
                row_data = row[data_col_index] if data_col_index is not None else ''
                row_solicitante = row[solicitante_col_index] if solicitante_col_index is not None else ''
                row_codigo = row[codigo_col_index] if codigo_col_index is not None else ''
                
                # Formatar data para comparação (assumindo formato DD/MM/YYYY)
                if row_data and '/' in row_data:
                    # Extrair apenas a data (remover hora se houver)
                    data_parte = row_data.split(' ')[0]
                    # Converter para formato de comparação
                    try:
                        from datetime import datetime
                        dt = datetime.strptime(data_parte, '%d/%m/%Y')
                        data_formatada = dt.strftime('%d/%m/%Y')
                    except:
                        data_formatada = data_parte
                else:
                    data_formatada = row_data
                
                # Criar chave para comparação
                row_key = f"{data_formatada}_{row_solicitante}_{row_codigo}"
                
                # Verificar se esta linha corresponde a uma solicitação alterada
                if row_key in solicitacoes_map:
                    # Atualizar a coluna de status
                    worksheet.update_cell(row_index, status_col_index + 1, 'Em Separação')  # +1 porque update_cell usa índice baseado em 1
                    updates_count += 1
                    print(f"   ✅ Linha {row_index}: {row_solicitante} - {row_codigo} atualizado para 'Em Separação'")
                
            except Exception as e:
                print(f"   ⚠️ Erro ao processar linha {row_index}: {e}")
                continue
        
        print(f"📝 {updates_count} linhas atualizadas no Google Sheets")
        return updates_count
        
    except Exception as e:
        print(f"❌ Erro ao atualizar Google Sheets: {e}")
        raise e

# Rota de debug para verificar dados da matriz
@app.route('/debug-realizar-baixa')
@login_required
def debug_realizar_baixa():
    """Debug: Verificar dados da aba Realizar baixa"""
    try:
        print("🔍 DEBUG: Verificando dados da aba 'Realizar baixa'...")
        
        sheet = get_google_sheets_connection()
        if not sheet:
            return "❌ Erro ao conectar com Google Sheets"
        
        # Verificar aba Realizar baixa
        try:
            worksheet = sheet.worksheet("Realizar baixa")
            valores = worksheet.get_all_values()
            
            print(f"📊 Total de linhas na aba 'Realizar baixa': {len(valores)}")
            
            if len(valores) > 0:
                print(f"📋 Cabeçalhos: {valores[0]}")
                
                if len(valores) > 1:
                    print("📄 Dados encontrados:")
                    for i, row in enumerate(valores[1:], 1):
                        print(f"   Linha {i}: {row}")
                else:
                    print("⚠️ Apenas cabeçalhos encontrados")
            else:
                print("❌ Aba vazia")
                
        except gspread.WorksheetNotFound:
            print("❌ Aba 'Realizar baixa' não existe")
            return "Aba 'Realizar baixa' não existe"
        
        # Verificar aba IMPRESSAO_ITENS para comparação
        try:
            impressao_worksheet = sheet.worksheet("IMPRESSAO_ITENS")
            impressao_valores = impressao_worksheet.get_all_values()
            
            print(f"\n📊 Total de linhas na aba 'IMPRESSAO_ITENS': {len(impressao_valores)}")
            
            if len(impressao_valores) > 0:
                print(f"📋 Cabeçalhos IMPRESSAO_ITENS: {impressao_valores[0]}")
                
                if len(impressao_valores) > 1:
                    print("📄 Primeiras 3 linhas de dados IMPRESSAO_ITENS:")
                    for i, row in enumerate(impressao_valores[1:4], 1):
                        print(f"   Linha {i}: {row[:7]}...")  # Mostrar apenas primeiras 7 colunas
                        
        except gspread.WorksheetNotFound:
            print("❌ Aba 'IMPRESSAO_ITENS' não existe")
        
        return f"Debug concluído. Verifique o console. Total de registros na 'Realizar baixa': {len(valores) if 'valores' in locals() else 0}"
        
    except Exception as e:
        print(f"❌ Erro no debug: {e}")
        return f"Erro: {str(e)}"

@app.route('/debug-matriz')
@login_required
def debug_matriz():
    """Debug: Verificar dados da matriz do Google Sheets"""
    print("🔍 DEBUG: Verificando dados da matriz do Google Sheets...")
    
    # Buscar dados da matriz do Google Sheets
    matriz_data = get_matriz_data_from_sheets()
    
    print(f"📊 Total de registros na matriz: {len(matriz_data)}")
    
    for codigo, item in matriz_data.items():
        print(f"  - Código: {codigo}, Média: {item['media_mensal']}, Estoque: {item['saldo_estoque']}")
    
    # Buscar especificamente o código "1"
    if "1" in matriz_data:
        item = matriz_data["1"]
        print(f"🎯 Código '1' encontrado:")
        print(f"   - Código: {item['codigo']}")
        print(f"   - Descrição: {item['descricao']}")
        print(f"   - Média Mensal: {item['media_mensal']}")
        print(f"   - Saldo Estoque: {item['saldo_estoque']}")
        print(f"   - Localização: {item['locacao_matriz']}")
    else:
        print("❌ Código '1' NÃO encontrado na matriz")
    
    return f"Debug concluído. Verifique o console. Total de registros: {len(matriz_data)}"

# Rota de teste para debug
@app.route('/test-solicitacoes')
@login_required
def test_solicitacoes():
    status_filter = request.args.get('status', '')
    
    print(f"DEBUG TEST: status_filter recebido: '{status_filter}' (tipo: {type(status_filter)})")
    
    query = Solicitacao.query
    if status_filter:
        print(f"DEBUG TEST: Aplicando filtro para status: '{status_filter}'")
        query = query.filter_by(status=status_filter)
        count_antes = query.count()
        print(f"DEBUG TEST: Total de registros após filtro: {count_antes}")
    
    # Ordenar por data decrescente e buscar todos os registros
    solicitacoes_list = query.order_by(Solicitacao.data.asc()).all()
    print(f"DEBUG TEST: Total de registros retornados: {len(solicitacoes_list)}")
    
    # Enriquecer com dados da matriz do Google Sheets
    matriz_data = get_matriz_data_from_sheets()
    for solicitacao in solicitacoes_list:
        if matriz_data and solicitacao.codigo in matriz_data:
            matriz_item = matriz_data[solicitacao.codigo]
            solicitacao.saldo_estoque = matriz_item['saldo_estoque']
            solicitacao.locacao_matriz = matriz_item['locacao_matriz']
            solicitacao.media_mensal = matriz_item['media_mensal']
        else:
            solicitacao.saldo_estoque = 0
            solicitacao.locacao_matriz = None
            solicitacao.media_mensal = 0
    
    
    solicitacoes = CompleteList(solicitacoes_list)
    
    print(f"DEBUG TEST: Enviando para template - total: {solicitacoes.total}, items: {len(solicitacoes.items)}")
    
    return render_template('test_solicitacoes.html', 
                         solicitacoes=solicitacoes, 
                         status_filter=status_filter)

# Funcionalidade de criação de solicitações removida

# Funcionalidade de baixa de estoque
@app.route('/solicitacoes/<int:id>/baixar', methods=['POST'])
@login_required
def baixar_estoque(id):
    solicitacao = Solicitacao.query.get_or_404(id)
    quantidade_separada = int(request.form['quantidade_separada'])
    
    # Verificar se a solicitação está em separação
    if solicitacao.status != 'Em Separação':
        log_activity('baixar_estoque', 'Solicitacao', id, f'Tentativa de baixa em status inválido: {solicitacao.status}', 'erro')
        flash('Apenas solicitações em separação podem ter baixa registrada!', 'error')
        return redirect(url_for('solicitacoes'))
    
    # Verificar se a quantidade não excede o solicitado
    if quantidade_separada > solicitacao.quantidade:
        flash('Quantidade separada não pode ser maior que a solicitada!', 'error')
        return redirect(url_for('solicitacoes'))
    
    # Atualizar quantidade separada (somar com valor existente)
    solicitacao.qtd_separada += quantidade_separada
    
    # Calcular saldo restante
    solicitacao.saldo = solicitacao.quantidade - solicitacao.qtd_separada
    
    # Atualizar status baseado na quantidade separada
    if solicitacao.qtd_separada == solicitacao.quantidade:
        solicitacao.status = 'Concluida'
        solicitacao.data_separacao = datetime.utcnow()
        solicitacao.separado_por = current_user.username
    elif solicitacao.qtd_separada > 0:
        solicitacao.status = 'Entrega Parcial'
        if not solicitacao.data_separacao:
            solicitacao.data_separacao = datetime.utcnow()
        if not solicitacao.separado_por:
            solicitacao.separado_por = current_user.username
    
    db.session.commit()
    
    # Log da operação
    log_activity('baixar_estoque', 'Solicitacao', id, 
                f'Baixa registrada: {quantidade_separada} unidades. Status alterado para: {solicitacao.status}', 
                'sucesso')
    
    flash(f'Baixa registrada! {quantidade_separada} unidades separadas. Status: {solicitacao.status}', 'success')
    return redirect(url_for('solicitacoes'))

# Funcionalidade para colocar em separação
@app.route('/solicitacoes/<int:id>/separar', methods=['POST'])
@login_required
def colocar_em_separacao(id):
    solicitacao = Solicitacao.query.get_or_404(id)
    
    # Verificar se pode ser colocada em separação
    if solicitacao.status not in ['pendente', 'aprovada']:
        log_activity('separar', 'Solicitacao', id, f'Tentativa de separação em status inválido: {solicitacao.status}', 'erro')
        flash('Apenas solicitações pendentes ou aprovadas podem ser colocadas em separação!', 'error')
        return redirect(url_for('solicitacoes'))
    
    solicitacao.status = 'Em Separação'
    db.session.commit()
    
    # Log da operação
    log_activity('separar', 'Solicitacao', id, f'Solicitação colocada em separação', 'sucesso')
    
    flash('Solicitação colocada em separação!', 'success')
    return redirect(url_for('solicitacoes'))

# Rota de debug
@app.route('/debug-solicitacoes')
@login_required
def debug_solicitacoes():
    # Buscar status únicos
    status_list = [s[0] for s in Solicitacao.query.with_entities(Solicitacao.status).distinct().all()]
    
    # Buscar primeiras 10 solicitações
    solicitacoes = Solicitacao.query.limit(10).all()
    
    return render_template('debug_solicitacoes.html', 
                         status_list=status_list, 
                         solicitacoes=solicitacoes)

# Funcionalidade de baixa em lote
def update_quantidade_separada_na_planilha(codigo, quantidade_nova):
    """Atualiza a quantidade separada na planilha do Google Sheets"""
    try:
        # Conectar com Google Sheets
        sheet = get_google_sheets_connection()
        if not sheet:
            print("❌ Não foi possível conectar com Google Sheets")
            return False
        
        # Acessar a aba "Solicitações"
        worksheet = sheet.get_worksheet(0)
        
        # Obter todos os dados
        all_values = worksheet.get_all_values()
        if not all_values:
            print("❌ Planilha está vazia")
            return False
        
        # Encontrar o cabeçalho
        headers = all_values[0]
        print(f"📋 Cabeçalhos encontrados: {headers}")
        
        # Procurar colunas relevantes
        codigo_col = None
        qtd_separada_col = None
        status_col = None
        quantidade_col = None
        saldo_col = None
        
        for i, header in enumerate(headers):
            header_lower = header.lower().strip()
            print(f"🔍 Verificando cabeçalho {i}: '{header}' (lower: '{header_lower}')")
            
            if 'código' in header_lower or 'codigo' in header_lower:
                codigo_col = i
                print(f"✅ Encontrada coluna Código na posição {i}")
            elif 'qtd' in header_lower and 'separada' in header_lower:
                qtd_separada_col = i
                print(f"✅ Encontrada coluna Qtd. Separada na posição {i}")
            elif 'status' in header_lower and status_col is None:  # Pegar apenas a primeira coluna Status
                status_col = i
                print(f"✅ Encontrada coluna Status na posição {i}")
            elif 'quantidade' in header_lower:
                quantidade_col = i
                print(f"✅ Encontrada coluna Quantidade na posição {i}")
            elif 'saldo' in header_lower:
                saldo_col = i
                print(f"✅ Encontrada coluna Saldo na posição {i}")
        
        print(f"📍 Resumo das colunas encontradas:")
        print(f"   - Código: {codigo_col}")
        print(f"   - Qtd. Separada: {qtd_separada_col}")
        print(f"   - Status: {status_col}")
        print(f"   - Quantidade: {quantidade_col}")
        print(f"   - Saldo: {saldo_col}")
        
        if codigo_col is None:
            print("❌ Coluna 'Código' não encontrada")
            return False
        
        if qtd_separada_col is None:
            print("❌ Coluna 'Qtd. Separada' não encontrada")
            print("📋 Criando coluna 'Qtd. Separada'...")
            # Adicionar nova coluna
            worksheet.add_cols(1)
            headers.append('Qtd. Separada')
            qtd_separada_col = len(headers) - 1
            # Atualizar cabeçalho
            worksheet.update('A1', [headers])
        
        if saldo_col is None:
            print("❌ Coluna 'Saldo' não encontrada")
            print("📋 Criando coluna 'Saldo'...")
            # Adicionar nova coluna
            worksheet.add_cols(1)
            headers.append('Saldo')
            saldo_col = len(headers) - 1
            # Atualizar cabeçalho
            worksheet.update('A1', [headers])
        
        print(f"📍 Coluna Código: {codigo_col}, Coluna Qtd. Separada: {qtd_separada_col}")
        
        # Procurar a linha com o código
        for row_num, row in enumerate(all_values[1:], start=2):  # Começar da linha 2 (pular cabeçalho)
            if len(row) > codigo_col and str(row[codigo_col]).strip() == str(codigo).strip():
                print(f"✅ Encontrada linha {row_num} com código {codigo}")
                
                # Obter quantidade atual separada
                qtd_atual = 0
                if len(row) > qtd_separada_col and row[qtd_separada_col].strip():
                    try:
                        qtd_atual = int(row[qtd_separada_col])
                    except (ValueError, TypeError):
                        qtd_atual = 0
                
                # Calcular nova quantidade
                qtd_nova = qtd_atual + quantidade_nova
                
                # Obter quantidade solicitada para calcular status e saldo
                qtd_solicitada = 0
                if quantidade_col is not None and len(row) > quantidade_col and row[quantidade_col].strip():
                    try:
                        qtd_solicitada = int(row[quantidade_col])
                    except (ValueError, TypeError):
                        qtd_solicitada = 0
                
                # Calcular novo saldo: Quantidade Solicitada - Qtd. Separada (nunca menor que 0)
                novo_saldo = max(0, qtd_solicitada - qtd_nova)
                print(f"💰 Cálculo do saldo: {qtd_solicitada} (solicitada) - {qtd_nova} (separada) = {novo_saldo} (mínimo 0)")
                
                # Determinar novo status baseado na lógica de negócio
                novo_status = ""
                
                if qtd_nova >= qtd_solicitada and qtd_solicitada > 0:
                    if qtd_nova > qtd_solicitada:
                        novo_status = "Excedido"
                    else:
                        novo_status = "Concluído"
                elif qtd_nova > 0:
                    # Qualquer quantidade separada > 0 e < solicitada = Parcial
                    novo_status = "Parcial"
                else:
                    # Nenhuma quantidade separada = Aberta
                    novo_status = "Aberta"
                
                print(f"📊 Lógica de status:")
                print(f"   - Quantidade solicitada: {qtd_solicitada}")
                print(f"   - Quantidade separada: {qtd_nova}")
                print(f"   - Status calculado: {novo_status}")
                
                # Atualizar a célula da quantidade separada
                qtd_cell_address = f"{chr(65 + qtd_separada_col)}{row_num}"
                print(f"📝 Atualizando célula {qtd_cell_address} com valor {qtd_nova}")
                try:
                    worksheet.update(qtd_cell_address, [[qtd_nova]])
                    print(f"✅ Quantidade separada atualizada com sucesso na célula {qtd_cell_address}")
                except Exception as e:
                    print(f"❌ Erro ao atualizar quantidade separada: {e}")
                
                # Atualizar a célula do status se a coluna existir
                if status_col is not None and novo_status:
                    status_cell_address = f"{chr(65 + status_col)}{row_num}"
                    print(f"📝 Atualizando status {status_cell_address} para '{novo_status}'")
                    try:
                        worksheet.update(status_cell_address, [[novo_status]])
                        print(f"✅ Status atualizado com sucesso na célula {status_cell_address}")
                    except Exception as e:
                        print(f"❌ Erro ao atualizar status: {e}")
                else:
                    if status_col is None:
                        print("❌ Coluna Status não encontrada - não é possível atualizar status")
                    if not novo_status:
                        print("❌ Novo status vazio - não é possível atualizar")
                
                # Atualizar a célula do saldo se a coluna existir
                if saldo_col is not None:
                    saldo_cell_address = f"{chr(65 + saldo_col)}{row_num}"
                    print(f"📝 Atualizando saldo {saldo_cell_address} para '{novo_saldo}'")
                    try:
                        worksheet.update(saldo_cell_address, [[novo_saldo]])
                        print(f"✅ Saldo atualizado com sucesso na célula {saldo_cell_address}")
                    except Exception as e:
                        print(f"❌ Erro ao atualizar saldo: {e}")
                else:
                    print("❌ Coluna Saldo não encontrada - não é possível atualizar saldo")
                
                print(f"✅ Quantidade separada atualizada: {qtd_atual} + {quantidade_nova} = {qtd_nova}")
                print(f"✅ Status atualizado para: {novo_status}")
                print(f"✅ Saldo atualizado para: {novo_saldo}")
                return True
        
        print(f"❌ Código {codigo} não encontrado na planilha")
        return False
        
    except Exception as e:
        print(f"❌ Erro ao atualizar planilha: {e}")
        return False

@app.route('/solicitacoes/<int:id>/complementar', methods=['POST'])
@login_required
def complementar_quantidade(id):
    """Complementa a quantidade separada de uma solicitação na planilha do Google Sheets"""
    try:
        data = request.get_json()
        quantidade_nova = int(data.get('quantidade', 0))
        codigo = data.get('codigo', '')
        
        if quantidade_nova <= 0:
            return jsonify({'success': False, 'message': 'Quantidade deve ser maior que zero'})
        
        if not codigo:
            return jsonify({'success': False, 'message': 'Código não fornecido'})
        
        # Atualizar na planilha do Google Sheets
        sucesso = update_quantidade_separada_na_planilha(codigo, quantidade_nova)
        
        if sucesso:
            return jsonify({
                'success': True, 
                'message': f'Quantidade {quantidade_nova} adicionada com sucesso na planilha! Status atualizado conforme regra de negócio.',
                'qtd_separada': quantidade_nova,
                'codigo': codigo,
                'status': 'Atualizado'
            })
        else:
            return jsonify({
                'success': False, 
                'message': 'Erro ao atualizar a planilha do Google Sheets'
            })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao complementar quantidade: {str(e)}'})

@app.route('/solicitacoes/baixar-lote', methods=['POST'])
@login_required
def baixar_estoque_lote():
    try:
        # Obter IDs das solicitações selecionadas
        solicitacao_ids = request.form.getlist('solicitacao_ids')
        
        if not solicitacao_ids:
            log_activity('baixar_lote', 'Solicitacao', None, 'Tentativa de baixa em lote sem seleção', 'erro')
            flash('Nenhuma solicitação selecionada!', 'error')
            return redirect(url_for('solicitacoes'))
        
        baixas_registradas = 0
        
        for solicitacao_id in solicitacao_ids:
            solicitacao = Solicitacao.query.get(int(solicitacao_id))
            
            if not solicitacao:
                continue
                
            # Verificar se a solicitação está em separação
            if solicitacao.status != 'Em Separação':
                continue
            
            # Obter quantidade a separar
            quantidade_key = f'quantidades_{solicitacao_id}'
            quantidade_separada = request.form.get(quantidade_key)
            
            if not quantidade_separada:
                continue
                
            quantidade_separada = int(quantidade_separada)
            
            # Verificar se a quantidade não excede o solicitado
            if quantidade_separada > (solicitacao.quantidade - solicitacao.qtd_separada):
                flash(f'Solicitação #{solicitacao_id}: Quantidade excede o permitido!', 'warning')
                continue
            
            # Atualizar quantidade separada (somar com valor existente)
            solicitacao.qtd_separada += quantidade_separada
            
            # Calcular saldo restante (nunca menor que 0)
            solicitacao.saldo = max(0, solicitacao.quantidade - solicitacao.qtd_separada)
            
            # Atualizar status baseado na quantidade separada
            if solicitacao.qtd_separada == solicitacao.quantidade:
                solicitacao.status = 'Concluida'
                solicitacao.data_separacao = datetime.utcnow()
                solicitacao.separado_por = current_user.username
            elif solicitacao.qtd_separada > 0:
                solicitacao.status = 'Entrega Parcial'
                if not solicitacao.data_separacao:
                    solicitacao.data_separacao = datetime.utcnow()
                if not solicitacao.separado_por:
                    solicitacao.separado_por = current_user.username
            
            baixas_registradas += 1
        
        db.session.commit()
        
        if baixas_registradas > 0:
            log_activity('baixar_lote', 'Solicitacao', None, f'Baixa em lote: {baixas_registradas} solicitações processadas', 'sucesso')
            flash(f'Baixa em lote realizada! {baixas_registradas} solicitações processadas.', 'success')
        else:
            log_activity('baixar_lote', 'Solicitacao', None, 'Baixa em lote: nenhuma solicitação processada', 'aviso')
            flash('Nenhuma baixa foi registrada. Verifique as solicitações selecionadas.', 'warning')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao processar baixa em lote: {str(e)}', 'error')
    
    return redirect(url_for('solicitacoes'))

# Rotas de Logs
@app.route('/logs')
@login_required
def logs():
    """Página de visualização de logs"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # Filtros
    acao_filter = request.args.get('acao', '')
    entidade_filter = request.args.get('entidade', '')
    usuario_filter = request.args.get('usuario', '')
    status_filter = request.args.get('status', '')
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')
    
    # Construir query
    query = Log.query
    
    if acao_filter:
        query = query.filter(Log.acao.contains(acao_filter))
    if entidade_filter:
        query = query.filter(Log.entidade.contains(entidade_filter))
    if usuario_filter:
        query = query.filter(Log.usuario_nome.contains(usuario_filter))
    if status_filter:
        query = query.filter(Log.status == status_filter)
    if data_inicio:
        try:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d')
            query = query.filter(Log.timestamp >= data_inicio_obj)
        except ValueError:
            pass
    if data_fim:
        try:
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d')
            query = query.filter(Log.timestamp <= data_fim_obj)
        except ValueError:
            pass
    
    # Ordenar por timestamp decrescente
    logs = query.order_by(Log.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Estatísticas
    total_logs = Log.query.count()
    logs_hoje = Log.query.filter(Log.timestamp >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).count()
    logs_erro = Log.query.filter(Log.status == 'erro').count()
    
    stats = {
        'total': total_logs,
        'hoje': logs_hoje,
        'erros': logs_erro
    }
    
    return render_template('logs.html', 
                         logs=logs, 
                         stats=stats,
                         acao_filter=acao_filter,
                         entidade_filter=entidade_filter,
                         usuario_filter=usuario_filter,
                         status_filter=status_filter,
                         data_inicio=data_inicio,
                         data_fim=data_fim)

@app.route('/logs/export')
@login_required
def export_logs():
    """Exportar logs para CSV"""
    import csv
    import io
    
    # Aplicar mesmos filtros da página
    acao_filter = request.args.get('acao', '')
    entidade_filter = request.args.get('entidade', '')
    usuario_filter = request.args.get('usuario', '')
    status_filter = request.args.get('status', '')
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')
    
    query = Log.query
    
    if acao_filter:
        query = query.filter(Log.acao.contains(acao_filter))
    if entidade_filter:
        query = query.filter(Log.entidade.contains(entidade_filter))
    if usuario_filter:
        query = query.filter(Log.usuario_nome.contains(usuario_filter))
    if status_filter:
        query = query.filter(Log.status == status_filter)
    if data_inicio:
        try:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d')
            query = query.filter(Log.timestamp >= data_inicio_obj)
        except ValueError:
            pass
    if data_fim:
        try:
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d')
            query = query.filter(Log.timestamp <= data_fim_obj)
        except ValueError:
            pass
    
    logs = query.order_by(Log.timestamp.desc()).all()
    
    # Criar CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Cabeçalho
    writer.writerow(['ID', 'Data/Hora', 'Usuário', 'Ação', 'Entidade', 'ID Entidade', 'Detalhes', 'IP', 'Status'])
    
    # Dados
    for log in logs:
        writer.writerow([
            log.id,
            log.timestamp.strftime('%d/%m/%Y %H:%M:%S') if log.timestamp else '',
            log.usuario_nome,
            log.acao,
            log.entidade,
            log.entidade_id or '',
            log.detalhes or '',
            log.ip_address or '',
            log.status
        ])
    
    output.seek(0)
    
    # Criar resposta
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename=logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    return response

# API removida - não precisamos mais de produtos


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # OTIMIZAÇÃO: Criar índices para melhorar performance
        try:
            print("🚀 Criando índices de otimização...")
            with db.engine.connect() as conn:
                indices = [
                    "CREATE INDEX IF NOT EXISTS idx_user_username ON user (username)",
                    "CREATE INDEX IF NOT EXISTS idx_user_email ON user (email)",
                    "CREATE INDEX IF NOT EXISTS idx_produto_codigo ON produto (codigo)",
                    "CREATE INDEX IF NOT EXISTS idx_produto_categoria ON produto (categoria)"
                ]
                
                for indice in indices:
                    try:
                        conn.execute(db.text(indice))
                        print(f"✅ Índice criado: {indice.split('idx_')[1].split(' ')[0]}")
                    except Exception as e:
                        print(f"⚠️ Erro ao criar índice: {e}")
                        
            print("✅ Índices de otimização criados com sucesso!")
        except Exception as e:
            print(f"⚠️ Erro ao criar índices: {e}")
        
        # Criar usuário admin padrão se não existir
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='marcosvinicius.info@gmail.com', is_admin=True)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✅ Usuário admin criado: admin / admin123")
            print("💡 Para criar mais usuários, execute: python criar_usuarios.py")
    
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
