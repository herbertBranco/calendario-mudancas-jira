
# 🗓️ Calendário de Mudanças - Jira Cloud

Este projeto gera automaticamente um calendário visual com as mudanças agendadas no Jira Cloud, agrupadas por data e status, e o publica via GitHub Pages.

## 🔧 O que este repositório faz

- Consulta a API do Jira Cloud usando JQL.
- Agrupa as mudanças por data de início.
- Gera um arquivo `index.html` com um calendário mensal.
- Exibe status com códigos de cores (aguardando, em execução, resolvido, etc.).
- Mostra tooltips detalhados e links diretos para os chamados no Jira.
- Publica a visualização no GitHub Pages.
- Executa tudo automaticamente a cada minuto via GitHub Actions.

## 🖼️ Exemplo de visualização

Acesse a visualização mais recente aqui:  
📍 [https://herbertbranco.github.io/calendario-mudancas-jira](https://herbertbranco.github.io/calendario-mudancas-jira)

## ⚙️ Estrutura do Projeto

```
├── .github/
│   └── workflows/
│       └── run-python.yml  # Workflow de automação
├── index.html              # Arquivo gerado com o calendário
├── script.py               # Script Python que gera o HTML
└── README.md               # Este arquivo
```

## 💡 Como funciona

### 1. Script em Python (`script.py`)
Consulta a API do Jira usando autenticação básica (e-mail + token via variável de ambiente), extrai informações relevantes e gera um calendário HTML estilizado com CSS inline.

### 2. GitHub Actions (`run-python.yml`)
Automação que roda o script a cada minuto e publica a página.

### 3. GitHub Pages
Publica automaticamente o conteúdo de `index.html` na web.

## 🪄 Agendamento automático

O agendamento usa a seguinte expressão cron:

```yaml
schedule:
  - cron: '* * * * *'  # A cada minuto (UTC)
```

## 🔐 Configuração de segredo

No repositório GitHub:

1. Vá em `Settings > Secrets and variables > Actions > New repository secret`.
2. Nome: `JIRA_API_TOKEN`
3. Valor: Seu token de API do Jira Cloud.

> O e-mail do usuário Jira está fixado no código como `herbert.branco@stf.jus.br`.

## 🖥️ Requisitos para execução local

Se quiser rodar o script manualmente:

```bash
python script.py
```

Certifique-se de ter as bibliotecas:
```bash
pip install requests python-dateutil
```

## 🧩 Tecnologias utilizadas

- Python 3.x
- GitHub Actions
- GitHub Pages
- Jira Cloud REST API
- HTML + CSS puro

## 📌 Observações

- Os horários são ajustados para o fuso de Brasília (UTC-3) diretamente no script.
- Os status das mudanças são interpretados por nome e categorizados por cor.
- O calendário exibe apenas o ano corrente.
- Links diretos por dia levam a um filtro JQL dinâmico no Jira.

---

🛠️ Desenvolvido e mantido por Herbert HBT  
📧 herbert.branco@stf.jus.br
