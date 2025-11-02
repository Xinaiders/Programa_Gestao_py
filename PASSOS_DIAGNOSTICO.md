# 🔧 Passos para Diagnosticar o Problema de Salvamento de PDF

## 📋 Checklist Rápido - Execute nesta Ordem

### ✅ Passo 1: Verificar Variáveis de Ambiente no Cloud Run

Execute este comando no PowerShell:

```powershell
.\verificar_cloud_storage.ps1
```

**O que esperar:**
- ✅ Se mostrar "TUDO CONFIGURADO CORRETAMENTE" → vá para Passo 2
- ❌ Se mostrar "CONFIGURAÇÃO INCOMPLETA" → execute o Passo 1.1

**Passo 1.1 (se necessário):** Reconfigurar variáveis
```powershell
.\configurar_cloud_storage_cloud_run.ps1
```
Aguarde 30-60 segundos após executar.

---

### ✅ Passo 2: Testar Conexão Localmente

Execute este comando:

```powershell
python testar_gcs_permissoes.py
```

**O que verificar:**
- ✅ Se todos os testes passarem → o código está funcionando localmente
- ❌ Se algum teste falhar → anote qual teste falhou (será importante)

---

### ✅ Passo 3: Verificar Logs do Cloud Run

1. **Acesse os logs do Cloud Run:**
   https://console.cloud.google.com/run/detail/us-central1/programa-gestao-py/logs?project=gestaosolicitacao

2. **Crie um novo romaneio** através da interface web do Cloud Run

3. **Procure nos logs por estas mensagens:**

#### 🟢 Mensagens de Sucesso (Tudo OK):
```
🌐 Ambiente detectado: Cloud Run
✅ Credenciais carregadas da variável de ambiente
✅ Cliente GCS criado com credenciais
✅ Bucket encontrado e acessível
✅ === SUCESSO: PDF salvo no Cloud Storage ===
```

#### 🔴 Mensagens de Erro (Problemas):

**Erro 1: JSON Inválido**
```
❌ ERRO: JSON inválido na variável GOOGLE_SERVICE_ACCOUNT_INFO
```
**Solução:** Execute `.\configurar_cloud_storage_cloud_run.ps1` novamente

**Erro 2: Bucket Não Encontrado**
```
❌ ERRO: Bucket 'romaneios-separacao' não encontrado!
```
**Solução:** Verificar se o bucket existe no projeto:
- https://console.cloud.google.com/storage/browser?project=gestaosolicitacao

**Erro 3: Sem Permissão**
```
❌ ERRO: Sem permissão para acessar o bucket 'romaneios-separacao'!
```
**Solução:** Adicionar permissões da service account:
- https://console.cloud.google.com/storage/browser/romaneios-separacao?project=gestaosolicitacao
- Clique em "PERMISSÕES"
- Adicione: `gestsolicitacao@gestaosolicitacao.iam.gserviceaccount.com`
- Permissões: `Storage Object Creator` e `Storage Object Viewer`

**Erro 4: Cliente GCS Não Criado**
```
❌ ERRO: Não foi possível criar cliente GCS
```
**Solução:** Verificar logs anteriores para ver o erro específico

---

### ✅ Passo 4: Anotar Resultados

Preencha este checklist com os resultados:

- [ ] **Passo 1:** Variáveis configuradas? (Sim/Não)
- [ ] **Passo 2:** Testes locais passaram? (Sim/Não)
- [ ] **Passo 3:** Qual erro aparece nos logs? (Copie a mensagem completa)
- [ ] **Passo 3:** A mensagem de sucesso aparece? (Sim/Não)

---

## 🎯 Próximos Passos Baseados nos Resultados

### Cenário A: Tudo Funciona Local, Mas Não no Cloud Run

**Provável Causa:** Variáveis de ambiente não configuradas ou JSON inválido

**Ação:**
1. Execute `.\configurar_cloud_storage_cloud_run.ps1`
2. Aguarde 60 segundos
3. Teste novamente
4. Verifique logs novamente

### Cenário B: Erro de Permissão nos Logs

**Provável Causa:** Service account sem permissão no bucket

**Ação:**
1. Acesse: https://console.cloud.google.com/storage/browser/romaneios-separacao?project=gestaosolicitacao
2. Clique em "PERMISSÕES"
3. Verifique se `gestsolicitacao@gestaosolicitacao.iam.gserviceaccount.com` está listada
4. Se não estiver, adicione com permissões:
   - Storage Object Creator
   - Storage Object Viewer

### Cenário C: Bucket Não Encontrado

**Provável Causa:** Bucket não existe ou nome errado

**Ação:**
1. Verificar se o bucket existe: https://console.cloud.google.com/storage/browser?project=gestaosolicitacao
2. Verificar nome do bucket na variável `GCS_BUCKET_NAME`
3. Criar bucket se não existir

### Cenário D: JSON Inválido

**Provável Causa:** JSON corrompido na variável de ambiente

**Ação:**
1. Execute `.\configurar_cloud_storage_cloud_run.ps1` novamente
2. Aguarde 60 segundos
3. Teste novamente

---

## 📞 Se Nada Funcionar

1. **Copie TODA a mensagem de erro** dos logs do Cloud Run
2. **Execute:** `.\verificar_cloud_storage.ps1` e copie o resultado
3. **Execute:** `python testar_gcs_permissoes.py` e copie o resultado
4. Com essas informações, será possível identificar o problema exato

---

## ⏱️ Tempo Estimado

- Passo 1: 2 minutos
- Passo 2: 1 minuto
- Passo 3: 5 minutos (criar romaneio e verificar logs)
- **Total: ~10 minutos**

---

## ✅ Verificação Final

Após seguir os passos, o PDF deve:
- ✅ Aparecer no bucket `romaneios-separacao`
- ✅ Mostrar mensagem de sucesso nos logs
- ✅ Estar acessível para download

Se tudo funcionar, você verá nos logs:
```
✅ === SUCESSO: PDF salvo no Cloud Storage ===
✅ Caminho: gs://romaneios-separacao/ROM-XXXXXX.pdf
```

