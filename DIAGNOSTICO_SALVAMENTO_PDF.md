# 🔍 Diagnóstico Completo: Salvamento de PDF no Cloud Storage

## ✅ Melhorias Implementadas

### 1. Tratamento Melhorado de JSON
- ✅ Detecção de JSON como string escapada (double encoding)
- ✅ Validação de campos obrigatórios antes de criar credenciais
- ✅ Logs detalhados em caso de erro de parsing JSON
- ✅ Mensagens de erro mais claras indicando o problema específico

### 2. Validação de Acesso ao Bucket
- ✅ Verificação prévia se o bucket existe e é acessível
- ✅ Mensagens de erro específicas para:
  - Bucket não encontrado (404)
  - Sem permissão (403)
  - Outros erros
- ✅ Sugestões de correção baseadas no tipo de erro

### 3. Verificação de Upload
- ✅ Confirmação que o arquivo foi realmente salvo após upload
- ✅ Validação do tamanho do arquivo salvo
- ✅ Mensagens de erro específicas durante upload

### 4. Logs Detalhados
- ✅ Logs mostram exatamente onde o processo falha
- ✅ Informações sobre ambiente detectado (Cloud Run vs Local)
- ✅ Detalhes sobre variáveis de ambiente
- ✅ Informações da service account usada

## 🔧 Como Diagnosticar Problemas

### Passo 1: Verificar Variáveis de Ambiente

Execute o script de verificação:

```powershell
.\verificar_cloud_storage.ps1
```

**O que verificar:**
- ✅ `GOOGLE_SERVICE_ACCOUNT_INFO` está definida?
- ✅ `GCS_BUCKET_NAME` está definida?
- ✅ O JSON em `GOOGLE_SERVICE_ACCOUNT_INFO` está válido?

### Passo 2: Testar Conexão com Cloud Storage

Execute o script de teste:

```powershell
python testar_gcs_permissoes.py
```

**O script testa:**
1. Criação do cliente GCS
2. Acesso ao bucket
3. Permissão de leitura (listar arquivos)
4. Permissão de escrita (upload de teste)

### Passo 3: Verificar Logs do Cloud Run

Acesse os logs:
https://console.cloud.google.com/run/detail/us-central1/programa-gestao-py/logs?project=gestaosolicitacao

**Procure por estas mensagens:**

#### ✅ Sucesso:
```
🌐 Ambiente detectado: Cloud Run
📋 Carregando credenciais da variável de ambiente...
✅ Credenciais carregadas da variável de ambiente
   Projeto: gestaosolicitacao
   Service Account: gestsolicitacao@gestaosolicitacao.iam.gserviceaccount.com
✅ Cliente GCS criado com credenciais
🔍 Verificando acesso ao bucket: romaneios-separacao
✅ Bucket encontrado e acessível
📤 Fazendo upload de X bytes para ROM-XXXXXX.pdf...
✅ === SUCESSO: PDF salvo no Cloud Storage ===
✅ Caminho: gs://romaneios-separacao/ROM-XXXXXX.pdf
✅ Tamanho confirmado: X bytes
```

#### ❌ Problemas Comuns:

**1. JSON Inválido:**
```
❌ ERRO: JSON inválido na variável GOOGLE_SERVICE_ACCOUNT_INFO
   Erro: Expecting value: line 1 column 1 (char 0)
   Tamanho da string: X caracteres
```
**Solução:** Reconfigurar a variável usando `.\configurar_cloud_storage_cloud_run.ps1`

**2. Campos Faltando:**
```
❌ ERRO: Campos obrigatórios faltando: ['private_key', 'client_email']
```
**Solução:** Verificar se o JSON completo foi copiado para a variável

**3. Bucket Não Encontrado:**
```
❌ ERRO: Bucket 'romaneios-separacao' não encontrado!
   Verifique se o bucket existe no projeto
```
**Solução:** Verificar se o bucket existe no projeto

**4. Sem Permissão:**
```
❌ ERRO: Sem permissão para acessar o bucket 'romaneios-separacao'!
   Verifique as permissões da service account no bucket
   Permissões necessárias: Storage Object Creator, Storage Object Viewer
```
**Solução:** Adicionar permissões da service account no bucket

**5. Cliente GCS Não Criado:**
```
❌ ERRO: Não foi possível criar cliente GCS
```
**Solução:** Verificar logs anteriores para identificar o problema específico

## 📋 Checklist de Diagnóstico

Quando o PDF não salva no Cloud Run, verifique na ordem:

- [ ] **Variáveis de Ambiente:**
  - [ ] `GOOGLE_SERVICE_ACCOUNT_INFO` está definida?
  - [ ] `GCS_BUCKET_NAME` está definida?
  - [ ] O JSON é válido? (usar `testar_gcs_permissoes.py`)

- [ ] **Permissões:**
  - [ ] Service account tem permissão no bucket?
  - [ ] Permissões necessárias: `Storage Object Creator`, `Storage Object Viewer`
  - [ ] Bucket existe no projeto?

- [ ] **Logs:**
  - [ ] Qual erro específico aparece nos logs?
  - [ ] Mensagens de sucesso aparecem?
  - [ ] Há erros de JSON parsing?

- [ ] **Teste Local vs Cloud:**
  - [ ] Funciona localmente? (usa arquivo JSON)
  - [ ] Funciona no Cloud Run? (usa variável de ambiente)
  - [ ] Qual a diferença entre os dois?

## 🚀 Solução Rápida

Se nada funcionar, execute em ordem:

1. **Verificar configuração:**
   ```powershell
   .\verificar_cloud_storage.ps1
   ```

2. **Reconfigurar se necessário:**
   ```powershell
   .\configurar_cloud_storage_cloud_run.ps1
   ```

3. **Aguardar 30-60 segundos** para as variáveis serem atualizadas

4. **Testar conexão:**
   ```powershell
   python testar_gcs_permissoes.py
   ```

5. **Criar um romaneio** e verificar os logs

## 💡 Importante

**O layout do PDF NÃO é alterado** - As melhorias foram apenas em:
- Tratamento de erros
- Validações
- Logs de debug
- Mensagens de erro mais claras

O código de geração de PDF (`pdf_cloud_generator.py`, `pdf_browser_generator.py`) **não foi alterado**.

