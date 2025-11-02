# 🔧 Solução: Cloud Storage não salva no Cloud Run

## 🔴 PROBLEMA IDENTIFICADO

O problema principal estava no script `configurar_cloud_storage_cloud_run.ps1` que usava `--set-env-vars` em vez de `--update-env-vars`.

### O que acontecia:
- `--set-env-vars` **SUBSTITUI TODAS** as variáveis de ambiente existentes
- Isso fazia com que outras variáveis importantes fossem perdidas
- As variáveis `GOOGLE_SERVICE_ACCOUNT_INFO` e `GCS_BUCKET_NAME` podem ter sido perdidas em algum deploy anterior

### A correção:
- Agora usa `--update-env-vars` que **adiciona/atualiza** apenas as variáveis especificadas
- Não remove outras variáveis já configuradas
- Mantém toda a configuração existente intacta

## ✅ SOLUÇÃO: 3 PASSOS

### Passo 1: Verificar Configuração Atual

Execute o script de verificação:

```powershell
.\verificar_cloud_storage.ps1
```

Este script vai mostrar:
- ✅ Se as variáveis estão configuradas
- ❌ Se estão faltando
- 📋 O status completo da configuração

### Passo 2: Reconfigurar Variáveis (se necessário)

Se as variáveis não estiverem configuradas ou estiverem incorretas, execute:

```powershell
.\configurar_cloud_storage_cloud_run.ps1
```

**O que este script faz:**
1. ✅ Lê o arquivo de credenciais `gestaosolicitacao-fe66ad097590.json`
2. ✅ Converte para formato JSON em uma linha
3. ✅ Configura `GOOGLE_SERVICE_ACCOUNT_INFO` usando `--update-env-vars` (CORRIGIDO!)
4. ✅ Configura `GCS_BUCKET_NAME` usando `--update-env-vars`
5. ✅ Verifica se foi configurado corretamente

### Passo 3: Verificar Logs

Após configurar, teste criando um romaneio e verifique os logs:

**Link dos Logs:**
https://console.cloud.google.com/run/detail/us-central1/programa-gestao-py/logs?project=gestaosolicitacao

**Procure por estas mensagens nos logs:**
- ✅ `✅ Credenciais carregadas da variável de ambiente`
- ✅ `✅ Cliente GCS criado com credenciais`
- ✅ `✅ === SUCESSO: PDF salvo no Cloud Storage ===`
- ❌ `❌ ERRO` (se houver problemas)

## 🔍 DIAGNÓSTICO

### Se ainda não estiver salvando, verifique:

#### 1. Variáveis de Ambiente
```powershell
.\verificar_cloud_storage.ps1
```

#### 2. Permissões da Service Account
A service account precisa ter permissões no bucket:

- **Storage Object Creator** (para criar arquivos)
- **Storage Object Viewer** (para ler arquivos)

**Verificar/Configurar:**
1. Acesse: https://console.cloud.google.com/storage/browser/romaneios-separacao?project=gestaosolicitacao
2. Clique em "PERMISSÕES"
3. Verifique se `gestsolicitacao@gestaosolicitacao.iam.gserviceaccount.com` está listado
4. Se não estiver, adicione com as permissões acima

#### 3. Bucket Existe?
Verifique se o bucket `romaneios-separacao` existe:
- https://console.cloud.google.com/storage/browser?project=gestaosolicitacao

## 📋 CHECKLIST RÁPIDO

- [ ] Executar `.\verificar_cloud_storage.ps1`
- [ ] Se faltar variáveis, executar `.\configurar_cloud_storage_cloud_run.ps1`
- [ ] Aguardar 30-60 segundos após configurar
- [ ] Testar criando um romaneio
- [ ] Verificar logs do Cloud Run
- [ ] Verificar permissões da Service Account no bucket

## 🔧 MUDANÇAS FEITAS

