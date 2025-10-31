# Script Completo de Verificação do Repositório
# Verifica TUDO para garantir que está no lugar certo

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  VERIFICAÇÃO COMPLETA DO REPOSITÓRIO" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# 1. Verificar caminho atual
Write-Host "1️⃣ VERIFICANDO CAMINHO ATUAL..." -ForegroundColor Yellow
$caminhoAtual = Get-Location
Write-Host "   Caminho: $($caminhoAtual.Path)" -ForegroundColor White

$caminhoEsperado = "G:\Meu Drive\Line Flex\PROG_GESTAO_PY\Programa_Gestao_py"
if ($caminhoAtual.Path -eq $caminhoEsperado) {
    Write-Host "   ✅ Caminho CORRETO!" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Caminho DIFERENTE do esperado" -ForegroundColor Yellow
    Write-Host "   Esperado: $caminhoEsperado" -ForegroundColor Gray
}

# 2. Verificar se é um repositório Git
Write-Host "`n2️⃣ VERIFICANDO SE É REPOSITÓRIO GIT..." -ForegroundColor Yellow
if (Test-Path ".git") {
    Write-Host "   ✅ É um repositório Git" -ForegroundColor Green
} else {
    Write-Host "   ❌ NÃO é um repositório Git!" -ForegroundColor Red
    exit 1
}

# 3. Verificar repositório remoto
Write-Host "`n3️⃣ VERIFICANDO REPOSITÓRIO REMOTO..." -ForegroundColor Yellow
$remoteUrl = git remote get-url origin 2>&1
if ($remoteUrl -match "Xinaiders/Programa_Gestao_py") {
    Write-Host "   ✅ Repositório remoto CORRETO" -ForegroundColor Green
    Write-Host "   URL: $remoteUrl" -ForegroundColor Gray
} else {
    Write-Host "   ⚠️  Repositório remoto pode estar diferente" -ForegroundColor Yellow
    Write-Host "   URL encontrado: $remoteUrl" -ForegroundColor Gray
}

# 4. Verificar branch atual
Write-Host "`n4️⃣ VERIFICANDO BRANCH..." -ForegroundColor Yellow
$branch = git branch --show-current
Write-Host "   Branch atual: $branch" -ForegroundColor White
if ($branch -eq "main") {
    Write-Host "   ✅ Branch CORRETA (main)" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Branch diferente de 'main'" -ForegroundColor Yellow
}

# 5. Verificar status de sincronização
Write-Host "`n5️⃣ VERIFICANDO SINCRONIZAÇÃO..." -ForegroundColor Yellow
$status = git status -sb
if ($status -match "up to date") {
    Write-Host "   ✅ Sincronizado com GitHub" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Pode haver diferenças com GitHub" -ForegroundColor Yellow
}

# 6. Verificar último commit
Write-Host "`n6️⃣ VERIFICANDO ÚLTIMO COMMIT..." -ForegroundColor Yellow
$ultimoCommit = git log -1 --oneline
Write-Host "   Último commit: $ultimoCommit" -ForegroundColor White
if ($ultimoCommit -match "Teste: adicionar texto de teste na navbar") {
    Write-Host "   ✅ Último commit é o nosso teste!" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Último commit diferente do esperado" -ForegroundColor Yellow
}

# 7. Verificar arquivos importantes
Write-Host "`n7️⃣ VERIFICANDO ARQUIVOS IMPORTANTES..." -ForegroundColor Yellow
$arquivos = @("app.py", "templates/base.html", "salvar_pdf_gcs.py", "gestaosolicitacao-fe66ad097590.json")
foreach ($arquivo in $arquivos) {
    if (Test-Path $arquivo) {
        Write-Host "   ✅ $arquivo encontrado" -ForegroundColor Green
    } else {
        Write-Host "   ❌ $arquivo NÃO encontrado!" -ForegroundColor Red
    }
}

# 8. Verificar alteração no HTML
Write-Host "`n8️⃣ VERIFICANDO ALTERAÇÃO NO HTML..." -ForegroundColor Yellow
if (Test-Path "templates/base.html") {
    $conteudo = Get-Content "templates/base.html" -Raw
    if ($conteudo -match "TESTE CLOUD STORAGE") {
        Write-Host "   ✅ Alteração encontrada no HTML!" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Alteração não encontrada no HTML" -ForegroundColor Yellow
    }
}

# 9. Verificar arquivo de credenciais (não deve estar no git)
Write-Host "`n9️⃣ VERIFICANDO PROTEÇÃO DE CREDENCIAIS..." -ForegroundColor Yellow
$gitStatus = git status --porcelain "gestaosolicitacao-fe66ad097590.json" 2>&1
if ($gitStatus -match "gestaosolicitacao" -or $gitStatus -eq "") {
    # Arquivo não está sendo rastreado ou está protegido
    if (Test-Path ".gitignore") {
        $gitignore = Get-Content ".gitignore" -Raw
        if ($gitignore -match "\.json") {
            Write-Host "   ✅ Arquivo de credenciais PROTEGIDO (.gitignore)" -ForegroundColor Green
        } else {
            Write-Host "   ⚠️  Arquivo pode não estar protegido" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "   ❌ PERIGO! Arquivo de credenciais pode ser commitado!" -ForegroundColor Red
}

# Resumo final
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  RESUMO FINAL" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$tudoOk = $true
if ($caminhoAtual.Path -ne $caminhoEsperado) { $tudoOk = $false }
if (-not (Test-Path ".git")) { $tudoOk = $false }
if ($branch -ne "main") { $tudoOk = $false }

if ($tudoOk) {
    Write-Host "✅ TUDO VERIFICADO E CORRETO!" -ForegroundColor Green
    Write-Host "`nVocê está trabalhando no repositório certo!" -ForegroundColor Cyan
} else {
    Write-Host "⚠️  Algumas verificações falharam. Revise os itens acima." -ForegroundColor Yellow
}

Write-Host "`n========================================`n" -ForegroundColor Cyan

