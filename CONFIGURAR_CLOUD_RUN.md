# 🔧 Configurar Credenciais no Google Cloud Run

## ⚠️ PROBLEMA
O sistema funciona localmente, mas no Cloud Run não consegue acessar o arquivo JSON de credenciais porque o arquivo está no `.gitignore` (por segurança).

## ✅ SOLUÇÃO: Variável de Ambiente

### Passo 1: Converter o JSON para variável de ambiente

Execute este comando para obter o JSON em formato de variável de ambiente:

```bash
python -c "import json; data = open('sistema-consulta-produtos-2c00b5872af4.json').read(); print(data)"
```

**IMPORTANTE:** Copie TODO o conteúdo que aparecer no terminal.

### Passo 2: Adicionar no Google Cloud Run

1. Acesse: https://console.cloud.google.com/run
2. Clique no serviço: `programa-gestao-py`
3. Clique em **"EDITAR & IMPLANTAR NOVA REVISÃO"**
4. Clique na aba **"VARIÁVEIS E SECRETOS"**
5. Clique em **"ADICIONAR VARIÁVEL"**
6. Configure:
   - **Nome**: `GOOGLE_SERVICE_ACCOUNT_INFO`
   - **Valor**: Cole o conteúdo JSON completo do arquivo (sem aspas extras)
7. Clique em **"SALVAR"**
8. Clique em **"IMPLANTAR"**

### Passo 3: Aguardar Deploy

⏱️ Aguarde 3-5 minutos para o deploy terminar

### Passo 4: Testar

Acesse: https://programa-gestao-py-661879898685.us-central1.run.app/solicitacoes

O erro deve desaparecer!

---

## 📋 Formato Esperado da Variável

A variável `GOOGLE_SERVICE_ACCOUNT_INFO` deve conter o JSON completo, por exemplo:

```json
{
  "type": "service_account",
  "project_id": "sistema-consulta-produtos",
  "private_key_id": "572a382a8d50ca8f2833cde12bb935785e650af6",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "gestaosolicitacao@sistema-consulta-produtos.iam.gserviceaccount.com",
  "client_id": "105306737506940549191",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  ...
}
```

## ✅ Checklist

- [ ] Converter JSON para string
- [ ] Adicionar variável no Cloud Run
- [ ] Fazer novo deploy
- [ ] Testar acesso à planilha
- [ ] Verificar logs no Cloud Run

## 📝 Nota de Segurança

⚠️ **NÃO adicione o arquivo JSON diretamente no repositório Git!**

O arquivo está corretamente no `.gitignore` por segurança. Usar variáveis de ambiente é a forma segura de passar credenciais para o Cloud Run.

