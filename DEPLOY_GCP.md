# 🚀 Deploy no Google Cloud Platform

## ⚠️ **IMPORTANTE - COMPATIBILIDADE GCP**

Este projeto foi adaptado para funcionar no **Google Cloud App Engine** com as seguintes modificações:

### 🔧 **Mudanças Implementadas**

1. **PDF Generation**: 
   - ✅ **Desenvolvimento Local**: Chrome headless (layout 100% idêntico)
   - ✅ **Google Cloud**: ReportLab (compatível, layout similar)

2. **Armazenamento**:
   - ✅ **Desenvolvimento Local**: Arquivos locais em `Romaneios_Separacao/`
   - ✅ **Google Cloud**: Cloud Storage (opcional) ou memória temporária

3. **Banco de Dados**:
   - ✅ **Desenvolvimento Local**: SQLite persistente
   - ✅ **Google Cloud**: SQLite em memória (dados vêm do Google Sheets)

## 📋 **Pré-requisitos**

1. **Google Cloud SDK** instalado
2. **Projeto GCP** criado
3. **APIs habilitadas**:
   - App Engine Admin API
   - Google Sheets API
   - Cloud Storage API (opcional)

## 🚀 **Deploy Steps**

### 1. **Configurar Projeto**
```bash
# Fazer login no GCP
gcloud auth login

# Configurar projeto
gcloud config set project SEU_PROJECT_ID

# Habilitar APIs necessárias
gcloud services enable appengine.googleapis.com
gcloud services enable sheets.googleapis.com
gcloud services enable storage.googleapis.com
```

### 2. **Configurar Variáveis de Ambiente**
```bash
# Editar app.yaml e configurar:
# - SECRET_KEY: chave secreta forte
# - GCS_BUCKET_NAME: nome do bucket para PDFs (opcional)
```

### 3. **Deploy**
```bash
# Deploy para App Engine
gcloud app deploy

# Verificar status
gcloud app browse
```

## 🔧 **Configurações Específicas**

### **app.yaml**
- ✅ Runtime: Python 3.11
- ✅ Recursos: 1 CPU, 1GB RAM
- ✅ Auto-scaling: 1-5 instâncias
- ✅ Banco: SQLite em memória

### **requirements.txt**
- ✅ Todas as dependências compatíveis com GCP
- ✅ ReportLab para geração de PDF
- ✅ Google Cloud Storage (opcional)

## 📁 **Estrutura de Arquivos**

```
├── app.py                    # Aplicação principal
├── app.yaml                  # Configuração GCP
├── requirements.txt          # Dependências
├── cloud_config.py          # Configurações GCP
├── pdf_cloud_generator.py   # Gerador PDF para GCP
├── pdf_browser_generator.py # Gerador PDF local (Chrome)
└── templates/               # Templates HTML
```

## ⚡ **Funcionalidades**

### ✅ **Funcionam no GCP**
- ✅ Autenticação e login
- ✅ Sincronização com Google Sheets
- ✅ Criação de romaneios
- ✅ Geração de PDF (ReportLab)
- ✅ Reimpressão com marca "CÓPIA"
- ✅ Atualização de status

### ⚠️ **Limitações no GCP**
- ⚠️ PDFs não são salvos permanentemente (memória temporária)
- ⚠️ Layout do PDF pode ser ligeiramente diferente (ReportLab vs Chrome)
- ⚠️ Banco de dados em memória (dados vêm do Google Sheets)

## 🔄 **Desenvolvimento vs Produção**

| Funcionalidade | Desenvolvimento | Google Cloud |
|----------------|-----------------|--------------|
| PDF Generation | Chrome Headless | ReportLab |
| Layout PDF | 100% Idêntico | Similar |
| Armazenamento | Arquivos Locais | Memória/Cloud Storage |
| Banco de Dados | SQLite Persistente | SQLite Memória |
| Performance | Rápido | Rápido |

## 🛠️ **Troubleshooting**

### **Erro de Memória**
```yaml
# Aumentar recursos no app.yaml
resources:
  cpu: 2
  memory_gb: 2
```

### **Erro de Timeout**
```yaml
# Ajustar timeout no app.yaml
automatic_scaling:
  target_cpu_utilization: 0.5
```

### **Erro de Dependências**
```bash
# Verificar requirements.txt
pip install -r requirements.txt
```

## 📊 **Monitoramento**

```bash
# Ver logs
gcloud app logs tail

# Ver métricas
gcloud app services list
```

## 🔐 **Segurança**

1. **SECRET_KEY**: Use uma chave forte e única
2. **Google Sheets**: Configure permissões adequadas
3. **Cloud Storage**: Configure IAM adequadamente
4. **HTTPS**: Sempre habilitado no GCP

## ✅ **Checklist de Deploy**

- [ ] Projeto GCP criado
- [ ] APIs habilitadas
- [ ] SECRET_KEY configurada
- [ ] Google Sheets configurado
- [ ] Teste local funcionando
- [ ] Deploy executado
- [ ] Teste em produção
- [ ] Monitoramento configurado

---

**🎯 Resultado**: Aplicação totalmente funcional no Google Cloud Platform com geração de PDF compatível!


