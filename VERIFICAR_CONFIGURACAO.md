# 🔍 Como Verificar se Está Tudo Configurado

## 1. ✅ Verificar se a API do Cloud Storage está Habilitada

### Passo a passo:

1. Acesse este link diretamente:
   ```
   https://console.cloud.google.com/apis/library/storage.googleapis.com?project=gestaosolicitacao
   ```

2. **O que você deve ver:**
   - Se estiver habilitada: Botão verde "GERENCIAR" (não "HABILITAR")
   - Se NÃO estiver habilitada: Botão azul "HABILITAR"

3. **Se não estiver habilitada:**
   - Clique em **"HABILITAR"**
   - Aguarde alguns minutos para propagação

---

## 2. ✅ Verificar Variável GOOGLE_SERVICE_ACCOUNT_INFO no Cloud Run

### Se você está usando Cloud Run (produção):

#### Passo a passo:

1. Acesse o Cloud Run:
   ```
   https://console.cloud.google.com/run?project=gestaosolicitacao
   ```

2. Clique no seu serviço (provavelmente `programa-gestao-py` ou similar)

3. Clique em **"EDITAR & IMPLANTAR NOVA REVISÃO"** (ou **"EDIT AND DEPLOY NEW REVISION"**)

4. Vá na aba **"VARIÁVEIS E SECRETOS"** (ou **"VARIABLES & SECRETS"**)

5. **Procure por:**
   - `GOOGLE_SERVICE_ACCOUNT_INFO` - Deve existir
   - `GCS_BUCKET_NAME` - Deve ter valor `romaneios-separacao`

6. **Para atualizar GOOGLE_SERVICE_ACCOUNT_INFO:**
   
   a. Clique no lápis (editar) ao lado de `GOOGLE_SERVICE_ACCOUNT_INFO`
   
   b. O valor deve ser o conteúdo COMPLETO do arquivo `gestaosolicitacao-fe66ad097590.json`
   
   c. Para obter o conteúdo, execute no terminal (na pasta do projeto):
   ```bash
   python -c "import json; data = open('gestaosolicitacao-fe66ad097590.json').read(); print(data)"
   ```
   
   d. Copie TODO o conteúdo que aparecer (todo o JSON)
   
   e. Cole no campo de valor (sem aspas extras, só o JSON mesmo)
   
   f. Clique em **"SALVAR"** ou **"SAVE"**
   
   g. Clique em **"IMPLANTAR"** ou **"DEPLOY"** para fazer o deploy

---

## 3. ✅ Ver os Logs do Sistema

### Se estiver rodando localmente (desenvolvimento):

Os logs aparecem no **terminal/console** onde você executou `python app.py`

### Se estiver no Cloud Run (produção):

#### Passo a passo:

1. Acesse o Cloud Run:
   ```
   https://console.cloud.google.com/run?project=gestaosolicitacao
   ```

2. Clique no seu serviço

3. Clique na aba **"LOGS"** ou **"REGISTROS"**

4. Você verá os logs em tempo real

5. **Para ver logs ao gerar um romaneio:**
   - Gere um romaneio pelo sistema
   - Volte para a aba de logs
   - Procure por mensagens como:
     - `☁️ Salvando PDF no Cloud Storage`
     - `✅ PDF salvo no Cloud Storage`
     - `❌ Erro ao salvar PDF` (se houver erro)

---

## 📋 Checklist Completo

Marque cada item conforme verificar:

- [ ] API Cloud Storage está habilitada
- [ ] Variável `GOOGLE_SERVICE_ACCOUNT_INFO` existe no Cloud Run
- [ ] Variável `GOOGLE_SERVICE_ACCOUNT_INFO` tem o conteúdo do novo arquivo JSON
- [ ] Variável `GCS_BUCKET_NAME` existe e vale `romaneios-separacao`
- [ ] Bucket `romaneios-separacao` existe
- [ ] Permissões do bucket estão configuradas
- [ ] Service account tem acesso ao bucket

---

## 🔗 Links Rápidos

- **API Cloud Storage**: https://console.cloud.google.com/apis/library/storage.googleapis.com?project=gestaosolicitacao
- **Cloud Run**: https://console.cloud.google.com/run?project=gestaosolicitacao
- **Bucket**: https://console.cloud.google.com/storage/browser/romaneios-separacao?project=gestaosolicitacao

---

## ⚠️ Se Encontrar Erros

Copie a mensagem de erro completa dos logs e me envie para ajudar a diagnosticar!

