# 🔐 Guia Rápido: Autenticar no GitGuardian

## Passo a Passo

### 1️⃣ Acesse o Dashboard do GitGuardian

Abra seu navegador e vá para:
**https://dashboard.gitguardian.com/**

### 2️⃣ Faça Login ou Crie Conta

- Se já tem conta: faça login
- Se não tem: clique em "Sign up" (é **GRATUITO** para uso pessoal)

### 3️⃣ Crie um Token

Depois de fazer login:

1. Clique no seu **perfil/avatar** no canto superior direito
2. Vá em **Settings** (Configurações)
3. No menu lateral, clique em **Tokens** ou **API Tokens**
4. Clique em **"Create token"** ou **"New token"**
5. Dê um nome para o token (ex: "Meu Computador" ou "Windows")
6. Clique em **"Create"** ou **"Generate"**
7. **COPIE O TOKEN** que aparece na tela (é a única vez que você verá ele completo!)

⚠️ **IMPORTANTE:** O token será mostrado apenas uma vez. Copie e salve em um lugar seguro!

### 4️⃣ Autenticar no Terminal

Volte ao PowerShell e execute:

```powershell
ggshield auth login
```

Quando pedir, cole o token que você copiou e pressione Enter.

### 5️⃣ Verificar se Funcionou

Execute:

```powershell
ggshield api-status
```

Se mostrar informações da API, está tudo certo! ✅

---

## 🎯 Pronto!

Agora o GitGuardian vai proteger seus commits automaticamente!

