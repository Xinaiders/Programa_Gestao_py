# 📁 Configuração de Pasta para PDFs

## Onde os PDFs são salvos?

**Configuração atual**: Os PDFs dos romaneios são salvos **localmente** na pasta:
- **Nome**: "Romaneios_Separacao"
- **Localização**: `Programa_Gestao_py/Romaneios_Separacao/`

**Opções disponíveis**:
- ✅ **Local**: Pasta no projeto (atual)
- ✅ **Google Drive**: Pasta na nuvem

## Como configurar uma pasta específica?

### Opção 1: Usar o script de configuração (Recomendado)

```bash
python configurar_pasta_pdf.py
```

O script irá:
1. Listar suas pastas do Google Drive
2. Permitir escolher uma pasta existente
3. Ou criar uma nova pasta
4. Salvar a configuração automaticamente

### Opção 2: Editar manualmente o arquivo de configuração

Edite o arquivo `config_pdf.py`:

```python
PDF_CONFIG = {
    # Pasta local (atual)
    'PASTA_DESTINO': "Romaneios_Separacao",
    
    # Tipo de armazenamento
    'TIPO_ARMAZENAMENTO': 'local',  # ou 'google_drive'
    
    'CRIAR_PASTA_AUTO': True,
    'NOME_PASTA_PADRAO': "Romaneios_Separacao"
}
```

## Exemplos de configuração

### Armazenamento local (atual):
```python
'TIPO_ARMAZENAMENTO': 'local',
'PASTA_DESTINO': "Romaneios_Separacao"
```

### Armazenamento no Google Drive:
```python
'TIPO_ARMAZENAMENTO': 'google_drive',
'PASTA_DESTINO': "Lineflex/Estoque/Romaneios"
```

### Pasta local personalizada:
```python
'TIPO_ARMAZENAMENTO': 'local',
'PASTA_DESTINO': "Meus_Romaneios"
```

## Como funciona?

1. **Criação de Romaneio**: PDF é gerado e salvo na pasta configurada
2. **Reimpressão**: Sistema busca o PDF na mesma pasta
3. **Organização**: Todos os PDFs ficam organizados em uma única pasta

## Estrutura de pastas

### Armazenamento Local (atual):
```
Programa_Gestao_py/
├── Romaneios_Separacao/             # Pasta local
│   ├── ROM-000001.pdf
│   ├── ROM-000002.pdf
│   └── ...
└── ...
```

### Armazenamento Google Drive:
```
Google Drive/
├── Romaneios de Separação/          # Pasta padrão
│   ├── ROM-000001.pdf
│   ├── ROM-000002.pdf
│   └── ...
└── Sua Pasta Personalizada/         # Pasta configurada
    ├── ROM-000001.pdf
    ├── ROM-000002.pdf
    └── ...
```

## Troubleshooting

### Pasta não encontrada
- Verifique se a pasta existe no Google Drive
- Confirme o nome exato da pasta
- Verifique permissões de acesso

### Erro de permissão
- Certifique-se de que a conta tem acesso ao Google Drive
- Verifique se as credenciais estão corretas

### PDF não aparece
- Aguarde alguns segundos para sincronização
- Verifique se o arquivo foi salvo corretamente
- Confirme se está na pasta correta
