# Script Seguro para Fazer Commit
# Este script mostra o que será commitado ANTES de fazer qualquer coisa

Write-Host "🔒 VERIFICAÇÃO DE SEGURANÇA ANTES DO COMMIT" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green
Write-Host ""

# 1. Verificar se arquivo de credenciais está protegido
Write-Host "1️⃣ Verificando proteção de credenciais..." -ForegroundColor Yellow
$credFile = "gestaosolicitacao-fe66ad097590.json"
$gitStatus = git status --porcelain $credFile 2>&1

if ($gitStatus -match "gestaosolicitacao") {
    Write-Host "❌ PERIGO! Arquivo de credenciais pode ser commitado!" -ForegroundColor Red
    Write-Host "   CANCELANDO por segurança!" -ForegroundColor Red
    exit 1
} else {
    Write-Host "✅ Arquivo de credenciais está PROTEGIDO (.gitignore)" -ForegroundColor Green
}

Write-Host ""
Write-Host "2️⃣ Arquivos que SERÃO commitados:" -ForegroundColor Yellow
Write-Host ""

# Mostrar arquivos modificados
Write-Host "   📝 Arquivos MODIFICADOS:" -ForegroundColor Cyan
git status --porcelain | Where-Object { $_ -match "^ M" } | ForEach-Object {
    $file = ($_ -replace "^ M ", "").Trim()
    Write-Host "      ✅ $file" -ForegroundColor White
}

# Mostrar arquivos novos
Write-Host ""
Write-Host "   📄 Arquivos NOVOS:" -ForegroundColor Cyan
git status --porcelain | Where-Object { $_ -match "^\?\?" } | ForEach-Object {
    $file = ($_ -replace "^\?\? ", "").Trim()
    # Filtrar arquivos de teste e PDFs
    if ($file -notmatch "testar_.*\.py|\.pdf$|deploy_completo") {
        Write-Host "      ✅ $file" -ForegroundColor White
    } else {
        Write-Host "      ⚠️  $file (será IGNORADO)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "3️⃣ Preparando arquivos para commit..." -ForegroundColor Yellow

# Adicionar apenas arquivos seguros
Write-Host "   Adicionando arquivos modificados..." -ForegroundColor Blue
git add app.py
git add salvar_pdf_gcs.py
git add pdf_cloud_generator.py
git add CONFIGURACAO_PLANILHA.md
git add CONFIGURAR_ARMAZENAMENTO_NUVEM.md
git add CONFIGURAR_CLOUD_RUN.md
git add README.md
git add README_DEPLOY.md
git add SISTEMA_COMPLETO.md

Write-Host "   Adicionando documentação nova..." -ForegroundColor Blue
git add DEPLOY_CREDENCIAIS.md
git add DEPLOY_SIMPLES.md
git add SOLUCAO_CLOUD_STORAGE.md
git add VERIFICAR_CONFIGURACAO.md
git add COMMIT_SEGURO.md

Write-Host ""
Write-Host "4️⃣ RESUMO FINAL - O que será commitado:" -ForegroundColor Yellow
Write-Host ""
git status --short

Write-Host ""
Write-Host "5️⃣ Deseja continuar com o commit?" -ForegroundColor Yellow
Write-Host "   Digite 'SIM' para confirmar ou qualquer outra coisa para cancelar:" -ForegroundColor White
$confirmacao = Read-Host

if ($confirmacao -eq "SIM") {
    Write-Host ""
    Write-Host "💾 Fazendo commit..." -ForegroundColor Green
    $commitMsg = @"
Atualizar para novas credenciais gestaosolicitacao e Cloud Storage

- Atualizar app.py para sempre salvar PDFs no Cloud Storage
- Atualizar salvar_pdf_gcs.py para usar credenciais locais
- Atualizar documentação com novas referências
- Adicionar guias de deploy e verificação
"@
    git commit -m $commitMsg

    Write-Host ""
    Write-Host "✅ Commit realizado com sucesso!" -ForegroundColor Green
    Write-Host ""
    Write-Host "6️⃣ Deseja fazer PUSH para o GitHub?" -ForegroundColor Yellow
    Write-Host "   Digite 'SIM' para enviar ou qualquer outra coisa para cancelar:" -ForegroundColor White
    $push = Read-Host

    if ($push -eq "SIM") {
        Write-Host ""
        Write-Host "📤 Enviando para GitHub..." -ForegroundColor Green
        git push origin main
        Write-Host ""
        Write-Host "✅ Push concluído com sucesso!" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "⚠️ Push cancelado. Execute manualmente quando quiser:" -ForegroundColor Yellow
        Write-Host "   git push origin main" -ForegroundColor Cyan
    }
} else {
    Write-Host ""
    Write-Host "❌ Commit cancelado. Nada foi alterado." -ForegroundColor Yellow
    Write-Host "   Execute 'git restore --staged .' se quiser desfazer o staging" -ForegroundColor Cyan
}

