# Script para verificar se as variaveis de ambiente do Cloud Storage estao configuradas
# Autor: Sistema de Gestao
# Data: 2025

Write-Host "`n=== VERIFICAR CONFIGURACAO CLOUD STORAGE NO CLOUD RUN ===" -ForegroundColor Cyan
Write-Host ""

# Configuracoes
$SERVICE_NAME = "programa-gestao-py"
$REGION = "us-central1"
$PROJECT_ID = "gestaosolicitacao"

# Cores
$GREEN = "Green"
$YELLOW = "Yellow"
$RED = "Red"
$BLUE = "Blue"

# Verificar se gcloud esta instalado
try {
    gcloud --version 2>&1 | Out-Null
    Write-Host "OK: gcloud CLI encontrado" -ForegroundColor $GREEN
} catch {
    Write-Host "ERRO: gcloud CLI nao encontrado!" -ForegroundColor $RED
    Write-Host "   Instale: https://cloud.google.com/sdk/docs/install" -ForegroundColor $YELLOW
    exit 1
}

# Configurar projeto
Write-Host "`nConfigurando projeto..." -ForegroundColor $BLUE
gcloud config set project $PROJECT_ID 2>&1 | Out-Null
Write-Host "OK: Projeto configurado: $PROJECT_ID" -ForegroundColor $GREEN

# Verificar se o servico existe
Write-Host "`nVerificando servico Cloud Run..." -ForegroundColor $BLUE
try {
    $serviceInfo = gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)" 2>&1
    if ($serviceInfo -match "ERROR") {
        Write-Host "ERRO: Servico nao encontrado: $SERVICE_NAME" -ForegroundColor $RED
        exit 1
    }
    Write-Host "OK: Servico encontrado: $SERVICE_NAME" -ForegroundColor $GREEN
    Write-Host "   URL: $serviceInfo" -ForegroundColor $BLUE
} catch {
    Write-Host "ERRO: Erro ao verificar servico: $_" -ForegroundColor $RED
    exit 1
}

# Obter todas as variaveis de ambiente
Write-Host "`nVerificando variaveis de ambiente..." -ForegroundColor $BLUE
try {
    $envVarsOutput = gcloud run services describe $SERVICE_NAME `
        --region=$REGION `
        --format="get(spec.template.spec.containers[0].env)" `
        2>&1
    
    Write-Host "`n========================================" -ForegroundColor $BLUE
    
    # Verificar GOOGLE_SERVICE_ACCOUNT_INFO
    $hasGoogleSA = $false
    $googleSALength = 0
    if ($envVarsOutput -match "GOOGLE_SERVICE_ACCOUNT_INFO") {
        $hasGoogleSA = $true
        Write-Host "   OK: GOOGLE_SERVICE_ACCOUNT_INFO: DEFINIDA" -ForegroundColor $GREEN
    } else {
        Write-Host "   ERRO: GOOGLE_SERVICE_ACCOUNT_INFO: NAO ENCONTRADA" -ForegroundColor $RED
        Write-Host "      Acao: Execute .\configurar_cloud_storage_cloud_run.ps1" -ForegroundColor $YELLOW
    }
    
    # Verificar GCS_BUCKET_NAME
    if ($envVarsOutput -match "GCS_BUCKET_NAME") {
        Write-Host "   OK: GCS_BUCKET_NAME: DEFINIDA" -ForegroundColor $GREEN
    } else {
        Write-Host "   ERRO: GCS_BUCKET_NAME: NAO ENCONTRADA" -ForegroundColor $RED
        Write-Host "      Acao: Execute .\configurar_cloud_storage_cloud_run.ps1" -ForegroundColor $YELLOW
    }
    
    Write-Host "`n========================================" -ForegroundColor $BLUE
    
    # Resumo
    Write-Host "`nRESUMO:" -ForegroundColor $BLUE
    if ($hasGoogleSA -and ($envVarsOutput -match "GCS_BUCKET_NAME")) {
        Write-Host "   OK: TUDO CONFIGURADO CORRETAMENTE!" -ForegroundColor $GREEN
        Write-Host "`n   Se ainda nao esta salvando, verifique:" -ForegroundColor $YELLOW
        Write-Host "   1. Logs do Cloud Run:" -ForegroundColor $YELLOW
        Write-Host "      https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/logs?project=$PROJECT_ID" -ForegroundColor $BLUE
        Write-Host "   2. Permissoes da Service Account no bucket" -ForegroundColor $YELLOW
        Write-Host "   3. Se o bucket romaneios-separacao existe" -ForegroundColor $YELLOW
    } else {
        Write-Host "   ERRO: CONFIGURACAO INCOMPLETA!" -ForegroundColor $RED
        Write-Host "`n   Execute o script de configuracao:" -ForegroundColor $YELLOW
        Write-Host "   .\configurar_cloud_storage_cloud_run.ps1" -ForegroundColor $BLUE
    }
    
} catch {
    Write-Host "ERRO: Erro ao verificar variaveis: $_" -ForegroundColor $RED
    exit 1
}

Write-Host "`n=== VERIFICACAO CONCLUIDA ===" -ForegroundColor Cyan
Write-Host ""
