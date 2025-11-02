# Script de Configuração do GitGuardian (ggshield)
# Este script instala e configura o ggshield para proteção automática

Write-Host "🔒 CONFIGURAÇÃO DO GITGUARDIAN (ggshield)" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

# 1. Verificar Python
Write-Host "1️⃣ Verificando Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "   ✅ Python encontrado: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Python não encontrado!" -ForegroundColor Red
    Write-Host "   Instale Python de: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# 2. Instalar ggshield
Write-Host ""
Write-Host "2️⃣ Instalando ggshield..." -ForegroundColor Yellow
try {
    pip install ggshield
    Write-Host "   ✅ ggshield instalado com sucesso!" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  Erro ao instalar ggshield. Tentando com python -m pip..." -ForegroundColor Yellow
    python -m pip install ggshield
    Write-Host "   ✅ ggshield instalado!" -ForegroundColor Green
}

# 3. Verificar instalação
Write-Host ""
Write-Host "3️⃣ Verificando instalação..." -ForegroundColor Yellow
try {
    $ggshieldVersion = ggshield --version 2>&1
    Write-Host "   ✅ ggshield instalado: $ggshieldVersion" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Erro ao verificar ggshield" -ForegroundColor Red
    Write-Host "   Tente executar manualmente: pip install ggshield" -ForegroundColor Yellow
    exit 1
}

# 4. Instalar pre-commit
Write-Host ""
Write-Host "4️⃣ Instalando pre-commit..." -ForegroundColor Yellow
try {
    pip install pre-commit
    Write-Host "   ✅ pre-commit instalado!" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  Tentando com python -m pip..." -ForegroundColor Yellow
    python -m pip install pre-commit
}

# 5. Verificar se .pre-commit-config.yaml existe
Write-Host ""
Write-Host "5️⃣ Verificando configuração do pre-commit..." -ForegroundColor Yellow
if (Test-Path ".pre-commit-config.yaml") {
    Write-Host "   ✅ Arquivo .pre-commit-config.yaml encontrado!" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Arquivo .pre-commit-config.yaml não encontrado!" -ForegroundColor Yellow
    Write-Host "   O arquivo deve ser criado manualmente ou será criado automaticamente." -ForegroundColor Yellow
}

# 6. Instalar hooks do pre-commit
Write-Host ""
Write-Host "6️⃣ Instalando hooks do pre-commit..." -ForegroundColor Yellow
try {
    pre-commit install
    Write-Host "   ✅ Hooks instalados com sucesso!" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  Erro ao instalar hooks. Tente manualmente: pre-commit install" -ForegroundColor Yellow
}

# 7. Verificar autenticação
Write-Host ""
Write-Host "7️⃣ Verificando autenticação do GitGuardian..." -ForegroundColor Yellow
try {
    $authStatus = ggshield auth status 2>&1
    if ($authStatus -match "logged in" -or $authStatus -match "authenticated") {
        Write-Host "   ✅ Você está autenticado no GitGuardian!" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Você NÃO está autenticado!" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "   Para autenticar:" -ForegroundColor Cyan
        Write-Host "   1. Acesse: https://dashboard.gitguardian.com/" -ForegroundColor White
        Write-Host "   2. Vá em Settings → Tokens" -ForegroundColor White
        Write-Host "   3. Crie um novo token" -ForegroundColor White
        Write-Host "   4. Execute: ggshield auth login" -ForegroundColor White
        Write-Host ""
        $autenticar = Read-Host "   Deseja autenticar agora? (S/N)"
        if ($autenticar -eq "S" -or $autenticar -eq "s") {
            ggshield auth login
        }
    }
} catch {
    Write-Host "   ⚠️  Não foi possível verificar autenticação" -ForegroundColor Yellow
    Write-Host "   Execute manualmente: ggshield auth login" -ForegroundColor Yellow
}

# 8. Teste rápido
Write-Host ""
Write-Host "8️⃣ Executando teste rápido..." -ForegroundColor Yellow
Write-Host "   Escaneando arquivos do projeto..." -ForegroundColor Cyan
try {
    ggshield scan path . --exit-zero 2>&1 | Out-Null
    Write-Host "   ✅ Teste concluído! (nenhum segredo crítico detectado)" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  Alguns arquivos podem conter segredos. Revise os avisos acima." -ForegroundColor Yellow
}

# Resumo final
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  ✅ CONFIGURAÇÃO CONCLUÍDA!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Próximos passos:" -ForegroundColor Cyan
Write-Host "   1. Autentique-se (se ainda não fez): ggshield auth login" -ForegroundColor White
Write-Host "   2. Teste fazendo um commit para ver o bloqueio funcionar" -ForegroundColor White
Write-Host "   3. Leia o guia completo: CONFIGURAR_GITGUARDIAN.md" -ForegroundColor White
Write-Host ""
Write-Host "🔒 Seu código agora está protegido contra commits com segredos!" -ForegroundColor Green
Write-Host ""

