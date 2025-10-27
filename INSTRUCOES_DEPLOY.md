# 🚀 Instruções de Deploy no Google Cloud Run

## 📋 Fluxo Completo

### Passo 1: Autorizar Cloud Build
✅ Clique em **"Configurar com o Cloud Build"**

### Passo 2: Selecionar Repositório GitHub
1. **Autorize o Google Cloud** a acessar seu GitHub
2. **Selecione** a conta: `Xinaiders`
3. **Escolha o repositório**: `Programa-_GestaoPedidos_python`
4. **Branch**: `main` ou `master`
5. **Build configuration**: **Automático** ou **Detect**

### Passo 3: Configurar Serviço

**Nome do Serviço:**
```
sistema-gestao-estoque
```

**Região:**
Escolha: `us-central1` ou `southamerica-east1` (São Paulo)

**Autenticação:**
✅ Selecione: **"Permitir acesso público"** (para testes)

### Passo 4: Variáveis de Ambiente

Vá em **"Variables & Secrets"** ou **"Environment Variables"**

Adicione:

```
SECRET_KEY=sua-chave-secreta-aleatoria-gerada-aqui
DATABASE_URL=sqlite:///estoque.db
```

**Para gerar SECRET_KEY seguro:**
```python
import secrets
print(secrets.token_urlsafe(32))
```

### Passo 5: Credenciais do Google Sheets

**Opção A - Via Console:**
1. Console → **Secret Manager**
2. Criar novo secret
3. Colar conteúdo do arquivo JSON
4. Configurar variável de ambiente apontando para o secret

**Opção B - Temporário (não recomendado):**
Upload do arquivo JSON via Cloud Storage e configurar path.

### Passo 6: Deploy

✅ Clique em **"Deploy"** ou **"Create"**

⏱️ Aguarde 5-10 minutos (primeira vez)

---

## 🎯 Depois do Deploy

### Acessar aplicação:
```
https://sistema-gestao-estoque-[hash].region.run.app
```

### Verificar logs:
- Cloud Console → Cloud Run → Seu serviço → **Logs**

### Editar configurações:
- Clique em **"Edit & Deploy New Revision"**

---

## 🔐 Configurações de Segurança (Após Testes)

### Alterar autenticação:
1. Editar serviço
2. **Autenticação**: **"Autenticação necessária"**
3. Configurar IAM ou IAP

### Configurar domínio customizado (Opcional):
1. Cloud Run → Gerenciar domínios mapeados
2. Adicionar domínio

---

## 🆘 Troubleshooting

### Erro: "Module not found"
- Verificar `requirements.txt`
- Logs: Cloud Console → Cloud Run → Logs

### Erro: "DATABASE_URL"
- Verificar variáveis de ambiente
- Testar com SQLite primeiro

### Erro: "Permission denied" (Google Sheets)
- Verificar Service Account
- Configurar credenciais corretas

---

## 📚 Próximos Passos Recomendados

1. ✅ Deploy funcional
2. 🔄 Migrar para Cloud SQL
3. 🔄 Configurar backups
4. 🔄 Habilitar autenticação
5. 🔄 Configurar domínio

---

## 📝 Checklist de Deploy

- [ ] Código no GitHub
- [ ] Cloud Build autorizado
- [ ] Repositório conectado
- [ ] Nome do serviço definido
- [ ] Região selecionada
- [ ] Variáveis de ambiente configuradas
- [ ] SECRET_KEY definido
- [ ] Credenciais configuradas
- [ ] Autenticação configurada (pública para testes)
- [ ] Deploy executado
- [ ] URL funcionando
- [ ] Testar login
- [ ] Verificar funcionalidades

---

**✅ Siga esses passos e seu sistema estará no ar!**

