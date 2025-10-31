# 🚀 Configurar Cloud Storage no Cloud Run - Automático

## 📋 Script Automático

Criei um script PowerShell que configura automaticamente as variáveis de ambiente necessárias no Cloud Run.

## ⚡ Como Usar

### Pré-requisitos

1. **gcloud CLI instalado**: https://cloud.google.com/sdk/docs/install
2. **Arquivo de credenciais**: `gestaosolicitacao-fe66ad097590.json` no diretório do projeto
3. **Acesso ao projeto**: Você precisa ter permissões para atualizar o Cloud Run

### Executar o Script

Abra o PowerShell no diretório do projeto e execute:

```powershell
.\configurar_cloud_storage_cloud_run.ps1
```

O script irá:

1. ✅ Verificar se está no diretório correto
2. ✅ Verificar se gcloud está instalado
3. ✅ Verificar autenticação (faz login se necessário)
4. ✅ Ler e processar o arquivo JSON оформления
5. ✅ Configurar `GOOGLE_SERVICE_ACCOUNT_INFO` no Cloud Run
6. ✅ Configurar `GCS_BUCKET_NAME` no Cloud Run
7. ✅ Verificar se as variáveis foram configuradas
8. ✅ Mostrar próximos passos

## 🔍 O que o Script Faz

### Variáveis Configuradas:

1. **GOOGLE_SERVICE_ACCOUNT_INFO**
   - Lê o arquivo `gestaosolicitacao-fe66ad097590.json`
   - Converte para formato de uma linha (sem quebras)
   - Configura no Cloud Run

2. **GCS_BUCKET_NAME**
   - Valor: `romaneios-separacao`
   - Configura no Cloud Run

## ⚠️ Importante

### Permissões da Service Account

Após executar o script, **verifique manualmente** se a service account tem permissões no bucket:

1. Acesse: https://console.cloud.google.com/iam-admin/iam?project=gestaosolicitacao
2. Procure: `gestsolicitacao@gestaosolicitacao.iam.gserviceaccount.com`
3. Verifique se tem as roles:
   - ✅ **Storage Object Creator**
   - ✅ **Storage Object Viewer**

Se não tiver, adicione as permissões no bucket:
- https://console.cloud.google.com/storage/browser/romaneios-separacao?project=gestaosolicitacao
- Clique em "PERMISSÕES" → Adicione a service account

## 🧪 Testar Após Configuração

1. **Aguarde 30-60 segundos** para o Cloud Run atualizar

2. **Crie um romaneio**:
   - https://programa-gestao-py-661879898685.us-central1.run.app/

3. **Verifique os logs**:
   - https://console.cloud.google.com/run/detail/us-central1/programa-gestao-py/logs?project=gestaosolicitacao

4. **Procure por estas mensagens**:
   - ✅ `✅ Credenciais carregadas da variável de ambiente`
   - ✅ `✅ PDF salvo no Cloud Storage: gs://romaneios-separacao/ROM-XXXXXX.pdf`
   - ❌ `❌ ERRO` (se houver problemas)

5. **Verifique o bucket**:
   - https://console.cloud.google.com/storage/browser/romaneios-separacao?project=gestaosolicitacao
   - Deve aparecer o PDF recém-criado!

## 🐛 Troubleshooting

### Erro: "Arquivo de credenciais não encontrado"
- Certifique-se de estar no diretório correto do projeto
- Verifique se o arquivo `gestaosolicitacao-fe66ad097590.json` existe

### Erro: "gcloud CLI não encontrado"
- Instale o gcloud CLI: https://cloud.google.com/sdk/docs/install
- Reinicie o PowerShell após instalar

### Erro: "Serviço não encontrado"
- Certifique-se que o Cloud Run já foi implantado
- Verifique o nome do serviço: `programa-gestao-py`
- Verifique a região: `us-central1`

### Variáveis não aparecem nos logs
- Aguarde alguns minutos
- As variáveis podem demorar alguns segundos para propagar
- Verifique no console do Cloud Run se as variáveis estão configuradas

## 📝 Checklist Manual (se o script não funcionar)

Se preferir configurar manualmente:

1. **Acesse o Console do Cloud Run**:
   - https://console.cloud.google.com/run/detail/us-central1/programa-gestao-py/configuration?project=gestaosolicitacao

2. **Clique em "EDITAR E IMPLANTAR NOVA REVISÃO"**

3. **Vá em "Variáveis e Segredos"**

4. **Adicione GOOGLE_SERVICE_ACCOUNT_INFO**:
   - Nome: `GOOGLE_SERVICE_ACCOUNT_INFO`
   - Valor: Copie TODO o conteúdo do arquivo `gestaosolicitacao-fe66ad097590.json` em uma linha só

5. **Adicione GCS_BUCKET_NAME**:
   - Nome: `GCS_BUCKET_NAME`
   - Valor: `romaneios-separacao`

6. **Clique em "IMPLANTAR"**

## ✅ Sucesso!

Após configurar, o sistema deve salvar PDFs automaticamente no Cloud Storage quando estiver rodando no Cloud Run! 🎉

