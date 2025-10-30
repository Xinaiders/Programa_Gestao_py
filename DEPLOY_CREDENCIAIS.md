# 🚀 Deploy das Novas Credenciais no Google Cloud Run

## ⚠️ IMPORTANTE
Antes de testar, você precisa fazer deploy das alterações e atualizar as credenciais no Cloud Run!

---

## 📋 Passo 1: Fazer Commit das Alterações

```bash
git add .
git commit -m "Atualizar para novas credenciais gestaosolicitacao e Cloud Storage"
git push origin main
```

---

## 📋 Passo 2: Atualizar Variável de Ambiente GOOGLE_SERVICE_ACCOUNT_INFO

### 2.1. Obter o conteúdo do novo arquivo JSON

Execute no terminal (na pasta do projeto):

```bash
python -c "import json; data = open('gestaosolicitacao-fe66ad097590.json').read(); print(data)"
```

**IMPORTANTE:** Copie TODO o conteúdo que aparecer no terminal.

### 2.2. Atualizar no Cloud Run

1. Acesse: https://console.cloud.google.com/run?project=gestaosolicitacao

2. Clique no seu serviço (provavelmente `programa-gestao-py`)

3. Clique em **"EDITAR & IMPLANTAR NOVA REVISÃO"** (ou **"EDIT AND DEPLOY NEW REVISION"**)

4. Vá na aba **"VARIÁVEIS E SECRETOS"** (ou **"VARIABLES & SECRETS"**)

5. Procure pela variável `GOOGLE_SERVICE_ACCOUNT_INFO`

6. Clique no ícone de **lápis (editar)** ao lado dela

7. **Cole o conteúdo completo do novo arquivo JSON** (que você copiou no passo 2.1)

8. Clique em **"SALVAR"** ou **"SAVE"**

9. **Verifique se existe** a variável `GCS_BUCKET_NAME`:
   - Se não existir, clique em **"ADICIONAR VARIÁVEL"**
   - Nome: `GCS_BUCKET_NAME`
   - Valor: `romaneios-separacao`
   - Clique em **"SALVAR"**

10. Clique em **"IMPLANTAR"** ou **"DEPLOY"**

11. ⏱️ Aguarde 3-5 minutos para o deploy terminar

---

## 📋 Passo 3: Verificar Deploy

1. Após o deploy terminar, acesse seu serviço no Cloud Run

2. Vá na aba **"LOGS"** ou **"REGISTROS"**

3. Procure por mensagens de erro (se houver)

4. Tente gerar um romaneio e verifique os logs para confirmar que está funcionando

---

## 📋 Resumo das Alterações que Serão Deployadas

✅ `salvar_pdf_gcs.py` - Atualizado para usar novas credenciais  
✅ `app.py` - Atualizado para sempre tentar salvar no Cloud Storage  
✅ Referências atualizadas para `gestaosolicitacao-fe66ad097590.json`  
✅ Projeto atualizado para `gestaosolicitacao`  

---

## ✅ Checklist Final

Antes de testar, confirme:

- [ ] Código commitado e pushado para o repositório
- [ ] Variável `GOOGLE_SERVICE_ACCOUNT_INFO` atualizada com novo JSON
- [ ] Variável `GCS_BUCKET_NAME` existe e vale `romaneios-separacao`
- [ ] Deploy concluído no Cloud Run
- [ ] Bucket `romaneios-separacao` criado
- [ ] Permissões do bucket configuradas
- [ ] API Cloud Storage habilitada

---

## 🔗 Links Úteis

- **Cloud Run**: https://console.cloud.google.com/run?project=gestaosolicitacao
- **Bucket**: https://console.cloud.google.com/storage/browser/romaneios-separacao?project=gestaosolicitacao
- **API Storage**: https://console.cloud.google.com/apis/library/storage.googleapis.com?project=gestaosolicitacao

---

Após fazer o deploy, teste gerando um romaneio e verifique se o PDF aparece no bucket! 🚀

