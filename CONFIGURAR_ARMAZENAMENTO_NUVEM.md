# ☁️ Configurar Armazenamento de PDFs na Nuvem (Cloud Storage)

## ⚠️ Problema Atual

No **Cloud Run** (produção):
- A pasta local `Romaneios_Separacao` **NÃO FUNCIONA**
- Arquivos temporários são perdidos quando o container reinicia
- Precisa de armazenamento persistente na nuvem

## ✅ Solução: Google Cloud Storage

### Passo 1: Criar Bucket no Cloud Storage

1. Acesse: https://console.cloud.google.com/storage/browser?project=sistema-consulta-produtos

2. Clique em **"CRIAR BUCKET"**

3. Configure:
   - **Nome do bucket**: `romaneios-separacao`
   - **Região**: `us-central1` (mesma do Cloud Run)
   - **Default storage class**: `Standard`
   - **Access control**: `Uniform`
   - Clique em **"CRIAR"**

### Passo 2: Dar Permissões à Service Account

1. Após criar o bucket, clique nele
2. Vá na aba **"PERMISSÕES"**
3. Clique em **"GRANT ACCESS"**
4. Em "New principals", cole:
   ```
   gestaosolicitacao@sistema-consulta-produtos.iam.gserviceaccount.com
   ```
5. Em "Select a role", escolha: **"Storage Object Creator"** e **"Storage Object Viewer"**
6. Clique em **"SAVE"**

### Passo 3: Adicionar Variável de Ambiente no Cloud Run

1. Acesse o Cloud Run Console
2. Edite a revisão do serviço
3. Vá em **"Variáveis e Secretos"**
4. Adicione nova variável:
   - **Nome**: `GCS_BUCKET_NAME`
   - **Valor**: `romaneios-separacao`
5. Salve e faça **DEPLOY**

### Passo 4: Implementar Código de Salvamento

O código já está preparado! O arquivo `cloud_config.py` já detecta quando está no GCP e usa Cloud Storage automaticamente.

### Como Funciona?

**Ambiente Local (desenvolvimento):**
```
PDF salvo em: G:\Meu Drive\Line Flex\...\Romaneios_Separacao\
```

**Ambiente Cloud Run (produção):**
```
PDF salvo em: gs://romaneios-separacao/ROM-000001.pdf
```

## 📋 Resumo

- ✅ **Local**: `Romaneios_Separacao/`
- ✅ **Nuvem**: `gs://romaneios-separacao/`
- ✅ **Automático**: Sistema detecta ambiente e usa o local correto

## 🎯 Próximos Passos

1. Criar bucket `romaneios-separacao`
2. Dar permissões à service account
3. Adicionar variável `GCS_BUCKET_NAME` no Cloud Run
4. Fazer novo deploy
5. Testar!

