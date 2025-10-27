# 🚀 Guia de Deploy - Google Cloud Platform

Este guia explica como fazer o deploy manual do Sistema de Gestão de Estoque no Google Cloud Platform usando GitHub.

## 📋 Pré-requisitos

1. **Conta no Google Cloud Platform** (com projeto criado)
2. **Conta no GitHub**
3. **Google Cloud SDK** instalado localmente
4. **Credenciais do Google Sheets** (arquivo JSON)

---

## 🔧 Passo 1: Preparar o Projeto Local

### 1.1. Commit das alterações no Git

```bash
# Verificar status
git status

# Adicionar arquivos
git add .

# Commit
git commit -m "Preparação para deploy no Google Cloud"

# Push (se já tiver repositório remoto)
git push origin main
```

---

## 📤 Passo 2: Criar/Acessar Repositório no GitHub

### 2.1. Criar repositório no GitHub

1. Acesse: https://github.com/new
2. Nome do repositório: `sistema-gestao-estoque` (ou outro)
3. Escolha **Público** ou **Privado**
4. **NÃO inicialize com README** (já temos arquivos)
5. Clique em **Create repository**

### 2.2. Fazer push do código

```bash
# Se ainda não tiver repositório remoto
git remote add origin https://github.com/SEU-USUARIO/NOME-DO-REPO.git

# Push inicial
git branch -M main
git push -u origin main
```

---

## ☁️ Passo 3: Configurar Google Cloud

### 3.1. Instalar Google Cloud SDK

**Windows:**
```bash
# Baixar de: https://cloud.google.com/sdk/docs/install
# Executar instalador .exe
```

**Verificar instalação:**
```bash
gcloud --version
```

### 3.2. Login no Google Cloud

```bash
gcloud auth login
# Abrirá o navegador para autenticar
```

### 3.3. Criar/Acessar Projeto

```bash
# Listar projetos
gcloud projects list

# Selecionar projeto existente
gcloud config set project SEU-PROJECT-ID

# OU criar novo projeto
gcloud projects create seu-project-id --name="Sistema Gestão Estoque"
gcloud config set project seu-project-id
```

### 3.4. Habilitar APIs necessárias

```bash
gcloud services enable appengine.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

---

## 🔑 Passo 4: Configurar Credenciais do Google Sheets

### 4.1. Fazer upload do arquivo JSON no Cloud Storage

```bash
# Criar bucket (se não existir)
gsutil mb gs://seu-bucket-credenciais

# Upload do arquivo JSON (adicionar manualmente no Console)
# Console: Storage > Browser > Upload > selecionar arquivo JSON
# OU via CLI:
# gsutil cp sistema-consulta-produtos-*.json gs://seu-bucket-credenciais/
```

### 4.2. Configurar variáveis de ambiente

**Opção A: Via Console (Recomendado)**

1. Acesse: https://console.cloud.google.com/appengine
2. Vá em **Settings** > **Environment Variables**
3. Adicione:
   - `SECRET_KEY`: gere um valor aleatório seguro
   - `DATABASE_URL`: SQLite local (por enquanto)
   - Configure acesso ao Google Sheets via Service Account

**Opção B: Via arquivo `app.yaml`**

Edite o `app.yaml` e adicione as variáveis de ambiente necessárias.

---

## 🚀 Passo 5: Deploy no Google Cloud

### 5.1. Primeiro deploy

```bash
# No diretório do projeto
gcloud app deploy

# Responder 'Y' quando pedir para criar app
# Selecionar região (ex: us-central)
```

### 5.2. Aguardar conclusão

O deploy pode levar 5-10 minutos na primeira vez.

### 5.3. Acessar aplicação

```bash
# Obter URL
gcloud app browse

# OU acesse diretamente:
# https://SEU-PROJECT-ID.appspot.com
```

---

## 🔧 Configurações Importantes

### Adicionar arquivo JSON de credenciais

1. No Console do Cloud, crie um **Secret Manager**
2. Armazene o conteúdo do JSON como variável de ambiente
3. Configure no app para ler via Cloud Storage ou Secret Manager

### Configurar Cloud SQL (Opcional - para produção)

1. Criar instância Cloud SQL (MySQL)
2. Atualizar `DATABASE_URL` no `app.yaml`
3. Adicionar variável `CLOUD_SQL_CONNECTION_NAME`

---

## 📝 Notas Importantes

⚠️ **CRÍTICO:**
- **NUNCA commite** arquivos `.json` com credenciais no GitHub
- Use `.gitignore` para protegê-los
- No Google Cloud, use Secret Manager para credenciais

🔒 **Segurança:**
- Gere `SECRET_KEY` forte para produção
- Use HTTPS (automático no App Engine)
- Configure `login: required` no `app.yaml`

📊 **Monitoring:**
- Acesse logs: `gcloud app logs tail`
- Cloud Console mostra erros e métricas

---

## 🆘 Troubleshooting

### Erro: "No project found"
```bash
gcloud projects list
gcloud config set project SEU-PROJECT-ID
```

### Erro: "Permission denied"
```bash
gcloud auth login
gcloud auth application-default login
```

### Erro: Import errors no deploy
- Verifique `requirements.txt`
- Teste localmente: `pip install -r requirements.txt`

### App Engine não inicia
```bash
gcloud app logs tail
# Verificar logs para erros
```

---

## 📚 Próximos Passos

1. ✅ Deploy funcional
2. 🔄 Configurar Cloud SQL
3. 🔄 Migrar credenciais para Secret Manager
4. 🔄 Configurar domínio customizado (opcional)
5. 🔄 Configurar CI/CD automático (opcional)

---

## 🎯 Resumo do Processo

```
1. git commit & push → GitHub
2. gcloud auth login
3. gcloud config set project
4. gcloud app deploy
5. Configurar credenciais
6. Acessar: https://SEU-APP.appspot.com
```

**🎉 Pronto! Seu sistema está no ar!**

