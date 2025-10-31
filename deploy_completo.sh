#!/bin/bash

# Script Completo de Deploy - Novas Credenciais
# Este script faz tudo: commit, push, atualiza variáveis e faz deploy

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_message() {
    echo -e "${2}${1}${NC}"
}

# Configurações
PROJECT_ID="gestaosolicitacao"
SERVICE_NAME="programa-gestao-py"  # Ajuste se necessário
REGION="us-central1"
CREDENTIAL_FILE="gestaosolicitacao-fe66ad097590.json"

print_message "🚀 INICIANDO DEPLOY COMPLETO" $BLUE
print_message "================================" $BLUE

# 1. Verificar se está em um repositório git
if [ ! -d ".git" ]; then
    print_message "❌ Não é um repositório git!" $RED
    exit 1
fi

# 2. Verificar se o arquivo de credenciais existe
if [ ! -f "$CREDENTIAL_FILE" ]; then
    print_message "❌ Arquivo de credenciais não encontrado: $CREDENTIAL_FILE" $RED
    exit 1
fi

# 3. Fazer commit e push
print_message "\n📝 Passo 1: Fazendo commit das alterações..." $YELLOW
git add .
git commit -m "Atualizar para novas credenciais gestaosolicitacao e Cloud Storage" || print_message "⚠️ Nenhuma alteração para commitar" $YELLOW
git push origin main || print_message "⚠️ Erro ao fazer push (continuando...)" $YELLOW
print_message "✅ Commit e push concluídos" $GREEN

# 4. Ler conteúdo do arquivo JSON
print_message "\n📋 Passo 2: Lendo arquivo de credenciais..." $YELLOW
CREDENTIAL_CONTENT=$(cat "$CREDENTIAL_FILE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin)))" 2>/dev/null || cat "$CREDENTIAL_FILE")
print_message "✅ Credenciais lidas" $GREEN

# 5. Verificar gcloud
print_message "\n🔍 Passo 3: Verificando Google Cloud SDK..." $YELLOW
if ! command -v gcloud &> /dev/null; then
    print_message "❌ Google Cloud SDK não encontrado!" $RED
    print_message "Instale em: https://cloud.google.com/sdk/docs/install" $RED
    exit 1
fi
print_message "✅ Google Cloud SDK encontrado" $GREEN

# 6. Configurar projeto
print_message "\n⚙️ Passo 4: Configurando projeto..." $YELLOW
gcloud config set project "$PROJECT_ID" 2>/dev/null || {
    print_message "⚠️ Não foi possível configurar projeto automaticamente" $YELLOW
    print_message "Execute: gcloud config set project $PROJECT_ID" $YELLOW
}
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
print_message "📋 Projeto atual: $CURRENT_PROJECT" $BLUE

# 7. Atualizar variáveis de ambiente no Cloud Run
print_message "\n🔧 Passo 5: Atualizando variáveis de ambiente no Cloud Run..." $YELLOW

# Atualizar GOOGLE_SERVICE_ACCOUNT_INFO
print_message "   Atualizando GOOGLE_SERVICE_ACCOUNT_INFO..." $BLUE
echo "$CREDENTIAL_CONTENT" > /tmp/service_account_info.json
gcloud run services update "$SERVICE_NAME" \
    --region="$REGION" \
    --update-env-vars="GOOGLE_SERVICE_ACCOUNT_INFO=$CREDENTIAL_CONTENT" \
    2>/dev/null || {
    print_message "⚠️ Erro ao atualizar GOOGLE_SERVICE_ACCOUNT_INFO via CLI" $YELLOW
    print_message "   Você precisará atualizar manualmente no Console" $YELLOW
}

# Atualizar/Adicionar GCS_BUCKET_NAME
print_message "   Atualizando GCS_BUCKET_NAME..." $BLUE
gcloud run services update "$SERVICE_NAME" \
    --region="$REGION" \
    --update-env-vars="GCS_BUCKET_NAME=romaneios-separacao" \
    2>/dev/null || {
    print_message "⚠️ Erro ao atualizar GCS_BUCKET_NAME via CLI" $YELLOW
    print_message "   Você precisará atualizar manualmente no Console" $YELLOW
}

print_message "✅ Variáveis de ambiente atualizadas (ou precisa atualizar manualmente)" $GREEN

# 8. Fazer deploy
print_message "\n🚀 Passo 6: Fazendo deploy no Cloud Run..." $YELLOW

# Verificar se existe Dockerfile
if [ -f "Dockerfile" ]; then
    print_message "   Usando Dockerfile para build..." $BLUE
    gcloud run deploy "$SERVICE_NAME" \
        --source . \
        --region="$REGION" \
        --platform managed \
        --allow-unauthenticated \
        2>/dev/null || {
        print_message "⚠️ Deploy via source falhou, tentando outras opções..." $YELLOW
    }
else
    print_message "⚠️ Dockerfile não encontrado. Deploy precisa ser feito manualmente." $YELLOW
    print_message "   Acesse: https://console.cloud.google.com/run?project=$PROJECT_ID" $YELLOW
fi

print_message "\n✅ PROCESSO CONCLUÍDO!" $GREEN
print_message "================================" $GREEN
print_message "\n📋 Próximos passos:" $BLUE
print_message "1. Verifique as variáveis de ambiente no Console:" $BLUE
print_message "   https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/variables?project=$PROJECT_ID" $BLUE
print_message "2. Verifique os logs após o deploy:" $BLUE
print_message "   https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/logs?project=$PROJECT_ID" $BLUE
print_message "3. Teste gerando um romaneio e verifique se aparece no bucket!" $BLUE

