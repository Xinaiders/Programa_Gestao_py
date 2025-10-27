# 🔍 Como Verificar o Branch Correto

## Opção 1: Ver no GitHub Desktop

1. Abra o **GitHub Desktop**
2. No topo, veja o nome da branch atual (provavelmente `main` ou `master`)
3. Anote esse nome

## Opção 2: Ver no GitHub Web

1. Acesse: https://github.com/Xinaiders/programa-gestao-pedidos-python
2. Olhe no topo da página, ao lado do nome do repositório
3. Veja qual é o branch padrão (provavelmente mostra "main" ou "master")

## Opção 3: Ver se o push foi feito

1. Confirme que você **fez push** das alterações
2. Veja se o código está realmente no GitHub
3. Se não estiver, faça o push primeiro

## Correções Possíveis

### Se o branch for "master" (não "main"):
No Cloud Run, onde está `^main$`, mude para:
```
^master$
```

### Se o branch for outro nome:
Use esse nome exato.

### Exemplo de regex para aceitar qualquer branch:
```
.*
```
(Mas não recomendado - use o nome correto)

---

**📝 Depois de ajustar:**
1. Clique em **"Salvar"**
2. Aguarde o deploy iniciar

