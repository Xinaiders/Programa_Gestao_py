# 🚀 Deploy Simples - Comandos Manuais

Se os scripts automáticos não funcionarem, siga estes comandos manualmente:

## 1️⃣ Commit e Push

```bash
git add .
git commit -m "Atualizar para novas credenciais gestaosolicitacao e Cloud Storage"
git push origin main
```

## 2️⃣ Atualizar Variáveis de Ambiente

**No Windows PowerShell:**

```powershell
# Ler arquivo JSON
$json = Get-Content "gestaosolicitacao-fe66ad097590.json" -Raw

# Atualizar GOOGLE_SERVICE_ACCOUNT_INFO
gcloud run services update programa-gestao-py --region=us-central1 --update-env-vars="GOOGLE_SERVICE_ACCOUNT_INFO=$json"

# Atualizar GCS_BUCKET_NAME
gcloud run services update programa-gestao-py --region=us-central1 --update-env-vars="GCS_BUCKET_NAME=romaneios-separacao"
```

**No Linux/Mac:**

```bash
# Ler arquivo JSON
JSON=$(cat gestaosolicitacao-fe66ad097590.json)

# Atualizar GOOGLE_SERVICE_ACCOUNT_INFO
gcloud run services update programa-gestao-py --region=us-central1 --update-env-vars="GOOGLE_SERVICE_ACCOUNT_INFO=$JSON"

# Atualizar GCS_BUCKET_NAME
gcloud run services update programa-gestao-py --region=us-central1 --update-env-vars="GCS_BUCKET_NAME=romaneios-separacao"
```

## 3️⃣ Deploy do Código

```bash
gcloud run deploy programa-gestao-py --source . --region=us-central1
```

**OU via Console:**
1. Acesse: https://console.cloud.google.com/run?project=gestaosolicitacao
2. Clique no serviço
3. "EDITAR & IMPLANTAR NOVA REVISÃO"
4. "IMPLANTAR"

---

## ✅ Pronto!

Após o deploy, teste gerando um romaneio e verifique se aparece no bucket!

