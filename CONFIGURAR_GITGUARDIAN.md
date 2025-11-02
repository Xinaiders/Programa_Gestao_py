# 🔒 Guia Completo: Configurar GitGuardian (ggshield)

Este guia vai te ajudar a configurar o **ggshield** para detectar segredos antes de fazer commit.

---

## 📋 O que é o ggshield?

O **ggshield** é uma ferramenta do GitGuardian que:
- ✅ Detecta segredos (senhas, tokens, API keys) **antes** de fazer commit
- ✅ Bloqueia commits perigosos automaticamente
- ✅ Funciona localmente, sem precisar enviar código para servidores
- ✅ É **GRATUITO** para uso pessoal

---

## 🚀 Opção 1: Instalação Rápida (Recomendada)

### Passo 1: Instalar ggshield

Abra o **PowerShell** e execute:

```powershell
pip install ggshield
```

Ou se você usa Python 3 especificamente:

```powershell
python -m pip install ggshield
```

### Passo 2: Autenticar com GitGuardian

Você precisa de um token do GitGuardian. Se ainda não tem:

1. Acesse: https://dashboard.gitguardian.com/
2. Faça login (ou crie conta gratuita)
3. Vá em **Settings** → **Tokens**
4. Crie um novo token (nome: "Meu Computador")

Depois, autentique localmente:

```powershell
ggshield auth login
```

Quando pedir, cole o token que você copiou.

### Passo 3: Testar se funcionou

Teste escaneando um arquivo:

```powershell
ggshield scan path .
```

Se funcionar, você verá uma lista de possíveis segredos encontrados (ou nenhum, se tudo estiver limpo).

---

## 🔧 Opção 2: Configurar Pre-Commit Hook (Automático)

Esta é a parte mais importante: fazer com que o ggshield **bloqueie automaticamente** commits perigosos.

### Passo 1: Instalar pre-commit

```powershell
pip install pre-commit
```

### Passo 2: Criar arquivo de configuração

Crie o arquivo `.pre-commit-config.yaml` na raiz do projeto:

```yaml
repos:
  - repo: https://github.com/gitguardian/ggshield
    rev: v1.21.0
    hooks:
      - id: ggshield
        language_version: python3
```

### Passo 3: Instalar o hook

```powershell
pre-commit install
```

### Passo 4: Testar

Tente fazer um commit de teste:

```powershell
git add .
git commit -m "teste"
```

Se houver algum segredo, o commit será **bloqueado automaticamente**! 🛡️

---

## 🎨 Opção 3: Extensão do VSCode (Detecção em Tempo Real)

Se você usa **Visual Studio Code**, pode instalar a extensão:

1. Abra o VSCode
2. Vá em **Extensions** (Ctrl+Shift+X)
3. Procure por: **"GitGuardian"**
4. Instale a extensão oficial do GitGuardian
5. Faça login com seu token (como no Passo 2 da Opção 1)

**Vantagem:** Você verá avisos **enquanto digita**, antes mesmo de salvar o arquivo!

---

## 📝 Como Funciona na Prática

### Cenário Normal (Sem Segredos)

```powershell
# Você faz alterações
git add app.py
git commit -m "Atualizar função X"

# ✅ Commit realizado com sucesso!
```

### Cenário com Segredo Detectado

```powershell
# Você tenta commitar arquivo com senha
git add arquivo_com_senha.py
git commit -m "Atualizar arquivo"

# ❌ ERRO: ggshield detectou uma senha!
# 
# ⚠️  Senha detectada na linha 45:
#     password = "minhasenha123"
#
# 🔒 Commit bloqueado por segurança!
```

### Como Resolver

1. **Remova o segredo** do código
2. **Use variáveis de ambiente** (`os.environ.get('PASSWORD')`)
3. **Ou adicione ao `.gitignore`** se for arquivo de teste

---

## 🔍 Comandos Úteis

### Escanear apenas um arquivo
```powershell
ggshield scan path arquivo.py
```

### Escanear todo o repositório
```powershell
ggshield scan path .
```

### Escanear apenas arquivos staged (que serão commitados)
```powershell
ggshield scan commit
```

### Ver histórico de scans
```powershell
ggshield scan history
```

---

## ⚙️ Configurações Avançadas

### Ignorar falsos positivos

Se o ggshield detectar algo que **não é um segredo** (falso positivo), você pode ignorá-lo criando o arquivo `.gitguardian.yaml`:

```yaml
paths-ignore:
  - "**/teste_fake_password.py"
  
matches-ignore:
  - name: "Falso positivo em arquivo X"
    match: "password123"
```

### Configurar exceções por padrão

```yaml
paths-ignore:
  - "**/*.example"
  - "**/test_data/**"
```

---

## 🐛 Troubleshooting

### Erro: "ggshield: command not found"

**Solução:**
```powershell
# Reinstalar
pip uninstall ggshield
pip install ggshield

# Verificar instalação
python -m ggshield --version
```

### Erro: "Token inválido"

**Solução:**
1. Verifique se o token está correto
2. Refaça o login: `ggshield auth login`
3. Ou defina manualmente: `$env:GG_SHIELD_TOKEN="seu-token-aqui"`

### Pre-commit não está bloqueando

**Solução:**
```powershell
# Verificar se está instalado
pre-commit --version

# Reinstalar hooks
pre-commit uninstall
pre-commit install

# Testar manualmente
pre-commit run --all-files
```

---

## 📚 Recursos Adicionais

- **Documentação oficial:** https://docs.gitguardian.com/internal-repositories-monitoring/integrations/git_hooks/pre_commit
- **Dashboard:** https://dashboard.gitguardian.com/
- **Tutorial em vídeo:** https://www.youtube.com/watch?v=VIDEO_ID (do e-mail)

---

## ✅ Checklist Final

- [ ] ✅ ggshield instalado (`ggshield --version`)
- [ ] ✅ Autenticado (`ggshield auth status`)
- [ ] ✅ Pre-commit instalado (`pre-commit --version`)
- [ ] ✅ Hook configurado (`.pre-commit-config.yaml` criado)
- [ ] ✅ Teste realizado (commit bloqueado quando detectar segredo)
- [ ] ✅ Extensão VSCode instalada (opcional, mas recomendado)

---

## 🎯 Próximos Passos

1. **Teste agora mesmo:** Tente fazer um commit com um arquivo que contenha "password123" e veja o bloqueio funcionar!

2. **Escaneie seu histórico:** 
   ```powershell
   ggshield scan commit-range HEAD~10..HEAD
   ```

3. **Configure a equipe:** Compartilhe este guia com outros desenvolvedores do projeto!

---

**🔒 Agora seu código está protegido automaticamente!**

