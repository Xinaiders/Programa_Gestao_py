# Script Completo de Deploy - Windows PowerShell
# Este script faz tudo: commit, push, atualiza variáveis e faz deploy

$ErrorActionPreference = "Stop"

# Configurações
$PROJECT_ID = "gestaosolicitacao"
$SERVICE_NAME = "programa-gestao-py"
$REGION = "us-central1"
$CREDENTIAL_FILE = "gestaosolicitacao-fe66ad097590.json"

Write-Host "🚀 INICIANDO DEPLOY COMPLETO" -ForegroundColor Blue
Write-Host "================================" -ForegroundColor Blue

# 1. Verificar git
if (-not (Test-Path ".git")) {
    Write-Host "❌ Não é um repositório git!" -ForegroundColor Red
    exit 1
}

# 2. Verificar arquivo de credenciais
if (-not (Test-Path $CREDENTIAL_FILE)) {
    Write-Host "❌ Arquivo de credenciais não encontrado: $CREDENTIAL_FILE" -ForegroundColor Red
    exit 1
}

# 3. Commit e push
Write-Host "`n📝 Passo 1: Fazendo commit das alterações..." -ForegroundColor Yellow
try {
    git add .
    git commit -m "Atualizar para novas credenciais gestaosolicitacao e Cloud Storage"
    Write-Host "✅ Alterações commitadas" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Nenhuma alteração para commitar和谐" -ForegroundColor Yellow
}

try {
    git push origin main
    Write-Host "✅ Push concluído" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Erro ao fazer push (continuando...)" -ForegroundColor Yellow
}

# 4. Ler arquivo JSON
Write-Host "`n📋 Passo 2: Lendo arquivo de credenciais..." -ForegroundColor Yellow
$CREDENTIAL_CONTENT = Get-Content $CREDENTIAL_FILE -Raw
Write-Host "✅ Credenciais lidas" -ForegroundColor Green

# 5. Verificar gcloud
Write-Host "`n🔍 Passo 3: Verificando Google Cloud SDK..." -ForegroundColor Yellow
try {
    $null = gcloud --version 2>&1
    Write-Host "✅ Google Cloud SDK encontrado" -ForegroundColor Green
} catch {
    Write-Host "❌ Google Cloud SDK não encontrado!" -ForegroundColor Red
    Write-Host "Instale em: https://cloud.google.com/sdk/docs/install" -ForegroundColor Red
    exit 1
}

# 6. Configurar projeto
Write-Host "`n⚙️ Passo 4: Configurando projeto..." -ForegroundColor Yellow
gcloud config set project $PROJECT_ID 2>&1 | Out-Null
$CURRENT_PROJECT = gcloud config get-value project 2>&1
Write-Host "📋 Projeto: $CURRENT_PROJECT" -ForegroundColor Blue

# 7. Atualizar variáveis
Write-Host "`n🔧 Passo 5: Atualizando variáveis de ambiente..." -ForegroundColor Yellow

Write-Host "   Atualizando GOOGLE_SERVICE_ACCOUNT_INFO..." -ForegroundColor Blue
$env:GOOGLE_CREDENTIALS = $CREDENTIAL_CONTENT
gcloud run services update $SERVICE_NAME --region=$REGION --update-env-vars="GOOGLE_SERVICE_ACCOUNT_INFO=$CREDENTIAL_CONTENT" 2>&1 | Out-Null

Write-Host "   Atualizando GCS_BUCKET_NAME..." -ForegroundColor Blue
gcloud run services update $SERVICE_NAME --region=$REGION --update-env-vars="GCS_BUCKET_NAME=romaneios-separacao" 2>&1 | Out-Null

Write-Host "✅ Variáveis atualizadas" -ForegroundColor Green

# 8. Deploy
Write-Host "`n🚀 Passo 6: Fazendo deploy..." -ForegroundColor Yellow
if (Test-Path "Dockerfile") {
    gcloud run deploy $SERVICE_NAME --source . --region=$REGION --platform managed --allow-unauthenticated
    Write-Host "✅ Deploy concluído!" -ForegroundColor Green
} else {
    Write-Host "⚠️ Dockerfile não encontrado" -ForegroundColor Yellow
}

Write-Host "`n✅ PROCESSO CONCLUÍDO!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host "`n📋 Próximos passos:" -ForegroundColor Blue
Write-Host "1. Verifique as variáveis no Console" -ForegroundColor Blue
Write-Host "2. Verifique os logs" -ForegroundColor Blue
Write-Host "3. Teste gerando um romaneio!" -ForegroundColor Blue
