import requests                   # Biblioteca para fazer requisições HTTP
import base64                     # Biblioteca para codificação em base64 (usada na autenticação)
from datetime import datetime, timedelta  # Manipulação de datas e horas
from urllib.parse import quote    # Para codificar parâmetros na URL (JQL e campos)
from calendar import monthrange  # Para obter o primeiro dia da semana e o total de dias do mês
from collections import defaultdict  # Dicionário que cria lista automaticamente para cada nova chave
import locale                     # Para manipular a localidade (idioma/país) e formatar datas
import os                         # Para acessar variáveis de ambiente (token)
from dateutil.parser import parse  # Para interpretar strings de datas em objetos datetime

# CONFIGURAÇÕES: dados fixos para a API do Jira e consulta
JIRA_USER_EMAIL = "herbert.branco@stf.jus.br"   # Seu email para autenticação no Jira
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")    # Token da API obtido da variável de ambiente (não exposto no código)
JIRA_DOMAIN = "stfjira.atlassian.net"            # Domínio Jira da sua organização
JQL = 'project = 10323 and status NOT IN (Cancelado)'  # Consulta Jira Query Language para filtrar issues
CAMPOS = "summary,customfield_10065,customfield_10088,customfield_10057,customfield_10056,status,assignee"  # Campos a retornar da API

# VERIFICAÇÃO DO TOKEN: garante que o token foi carregado antes de continuar
if not JIRA_API_TOKEN:
    print("❌ JIRA_API_TOKEN não foi carregado.")
    exit(1)  # Encerra o script se o token não foi encontrado
else:
    print("✅ Token carregado com sucesso.")

