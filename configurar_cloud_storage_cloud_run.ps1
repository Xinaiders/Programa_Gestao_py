# Script para configurar variáveis de ambiente do Cloud Storage no Cloud Run
# Autor: Sistema de Gestão
# Data: 2025

Write-Host "`n=== CONFIGURAR CLOUD STORAGE NO CLOUD RUN ===" -ForegroundColor Cyan
Write-Host ""

# Configurações
$SERVICE_NAME = "programa-gestao-py"
$REGION = "us-central1"
$PROJECT_ID = "gestaosolicitacao"
$CREDENTIAL_FILE = "gestaosolicitacao-fe66ad097590.json"
$BUCKET_NAME = "romaneios-separacao"

# Cores
$GREEN = "Green"
$YELLOW = "Yellow"
$RED = "Red"
$BLUE = "Blue"

# Verificar se está no diretório correto
if (-not (Test-Path $CREDENTIAL_FILE)) {
    Write-Host "❌ ERRO: Arquivo de credenciais não encontrado: $CREDENTIAL_FILE" -ForegroundColor $RED
    Write-Host "   Certifique-se de estar no diretório do projeto!" -ForegroundColor $YELLOW
    exit 1
}

# Verificar se gcloud está instalado
try {
    gcloud --version 2>&1 | Out-Null
    Write-Host "✅ gcloud CLI encontrado" -ForegroundColor $GREEN
} catch {
    Write-Host "❌ ERRO: gcloud CLI não encontrado!" -ForegroundColor $RED
    Write-Host "   Instale: https://cloud.google.com/sdk/docs/install" -ForegroundColor $YELLOW
    exit 1
}

# Verificar se está autenticado
Write-Host "`n🔐 Verificando autenticação..." -ForegroundColor $BLUE
try {
    $currentAccount = gcloud config get-value account 2>&1
    if ($currentAccount -match "ERROR") {
        Write-Host "⚠️ Não autenticado. Fazendo login..." -ForegroundColor $YELLOW
        gcloud auth login
    } else {
        Write-Host "✅ Autenticado como: $currentAccount" -ForegroundColor $GREEN
    }
} catch {
    Write-Host "❌ Erro ao verificar autenticação" -ForegroundColor $RED
    exit 1
}

# Configurar projeto
Write-Host "`n📦 Configurando projeto..." -ForegroundColor $BLUE
gcloud config set project $PROJECT_ID 2>&1 | Out-Null
Write-Host "✅ Projeto configurado: $PROJECT_ID" -ForegroundColor $GREEN

# Passo 1: Ler e converter credenciais JSON
Write-Host "`n📋 Passo 1: Processando credenciais..." -ForegroundColor $BLUE
try {
    # Ler o arquivo JSON
    $jsonContent = Get-Content $CREDENTIAL_FILE -Raw -Encoding UTF8
    
    # Converter para JSON e depois de volta para garantir formato válido (uma linha)
    $jsonObject = $jsonContent | ConvertFrom-Json
    $jsonOneLine = $jsonObject | ConvertTo-Json -Compress -Depth 10
    
    # Escapar caracteres especiais para PowerShell (especialmente $)
    $jsonOneLine = $jsonOneLine -replace '\$', '`$'
    
    Write-Host "✅ Credenciais processadas (tamanho: $($jsonOneLine.Length) caracteres)" -ForegroundColor $GREEN
} catch {
    Write-Host "❌ ERRO ao processar arquivo JSON: $_" -ForegroundColor $RED
    exit 1
}

# Passo 2: Verificar se o serviço existe
Write-Host "`n🔍 Passo 2: Verificando serviço Cloud Run..." -ForegroundColor $BLUE
try {
    $serviceInfo = gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)" 2>&1
    if ($serviceInfo -match "ERROR") {
        Write-Host "❌ Serviço não encontrado: $SERVICE_NAME" -ForegroundColor $RED
        Write-Host "   Certifique-se que o serviço foi implantado primeiro!" -ForegroundColor $YELLOW
        exit 1
    }
    Write-Host "✅ Serviço encontrado: $SERVICE_NAME" -ForegroundColor $GREEN
} catch {
    Write-Host "❌ Erro ao verificar serviço: $_" -ForegroundColor $RED
    exit 1
}

