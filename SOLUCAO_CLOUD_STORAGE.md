# 🔧 Solução: PDFs não estão sendo salvos no Cloud Storage

## ⚠️ Problema
Os PDFs não estão sendo salvos no bucket `romaneios-separacao` do Google Cloud Storage.

## ✅ Checklist de Verificação

### 1. Verificar se o Bucket Existe

1. Acesse: https://console.cloud.google.com/storage/browser?project=gestaosolicitacao
2. Verifique se o bucket `romaneios-separacao` existe
3. Se não existir, crie:
   - Clique em **"CRIAR BUCKET"**
   - Nome: `romaneios-separacao`
   - Região: `us-central1` (ou a mesma do Cloud Run)
   - Storage class: `Standard`
   - Access control: `Uniform`

### 2. Verificar Permissões do Bucket

O email da service account precisa ter permissões no bucket:

1. Acesse o bucket: https://console.cloud.google.com/storage/browser/romaneios-separacao?project=gestaosolicitacao
2. Clique na aba **"PERMISSÕES"**
3. Verifique se o email está listado:
   - `gestsolicitacao@gestaosolicitacao.iam.gserviceaccount.com`
4. Se não estiver, adicione:
   - Clique em **"GRANT ACCESS"**
   - Em "New principals", cole: `gestsolicitacao@gestaosolicitacao.iam.gserviceaccount.com`
   - Em "Select a role", escolha:
     - ✅ **"Storage Object Creator"** (para criar/upload)
     - ✅ **"Storage Object Viewer"** (para ler/visualizar)
   - Clique em **"SAVE"**

### 3. Verificar API do Cloud Storage

A API do Cloud Storage precisa estar habilitada:

1. Acesse: https://console.cloud.google.com/apis/library/storage.googleapis.com?project=gestaosolicitacao
2. Verifique se está **"HABILITADA"**
3. Se não estiver, clique em **"HABILITAR"**
4. Aguarde alguns minutos para propagação

### 4. Verificar Credenciais

#### Desenvolvimento Local:
- ✅ Arquivo `gestaosolicitacao-fe66ad097590.json` existe na raiz do projeto
- ✅ O código atualizado carrega credenciais do arquivo automaticamente

#### Cloud Run (Produção):
1. Acesse: https://console.cloud.google.com/run?project=gestaosolicitacao
2. Clique no serviço
3. Vá em **"EDITAR & IMPLANTAR NOVA REVISÃO"**
4. Clique na aba **"VARIÁVEIS E SECRETOS"**
5. Verifique se existe:
   - `GOOGLE_SERVICE_ACCOUNT_INFO` - JSON completo das credenciais
   - `GCS_BUCKET_NAME` - Valor: `romaneios-separacao`
6. Se não existir, adicione:
   - **GOOGLE_SERVICE_ACCOUNT_INFO**: Conteúdo do arquivo `gestaosolicitacao-fe66ad097590.json`
   - **GCS_BUCKET_NAME**: `romaneios-separacao`

### 5. Testar Conexão

Execute o teste local (se tiver `google-cloud-storage` instalado):

```bash
python testar_cloud_storage.py
```

Ou teste diretamente no código ao gerar um romaneio e verifique os logs.

## 🐛 Debug - Logs para Verificar

Ao tentar salvar um PDF, os logs devem mostrar:

```
☁️ Salvando PDF no Cloud Storage: ROM-000001
📋 Carregando credenciais do arquivo: gestaosolicitacao-fe66ad097590.json
✅ Credenciais carregadas do arquivo
✅ Cliente GCS criado com credenciais (Projeto: gestaosolicitacao)
📤 Fazendo upload de X bytes...
✅ PDF salvo no Cloud Storage: gs://romaneios-separacao/ROM-000001.pdf
```

### Erros Comuns:

1. **"Bucket não encontrado"**
   - ✅ Criar o bucket `romaneios-separacao`

2. **"Permission denied" ou "403 Forbidden التشريع"**
   - ✅ Adicionar permissões ao bucket (passo 2)

3. **"API não habilitada"**
   - ✅ Habilitar Cloud Storage API (passo 3)

4. **"Credenciais não encontradas"**
   - ✅ Verificar arquivo local (desenvolvimento)
   - ✅ Verificar variável de ambiente (Cloud Run)

## 📋 Resumo das Ações Necessárias

1. ✅ Bucket `romaneios-separacao` existe no projeto `gestaosolicitacao`
2. ✅ Email `gestsolicitacao@gestaosolicitacao.iam.gserviceaccount.com` tem permissões no bucket
3. ✅ API do Cloud Storage habilitada
4. ✅ Credenciais configuradas (arquivo local ou variável de ambiente)
5. ✅ Código atualizado para usar novas credenciais

## 🔗 Links Úteis

- **Bucket**: https://console.cloud.google.com/storage/browser/romaneios-separacao?project=gestaosolicitacao
- **Permissões**: https://console.cloud.google.com/storage/browser/romaneios-separacao?project=gestaosolicitacao&tab=permissions
- **API**: https://console.cloud.google.com/apis/library/storage.googleapis.com?project=gestaosolicitacao
- **Cloud Run**: https://console.cloud.google.com/run?project=gestaosolicitacao

