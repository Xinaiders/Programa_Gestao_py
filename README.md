# 🚀 Sistema de Gestão de Romaneios - LINE FLEX

Sistema otimizado para criação e gerenciamento de romaneios de separação com integração ao Google Sheets.

## 📁 **Estrutura do Projeto**

```
Programa_Gestao_py/
├── 📄 app.py                          # Aplicação principal Flask
├── ⚙️ config.py                       # Configurações gerais
├── ⚙️ config_pdf.py                   # Configurações de PDF
├── ⚙️ cloud_config.py                 # Configurações Google Cloud
├── 🔐 gestaosolicitacao-fe66ad097590.json # Credenciais Google Sheets
├── 📋 requirements.txt                # Dependências Python
├── 🐳 Dockerfile                     # Container Docker
├── ☁️ app.yaml                       # Configuração Google Cloud
├── 🚀 deploy.sh                      # Script de deploy
├── 📊 cloudbuild.yaml                # Build Google Cloud
├── 📝 env.example                    # Exemplo de variáveis de ambiente
│
├── 📁 static/                        # Arquivos estáticos
│   ├── css/
│   │   ├── style.css
│   │   └── solicitacoes.css
│   └── js/
│       ├── main.js
│       └── solicitacoes.js
│
├── 📁 templates/                     # Templates HTML
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── solicitacoes.html
│   ├── formulario_impressao.html
│   ├── processar_romaneio.html
│   ├── controle_impressoes.html
│   ├── detalhes_impressao.html
│   ├── logs.html
│   ├── print_solicitacoes.html
│   ├── processar_impressao.html
│   └── components/
│       └── status_badge.html
│   └── modals/
│       └── solicitacao_modals.html
│
├── 📁 Romaneios_Separacao/           # PDFs gerados
│   └── *.pdf
│
├── 📁 instance/                      # Banco de dados SQLite
│   └── estoque.db
│
└── 📚 Documentação/
    ├── README.md
    ├── OTIMIZACOES_PERFORMANCE.md
    ├── DEPLOY_GCP.md
    ├── CONFIGURACAO_PLANILHA.md
    └── README_PDF_CONFIG.md
```

## 🚀 **Funcionalidades Principais**

- ✅ **Criação de Romaneios**: Interface otimizada para seleção de solicitações
- ✅ **Geração de PDF**: Assíncrona com layout idêntico ao HTML
- ✅ **Processamento**: Sistema completo de separação e baixa
- ✅ **Cache Inteligente**: Performance otimizada com refresh automático
- ✅ **Integração Google Sheets**: Sincronização em tempo real
- ✅ **Controle de Impressões**: Gestão completa do ciclo de vida

## ⚡ **Otimizações Implementadas**

- **Cache Inteligente**: Dados em cache por 15-60 segundos com refresh automático
- **PDF Assíncrono**: Geração em background sem bloquear interface
- **Paginação**: Busca otimizada para planilhas grandes
- **Índices SQL**: Consultas até 10x mais rápidas
- **APIs de Status**: Monitoramento em tempo real

## 🛠️ **Tecnologias**

- **Backend**: Flask, SQLAlchemy, SQLite
- **Frontend**: Bootstrap 5, JavaScript, HTML5/CSS3
- **Integração**: Google Sheets API, Google Cloud Platform
- **PDF**: ReportLab (Cloud) + Chrome Headless (Local)
- **Deploy**: Google App Engine, Docker

## 📋 **Pré-requisitos**

- Python 3.11+
- Google Sheets API habilitada
- Credenciais de serviço Google Sheets
- Chrome/Edge (para geração local de PDF)

## 🚀 **Instalação**

1. **Clone o repositório**
2. **Instale dependências**: `pip install -r requirements.txt`
3. **Configure credenciais**: Coloque o arquivo JSON do Google Sheets
4. **Configure variáveis**: Copie `env.example` para `.env`
5. **Execute**: `python app.py`

## 📊 **APIs Disponíveis**

- `/api/pdf-status/<id>` - Status da geração de PDF
- `/api/invalidar-cache-sheets` - Invalidar cache do Google Sheets
- `/api/forcar-atualizacao` - Forçar atualização completa
- `/api/limpar-cache` - Limpar todo o cache
- `/debug-realizar-baixa` - Debug da aba "Realizar baixa"

## 🔧 **Configurações**

### **Cache**
- Duração: 15-60 segundos
- Refresh automático: 10-30 segundos
- Invalidação: Automática após mudanças

### **PDF**
- Local: Chrome Headless (layout 100% idêntico)
- Cloud: ReportLab (compatível com GCP)

### **Banco de Dados**
- SQLite com índices otimizados
- Criação automática de índices na inicialização

## 📈 **Performance**

| Métrica | Antes | Depois | Melhoria |
|---------|-------|--------|----------|
| Tempo de criação | 15-20s | 3-5s | **75% mais rápido** |
| Consultas Google Sheets | 5-8 | 1-2 | **70% menos** |
| Bloqueio da interface | 15-20s | 0s | **100% eliminado** |

## 🚀 **Deploy**

### **Google Cloud Platform**
```bash
gcloud app deploy
```

### **Docker**
```bash
docker build -t sistema-romaneios .
docker run -p 5000:5000 sistema-romaneios
```

## 📚 **Documentação**

- [Otimizações de Performance](OTIMIZACOES_PERFORMANCE.md)
- [Deploy no Google Cloud](DEPLOY_GCP.md)
- [Configuração da Planilha](CONFIGURACAO_PLANILHA.md)
- [Configuração de PDF](README_PDF_CONFIG.md)

## 🔍 **Debug**

- **Logs**: Console do servidor com informações detalhadas
- **Cache**: Logs de hit/miss automáticos
- **PDF**: Status em tempo real via API
- **Google Sheets**: Debug via `/debug-realizar-baixa`

## ⚠️ **Considerações**

- Cache em memória (perde dados ao reiniciar)
- Threads daemon (morrem quando servidor para)
- Compatível com Google Cloud Platform
- Backward compatibility mantida

---

**🎯 Sistema otimizado e pronto para produção!**