# Passo 3: Atualizar variável GOOGLE_SERVICE_ACCOUNT_INFO
Write-Host "`n☁️ Passo 3: Configurando GOOGLE_SERVICE_ACCOUNT_INFO..." -ForegroundColor $BLUE
Write-Host "   (Isso pode levar alguns segundos...)" -ForegroundColor $YELLOW
Write-Host "   ⚠️ IMPORTANTE: Usando --update-env-vars para não sobrescrever outras variáveis!" -ForegroundColor $YELLOW
try {
    # Usar --update-env-vars para adicionar/atualizar SEM remover outras variáveis
    # --set-env-vars SUBSTITUI todas as variáveis (problema que causava perda de outras configs)
    $result1 = gcloud run services update $SERVICE_NAME `
        --region=$REGION `
        --update-env-vars="GOOGLE_SERVICE_ACCOUNT_INFO=$jsonOneLine" `
        2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Variável GOOGLE_SERVICE_ACCOUNT_INFO configurada/atualizada com sucesso!" -ForegroundColor $GREEN
    } else {
        Write-Host "❌ ERRO ao configurar GOOGLE_SERVICE_ACCOUNT_INFO" -ForegroundColor $RED
        Write-Host "   Erro: $result1" -ForegroundColor $RED
        exit 1
    }
} catch {
    Write-Host "❌ ERRO ao configurar GOOGLE_SERVICE_ACCOUNT_INFO: $_" -ForegroundColor $RED
    exit 1
}

# Passo 4: Atualizar variável GCS_BUCKET_NAME
Write-Host "`n📦 Passo 4: Configurando GCS_BUCKET_NAME..." -ForegroundColor $BLUE
try {
    $envVar2 = "GCS_BUCKET_NAME=$BUCKET_NAME"
    $result2 = gcloud run services update $SERVICE_NAME `
        --region=$REGION `
        --update-env-vars="$envVar2" `
        2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Variável GCS_BUCKET_NAME configurada: $BUCKET_NAME" -ForegroundColor $GREEN
    } else {
        Write-Host "❌ ERRO ao configurar GCS_BUCKET_NAME" -ForegroundColor $RED
        Write-Host "   Erro: $result2" -ForegroundColor $RED
        exit 1
    }
} catch {
    Write-Host "❌ ERRO ao configurar GCS_BUCKET_NAME: $_" -ForegroundColor $RED
    exit 1
}

# Passo 5: Verificar variáveis configuradas
Write-Host "`n🔍 Passo 5: Verificando variáveis configuradas..." -ForegroundColor $BLUE
try {
    $envVars = gcloud run services describe $SERVICE_NAME `
        --region=$REGION `
        --format="value(spec.template.spec.containers[0].env)" `
        2>&1
    
    Write-Host "`n📋 Variáveis de ambiente configuradas:" -ForegroundColor $BLUE
    
    if ($envVars -match "GOOGLE_SERVICE_ACCOUNT_INFO") {
        Write-Host "   ✅ GOOGLE_SERVICE_ACCOUNT_INFO: DEFINIDA" -ForegroundColor $GREEN
    } else {
        Write-Host "   ❌ GOOGLE_SERVICE_ACCOUNT_INFO: NÃO ENCONTRADA" -ForegroundColor $RED
    }
    
    if ($envVars -match "GCS_BUCKET_NAME") {
        Write-Host "   ✅ GCS_BUCKET_NAME: DEFINIDA" -ForegroundColor $GREEN
    } else {
        Write-Host "   ❌ GCS_BUCKET_NAME: NÃO ENCONTRADA" -ForegroundColor $RED
    }
    
} catch {
    Write-Host "⚠️ Não foi possível verificar variáveis: $_" -ForegroundColor $YELLOW
}

# Passo 6: Verificar permissões no bucket
Write-Host "`n🔐 Passo 6: Verificando permissões no bucket..." -ForegroundColor $BLUE
try {
    $serviceAccountEmail = "gestsolicitacao@gestaosolicitacao.iam.gserviceaccount.com"
    Write-Host "   Service Account: $serviceAccountEmail" -ForegroundColor $BLUE
    
    Write-Host "   ⚠️ Verifique manualmente se a service account tem as permissões:" -ForegroundColor $YELLOW
    Write-Host "      - Storage Object Creator" -ForegroundColor $YELLOW
    Write-Host "      - Storage Object Viewer" -ForegroundColor $YELLOW
    Write-Host "   Link: https://console.cloud.google.com/iam-admin/iam?project=$PROJECT_ID" -ForegroundColor $BLUE
} catch {
    Write-Host "⚠️ Não foi possível verificar permissões" -ForegroundColor $YELLOW
}

# Resumo final
Write-Host "`n=== CONFIGURAÇÃO CONCLUÍDA ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ Variáveis de ambiente configuradas no Cloud Run!" -ForegroundColor $GREEN
Write-Host ""
Write-Host "📝 Próximos passos:" -ForegroundColor $BLUE
Write-Host "   1. Aguarde alguns segundos para o Cloud Run atualizar" -ForegroundColor White
Write-Host "   2. Teste criando um romaneio em:" -ForegroundColor White
Write-Host "      https://programa-gestao-py-661879898685.us-central1.run.app/" -ForegroundColor White
Write-Host "   3. Verifique os logs em:" -ForegroundColor White
Write-Host "      https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/logs?project=$PROJECT_ID" -ForegroundColor White
Write-Host ""
Write-Host "🔍 Nos logs, procure por:" -ForegroundColor $BLUE
Write-Host "   ✅ '✅ Credenciais carregadas da variável de ambiente'" -ForegroundColor $GREEN
Write-Host "   ✅ '✅ PDF salvo no Cloud Storage'" -ForegroundColor $GREEN
Write-Host "   ❌ '❌ ERRO' (se houver problemas)" -ForegroundColor $RED
Write-Host ""