### Arquivo: `configurar_cloud_storage_cloud_run.ps1`
- ✅ **CORRIGIDO:** Usa `--update-env-vars` em vez de `--set-env-vars`
- ✅ **MELHORADO:** Melhor tratamento de erros
- ✅ **ADICIONADO:** Mensagem explicando o uso de `--update-env-vars`

### Arquivo: `verificar_cloud_storage.ps1` (NOVO)
- ✅ Script para verificar rapidamente se as variáveis estão configuradas
- ✅ Mostra status detalhado da configuração
- ✅ Indica próximos passos se algo estiver faltando

## 💡 POR QUE FUNCIONA LOCAL E NÃO NO CLOUD?

**Local:**
- O código lê o arquivo `gestaosolicitacao-fe66ad097590.json` diretamente do disco
- Não depende de variáveis de ambiente (embora possa usá-las se existirem)

**Cloud Run:**
- Não tem acesso ao arquivo JSON (não está no container)
- **DEPENDE** da variável de ambiente `GOOGLE_SERVICE_ACCOUNT_INFO`
- Se a variável não estiver configurada ou estiver corrompida, não funciona

## 🚀 PRÓXIMOS PASSOS

1. Execute `.\verificar_cloud_storage.ps1` para verificar o status atual
2. Se necessário, execute `.\configurar_cloud_storage_cloud_run.ps1`
3. Aguarde alguns segundos
4. Teste criando um novo romaneio
5. Verifique os logs

Se ainda não funcionar após seguir estes passos, verifique as permissões da Service Account no bucket!

---

## 🔧 MELHORIAS RECENTES (Revisão do Código)

### Arquivo: `salvar_pdf_gcs.py`

#### 1. Tratamento Melhorado de JSON
- ✅ **Detecção de JSON como string escapada** (double encoding)
- ✅ **Validação de campos obrigatórios** antes de criar credenciais
- ✅ **Logs detalhados** em caso de erro de parsing JSON
- ✅ **Mensagens de erro mais claras** indicando o problema específico

#### 2. Validação de Acesso ao Bucket
- ✅ **Verificação prévia** se o bucket existe e é acessível
- ✅ **Mensagens de erro específicas** para:
  - Bucket não encontrado (404)
  - Sem permissão (403)
  - Outros erros
- ✅ **Sugestões de correção** baseadas no tipo de erro

#### 3. Verificação de Upload
- ✅ **Confirmação** que o arquivo foi realmente salvo após upload
- ✅ **Validação do tamanho** do arquivo salvo
- ✅ **Mensagens de erro específicas** durante upload

#### 4. Logs Detalhados
- ✅ Logs mostram **exatamente onde o processo falha**
- ✅ Informações sobre **ambiente detectado** (Cloud Run vs Local)
- ✅ Detalhes sobre **variáveis de ambiente**
- ✅ Informações da **service account usada**

### Arquivo: `testar_gcs_permissoes.py`
- ✅ **Melhorada validação de acesso ao bucket**
- ✅ **Mensagens de erro mais específicas**
- ✅ **Testa permissões de leitura e escrita**

### Novo Arquivo: `DIAGNOSTICO_SALVAMENTO_PDF.md`
- ✅ **Guia completo de diagnóstico**
- ✅ **Exemplos de logs de sucesso e erro**
- ✅ **Checklist passo a passo**
- ✅ **Soluções para problemas comuns**

## ⚠️ IMPORTANTE

**O layout do PDF NÃO foi alterado** - As melhorias foram apenas em:
- Tratamento de erros
- Validações
- Logs de debug
- Mensagens de erro mais claras

O código de geração de PDF (`pdf_cloud_generator.py`, `pdf_browser_generator.py`) **não foi alterado**.

## 📋 Próximos Passos para Diagnóstico

Se ainda não estiver funcionando, consulte o arquivo **`DIAGNOSTICO_SALVAMENTO_PDF.md`** para um guia completo de diagnóstico detalhado.

