# 🔍 Diagnóstico: PDF não salva no Cloud Storage (Cloud Run)

## Problema
- ✅ **Local**: PDF salva corretamente no bucket
- ❌ **Cloud Run**: PDF não está sendo salvo no Storage

## Causas Possíveis

### 1. Variáveis de Ambiente não configuradas no Cloud Run

Verificar se estas variáveis estão configuradas:

#### Variável 1: `GOOGLE_SERVICE_ACCOUNT_INFO`
```bash
# Verificar se existe
gcloud run services describe programa-gestao-py \
  --region=us-central1 \
  --format="value(spec.template.spec.containers[0].env)"
```

**Valor esperado**: JSON completo das credenciais (sem quebras de linha)

#### Variável 2: `GCS_BUCKET_NAME`
**Valor esperado**: `romaneios-separacao`

---

## 🔧 Como Verificar e Corrigir

### Passo 1: Verificar Variáveis de Ambiente no Cloud Run

1. Acesse: https://console.cloud.google.com/run/detail/us-central1/programa-gestao-py/configuration?project=gestaosolicitacao

2. Vá na aba **"Variáveis e Segredos"**

3. Verifique se existem:
   - `GOOGLE_SERVICE_ACCOUNT_INFO` 
   - `GCS_BUCKET_NAME`

### Passo 2: Verificar Logs do Cloud Run

1. Acesse: https://console.cloud.google.com/run/detail/us-central1/programa-gestao-py/logs?project=gestaosolicitacao

2. Procure por mensagens como:
   - `❌ Erro ao criar cliente GCS`
   - `📋 Carregando credenciais da variável de ambiente...`
   - `⚠️ Arquivo de credenciais não encontrado`

### Passo 3: Configurar Variáveis de Ambiente (se faltarem)

#### Opção A: Via Console do Google Cloud

1. Acesse: https://console.cloud.google.com/run/detail/us-central1/programa-gestao-py/configuration?project=gestaosolicitacao
2. Clique em **"EDITAR E IMPLANTAR NOVA REVISÃO"**
3. Vá em **"Variáveis e Segredos"**
4. Adicione:

**Variável 1:**
- **Nome**: `GOOGLE_SERVICE_ACCOUNT_INFO`
- **Valor**: Cole o conteúdo completo do arquivo `gestaosolicitacao-fe66ad097590.json` (como uma linha só, sem quebras)

**Variável 2:**
- **Nome**: `GCS_BUCKET_NAME`
- **Valor**: `romaneios-separacao`

5. Clique em **"IMPLANTAR"**

#### Opção B: Via CLI (gcloud)

```bash
# Ler o arquivo de credenciais e converter para uma linha
$json = Get-Content "gestaosolicitacao-fe66ad097590.json" -Raw | ConvertFrom-Json | ConvertTo-Json -Compress

# Atualizar GOOGLE_SERVICE_ACCOUNT_INFO
gcloud run services update programa-gestao-py \
  --region=us-central1 \
  --update-env-vars="GOOGLE_SERVICE_ACCOUNT_INFO=$json"

# Atualizar GCS_BUCKET_NAME
gcloud run services update programa-gestao-py \
  --region=us-central1 \
  --update-env-vars="GCS_BUCKET_NAME=romaneios-separacao"
```

**⚠️ IMPORTANTE**: O JSON precisa estar em uma linha só, sem quebras!

---

## 🔐 Permissões Necessárias

A service account `gestsolicitacao@gestaosolicitacao.iam.gserviceaccount.com` precisa ter:

1. **Storage Object Creator** - Para criar arquivos
2. **Storage Object Viewer** - Para ler arquivos

Verificar em: https://console.cloud.google.com/iam-admin/iam?project=gestaosolicitacao

---

## 🧪 Teste Rápido

Após configurar as variáveis:

1. Acesse: https://programa-gestao-py-661879898685.us-central1.run.app/
2. Crie um novo romaneio
3. Verifique os logs em: https://console.cloud.google.com/run/detail/us-central1/programa-gestao-py/logs?project=gestaosolicitacao
4. Procure por mensagens:
   - ✅ `✅ PDF salvo no Cloud Storage: gs://romaneios-separacao/ROM-XXXXXX.pdf`
   - ❌ `❌ Erro ao salvar PDF no Cloud Storage`

---

## 📝 Checklist de Verificação

- [ ] Variável `GOOGLE_SERVICE_ACCOUNT_INFO` existe no Cloud Run?
- [ ] Variável `GCS_BUCKET_NAME` existe no Cloud Run?
- [ ] JSON das credenciais está em uma linha só (sem quebras)?
- [ ] Service account tem permissões no bucket?
- [ ] Bucket `romaneios-separacao` existe?
- [ ] Logs mostram erro específico?