# AUTENTICAÇÃO: codifica email e token em base64 para o cabeçalho Authorization
auth = base64.b64encode(f"{JIRA_USER_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
headers = {
    "Authorization": f"Basic {auth}",  # Autenticação básica HTTP
    "Accept": "application/json"       # Espera resposta no formato JSON
}

# CONSULTA AO JIRA: monta URL da API e executa GET para buscar issues
url = f"https://{JIRA_DOMAIN}/rest/api/3/search?jql={quote(JQL)}&fields={quote(CAMPOS)}&maxResults=100"
response = requests.get(url, headers=headers)

# Verifica se a requisição teve sucesso
if response.status_code != 200:
    print(f"❌ Erro na requisição: {response.status_code}")
    print(response.text)
    exit(1)
else:
    issues = response.json().get("issues", [])  # Extrai a lista de issues da resposta JSON
    print(f"✅ {len(issues)} mudanças recebidas da API do Jira.")

# AGRUPAR MUDANÇAS POR DATA: cria um dicionário onde chave é data e valor é lista de issues daquele dia
mudancas_por_data = defaultdict(list)
for issue in issues:
    start = issue["fields"].get("customfield_10065")  # Data de início da mudança (campo customizado)
    print(f"{issue['key']} - Data de início bruta: {start}")
    # Às vezes o valor é um dict, então pega o valor string
    if isinstance(start, dict):
        start = start.get("value")
    if start:
        try:
            start_dt = parse(start).date()  # Converte string para objeto date (apenas data)
            mudancas_por_data[start_dt].append(issue)  # Adiciona issue à lista do dia correspondente
        except Exception as e:
            print(f"❌ Erro ao interpretar data da issue {issue['key']}: {start} - {e}")

# DEFINIR MÊS CORRENTE: pega data atual (ajustada -3 horas para fuso horário local)
hoje = datetime.now() - timedelta(hours=3)
ano = hoje.year
mes = hoje.month

# Nome do mês em português: tenta definir locale para pt_BR.UTF-8 para formatar nome do mês
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
    nome_mes = datetime(ano, mes, 1).strftime("%B").capitalize()  # Ex: "Junho"
except:
    # Se locale não disponível, usa dicionário manual de meses
    meses_pt = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
        7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    nome_mes = meses_pt[mes]

# FUNÇÃO PARA GERAR TOOLTIP: monta texto que aparecerá ao passar o mouse sobre um item
def gerar_tooltip(issue):
    key = issue["key"]  # Código da issue
    summary = issue["fields"].get("summary", "").replace('"', "'")  # Resumo da mudança (evita aspas duplas)
    tipo = issue["fields"].get("customfield_10088")  # Tipo da mudança (campo customizado)
    tipo_valor = tipo["value"] if isinstance(tipo, dict) else "Sem tipo"
    motivo = issue["fields"].get("customfield_10057")  # Motivo da mudança (campo customizado)
    motivo_valor = motivo["value"] if isinstance(motivo, dict) else "Sem motivo"
    unidade = issue["fields"].get("customfield_10056")  # Unidade executora (campo customizado)
    unidade_pai = unidade.get("value") if isinstance(unidade, dict) else "Sem unidade"
    unidade_filho = unidade.get("child", {}).get("value") if isinstance(unidade, dict) else ""
    assignee = issue["fields"].get("assignee")  # Responsável
    responsavel = assignee.get("displayName") if assignee else "Sem responsável"
    status = issue["fields"].get("status", {}).get("name", "Sem status")

    # Retorna string formatada com as informações para exibir no tooltip
    return (
        f"{key}\n"
        f"Tipo: {tipo_valor}\n"
        f"Status: {status}\n"
        f"Resumo: {summary}\n"
        f"Motivo: {motivo_valor}\n"
        f"Unidade executora: {unidade_pai} / {unidade_filho}\n"
        f"Responsável: {responsavel}"
    )

# INÍCIO DO HTML: estilização CSS + estrutura base da página e tabela
html = f"""
<html><head><meta charset="utf-8">
<style>
body {{
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
    background-color: #f9fafb;
    margin: 0;
    padding: 0;
}}
table {{
    border-collapse: collapse;
    width: 94%;
    max-width: 860px;
    margin: auto;
    margin-left: 200px;
    background-color: white;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}}
td, th {{
    border: 1px solid #e5e7eb;
    width: 14.2%;
    height: 80px;
    vertical-align: top;
    padding: 4px;
    font-size: 13px;
    position: relative;
}}
th {{
    background-color: #f3f4f6;
    color: #374151;
    font-size: 13px;
    height: 30px;
}}
.data-dia {{
    font-size: 12px;
    font-weight: bold;
    color: #111827;
    margin-bottom: 4px;
}}
.item-container {{
    margin-top: 18px;
}}
.item-bar {{
    width: 10px;
    height: 10px;
    display: inline-block;
    margin: 1px 1px 1px 0;
    border-radius: 50%;
}}
.status-aprovacao {{ background-color: #dc2626; }}
.status-aguardando {{ background-color: #facc15; }}
.status-emexecucao {{ background-color: #fb923c; }}
.status-resolvido {{ background-color: #8b5cf6; }}
.status-avaliacao {{ background-color: #1d4ed8; }}
.status-concluido {{ background-color:  #10b981; }}
.status-outros {{ background-color: #a3a3a3; }}
.contador {{
    font-size: 10px;
    color: #6b7280;
    margin-top: 4px;
    text-align: right;
}}
.mes-header {{
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    margin: 16px 0 8px 0;
    color: #1f2937;
}}
.mes-header h2 {{
    font-size: 20px;
    margin: 0;
}}
.atualizacao {{
    font-size: 12px;
    color: #6b7280;
    margin-top: 4px;
}}
.legenda-status {{
    position: fixed;
    top: 16px;
    left: 16px;
    background: rgba(255, 255, 255, 0.95);
    padding: 10px 12px;
    border-radius: 10px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    font-size: 12px;
    color: #1f2937;
    z-index: 1000;
    max-width: 200px;
    line-height: 1.5;
}}
</style>
</head><body>
<div class='legenda-status'>
    <strong>Legenda de status:</strong><br>
    <span class='item-bar status-aprovacao'></span> Em aprovação<br>
    <span class='item-bar status-aguardando'></span> Aguardando execução<br>
    <span class='item-bar status-emexecucao'></span> Em execução<br>
    <span class='item-bar status-resolvido'></span> Resolvido<br>
    <span class='item-bar status-avaliacao'></span> Em avaliação<br>
    <span class='item-bar status-concluido'></span> Concluído<br>
    <span class='item-bar status-outros'></span> Outros status
</div>
<div class='mes-header'>
    <h2>{nome_mes} {ano}</h2>  <!-- Título com mês e ano -->
    <div class='atualizacao'>Última atualização: {hoje.strftime("%d/%m/%Y %H:%M:%S")}</div>  <!-- Data e hora da execução -->
</div>
<table>
<tr>
<th>Dom</th><th>Seg</th><th>Ter</th><th>Qua</th><th>Qui</th><th>Sex</th><th>Sáb</th>
</tr>
"""

# CALENDÁRIO: obtém o primeiro dia da semana e o total de dias do mês atual
primeiro_dia_semana, total_dias = monthrange(ano, mes)

dia = 1
linha = "<tr>" + "<td></td>" * primeiro_dia_semana  # Preenche os dias vazios antes do 1º dia do mês

# Função que gera link JQL para listar todas as mudanças de um dia específico
def gerar_jql_link(data):
    data_str = data.strftime("%Y-%m-%d")
    jql_dia = f'project=10323 AND "Data e hora de início da execução" >= "{data_str}" AND "Data e hora de início da execução" < "{data_str} 23:59"'

