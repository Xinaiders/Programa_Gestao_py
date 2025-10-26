#!/bin/bash

# Script de Deploy para Google Cloud Run
# Sistema de Gestão de Estoque

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para imprimir mensagens coloridas
print_message() {
    echo -e "${2}${1}${NC}"
}

# Verificar se o gcloud está instalado
check_gcloud() {
    if ! command -v gcloud &> /dev/null; then
        print_message "❌ Google Cloud SDK não encontrado. Instale em: https://cloud.google.com/sdk/docs/install" $RED
        exit 1
    fi
    print_message "✅ Google Cloud SDK encontrado" $GREEN
}

# Verificar se o Docker está instalado
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_message "❌ Docker não encontrado. Instale em: https://docs.docker.com/get-docker/" $RED
        exit 1
    fi
    print_message "✅ Docker encontrado" $GREEN
}

# Configurar projeto
setup_project() {
    print_message "🔧 Configurando projeto..." $BLUE
    
    # Obter PROJECT_ID
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    if [ -z "$PROJECT_ID" ]; then
        print_message "❌ Nenhum projeto configurado. Execute: gcloud config set project SEU_PROJECT_ID" $RED
        exit 1
    fi
    
    print_message "📋 Projeto: $PROJECT_ID" $YELLOW
    
    # Habilitar APIs necessárias
    print_message "🔌 Habilitando APIs necessárias..." $BLUE
    gcloud services enable cloudbuild.googleapis.com
    gcloud services enable run.googleapis.com
    gcloud services enable containerregistry.googleapis.com
}

# Construir e enviar imagem
build_and_push() {
    print_message "🏗️ Construindo imagem Docker..." $BLUE
    
    IMAGE_NAME="gcr.io/$PROJECT_ID/gestao-estoque"
    TAG=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
    
    # Construir imagem
    docker build -t $IMAGE_NAME:$TAG .
    docker tag $IMAGE_NAME:$TAG $IMAGE_NAME:latest
    
    # Configurar Docker para usar gcloud
    gcloud auth configure-docker
    
    # Enviar imagem
    print_message "📤 Enviando imagem para Container Registry..." $BLUE
    docker push $IMAGE_NAME:$TAG
    docker push $IMAGE_NAME:latest
    
    print_message "✅ Imagem enviada: $IMAGE_NAME:$TAG" $GREEN
}

# Deploy no Cloud Run
deploy_to_cloud_run() {
    print_message "🚀 Fazendo deploy no Cloud Run..." $BLUE
    
    IMAGE_NAME="gcr.io/$PROJECT_ID/gestao-estoque"
    
    gcloud run deploy gestao-estoque \
        --image $IMAGE_NAME:latest \
        --platform managed \
        --region us-central1 \
        --allow-unauthenticated \
        --port 8080 \
        --memory 512Mi \
        --cpu 1 \
        --max-instances 10 \
        --set-env-vars FLASK_ENV=production \
        --set-env-vars SECRET_KEY=$(openssl rand -base64 32)
    
    print_message "✅ Deploy concluído!" $GREEN
}

# Obter URL do serviço
get_service_url() {
    SERVICE_URL=$(gcloud run services describe gestao-estoque --platform managed --region us-central1 --format 'value(status.url)')
    print_message "🌐 URL do serviço: $SERVICE_URL" $GREEN
    print_message "👤 Usuário padrão: admin" $YELLOW
    print_message "🔑 Senha padrão: admin123" $YELLOW
}

# Função principal
main() {
    print_message "🚀 Iniciando deploy do Sistema de Gestão de Estoque" $BLUE
    print_message "=================================================" $BLUE
    
    check_gcloud
    check_docker
    setup_project
    build_and_push
    deploy_to_cloud_run
    get_service_url
    
    print_message "🎉 Deploy concluído com sucesso!" $GREEN
}

# Executar se chamado diretamente
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
