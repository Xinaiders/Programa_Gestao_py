# 📧 Configuração de E-mail para Notificações de Erro

Este documento explica como configurar o sistema para enviar e-mails automáticos quando ocorrem erros no sistema.

## 🎯 Funcionalidade

Quando ocorre qualquer erro não tratado no sistema, um e-mail é enviado automaticamente para o administrador (`marcosvinicius.info@gmail.com`) contendo:

- Tipo e mensagem do erro
- Traceback completo
- Contexto da requisição (URL, método HTTP, IP, usuário)
- Data/hora do erro
- Informações adicionais do contexto

## ⚙️ Configuração

### 1. Configurar Gmail (Recomendado)

Para usar Gmail, você precisa criar uma **Senha de App**:

1. Acesse: https://myaccount.google.com/apppasswords
2. Faça login na sua conta Google
3. Selecione "App" → "Mail"
4. Selecione "Outro (nome personalizado)" → Digite "Sistema Gestão"
5. Clique em "Gerar"
6. Copie a senha de 16 caracteres gerada

### 2. Configurar Variáveis de Ambiente

#### No Cloud Run (Produção):

```powershell
# Configurar servidor de e-mail (Gmail)
gcloud run services update programa-gestao-py `
  --region us-central1 `
  --update-env-vars MAIL_SERVER=smtp.gmail.com `
  --update-env-vars MAIL_PORT=587 `
  --update-env-vars MAIL_USE_TLS=true `
  --update-env-vars MAIL_USERNAME=seu-email@gmail.com `
  --update-env-vars MAIL_PASSWORD=sua-senha-de-app-de-16-caracteres `
  --update-env-vars MAIL_DEFAULT_SENDER=seu-email@gmail.com `
  --update-env-vars ERROR_EMAIL_RECIPIENT=marcosvinicius.info@gmail.com
```

#### Localmente (Desenvolvimento):

Crie um arquivo `.env` na raiz do projeto:

```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=seu-email@gmail.com
MAIL_PASSWORD=sua-senha-de-app-de-16-caracteres
MAIL_DEFAULT_SENDER=seu-email@gmail.com
ERROR_EMAIL_RECIPIENT=marcosvinicius.info@gmail.com
```

### 3. Outros Provedores de E-mail

#### Outlook/Hotmail:

```env
MAIL_SERVER=smtp-mail.outlook.com
MAIL_PORT=587
MAIL_USE_TLS=true
```

#### Yahoo:

```env
MAIL_SERVER=smtp.mail.yahoo.com
MAIL_PORT=587
MAIL_USE_TLS=true
```

## 📨 Estrutura do E-mail

O e-mail de erro contém:

```
⚠️ ERRO DETECTADO NO SISTEMA DE GESTÃO DE ESTOQUE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 INFORMAÇÕES DO ERRO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tipo de Erro: [Tipo]
Mensagem: [Mensagem]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 CONTEXTO DA REQUISIÇÃO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

URL: [URL]
Método HTTP: [GET/POST/etc]
IP do Cliente: [IP]
Usuário: [Usuário ou "Não autenticado"]
User-Agent: [Navegador]
Data/Hora: [Data/Hora]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 TRACEBACK COMPLETO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Traceback completo do erro]
```

## ✅ Verificação

Após configurar, você pode testar enviando um erro de teste (apenas em desenvolvimento):

```python
# Em uma rota de teste (apenas desenvolvimento)
@app.route('/testar-email-erro')
def testar_email_erro():
    if os.environ.get('FLASK_ENV') == 'production':
        return "❌ Não disponível em produção", 403
    raise Exception("Este é um erro de teste para verificar o envio de e-mail")
```

**⚠️ Não use em produção!**

## 🔒 Segurança

- **Nunca** commite o arquivo `.env` com senhas reais
- Use **Senha de App** do Google, nunca sua senha principal
- As senhas devem ser configuradas como variáveis de ambiente
- O e-mail padrão (`marcosvinicius.info@gmail.com`) já está configurado, mas pode ser alterado via `ERROR_EMAIL_RECIPIENT`

## 🐛 Troubleshooting

### E-mail não está sendo enviado

1. Verifique se `MAIL_USERNAME` e `MAIL_PASSWORD` estão configurados
2. Verifique os logs do Cloud Run para erros de conexão SMTP
3. Teste a conectividade SMTP localmente
4. Certifique-se de usar uma **Senha de App** (não a senha normal do Gmail)

### Erro "535 Authentication failed"

- Você está usando sua senha normal? Use uma **Senha de App** do Google
- Verifique se a autenticação de 2 fatores está habilitada (necessária para Senha de App)

### Erro "Connection timeout"

- Verifique se a porta 587 está aberta
- Tente usar a porta 465 com `MAIL_USE_SSL=true` e `MAIL_USE_TLS=false`

## 📝 Notas

- Erros HTTP conhecidos (404, 403, etc) **não** geram e-mail (apenas erros inesperados)
- O sistema tenta enviar o e-mail mesmo se o log falhar
- Se o envio de e-mail falhar, o erro ainda será logado normalmente


