import requests
import base64
from datetime import datetime, timedelta
from urllib.parse import quote
from calendar import monthrange
from collections import defaultdict
import locale
import os

# CONFIGURAÇÕES
JIRA_USER_EMAIL = "herbert.branco@stf.jus.br"
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_DOMAIN = "stfjira.atlassian.net"
JQL = 'project = 10323'
CAMPOS = "summary,customfield_10065,customfield_10088,customfield_10057,customfield_10056,status,assignee"

# AUTENTICAÇÃO
auth = base64.b64encode(f"{JIRA_USER_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
headers = {
    "Authorization": f"Basic {auth}",
    "Accept": "application/json"
}

# CONSULTA AO JIRA
url = f"https://{JIRA_DOMAIN}/rest/api/3/search?jql={quote(JQL)}&fields={quote(CAMPOS)}&maxResults=100"
response = requests.get(url, headers=headers)
if response.status_code != 200:
    print(f"❌ Erro na requisição: {response.status_code}")
    print(response.text)
    exit(1)
else:
    issues = response.json().get("issues", [])
    print(f"✅ {len(issues)} mudanças recebidas da API do Jira.")

issues = response.json().get("issues", [])

# AGRUPAR MUDANÇAS POR DATA
mudancas_por_data = defaultdict(list)
for issue in issues:
    start = issue["fields"].get("customfield_10065")
    if isinstance(start, dict):
        start = start.get("value")
    if start:
        try:
            start_dt = datetime.fromisoformat(start).date()
            mudancas_por_data[start_dt].append(issue)
        except ValueError:
            continue

# DEFINIR MÊS CORRENTE
hoje = datetime.now() - timedelta(hours=3)
ano = hoje.year
mes = hoje.month

# Nome do mês em português
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
    nome_mes = datetime(ano, mes, 1).strftime("%B").capitalize()
except:
    meses_pt = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
        7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    nome_mes = meses_pt[mes]

# TOOLTIP
def gerar_tooltip(issue):
    key = issue["key"]
    summary = issue["fields"].get("summary", "").replace('"', "'")
    tipo = issue["fields"].get("customfield_10088")
    tipo_valor = tipo["value"] if isinstance(tipo, dict) else "Sem tipo"

    motivo = issue["fields"].get("customfield_10057")
    motivo_valor = motivo["value"] if isinstance(motivo, dict) else "Sem motivo"

    unidade = issue["fields"].get("customfield_10056")
    unidade_pai = unidade.get("value") if isinstance(unidade, dict) else "Sem unidade"
    unidade_filho = unidade.get("child", {}).get("value") if isinstance(unidade, dict) else ""

    assignee = issue["fields"].get("assignee")
    responsavel = assignee.get("displayName") if assignee else "Sem responsável"

    status = issue["fields"].get("status", {}).get("name", "Sem status")

    return (
        f"{key}\n"
        f"Tipo: {tipo_valor}\n"
        f"Status: {status}\n"
        f"Resumo: {summary}\n"
        f"Motivo: {motivo_valor}\n"
        f"Unidade executora: {unidade_pai} / {unidade_filho}\n"
        f"Responsável: {responsavel}"
    )

# HTML
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
.status-aguardando {{ background-color: #facc15; }}
.status-emexecucao {{ background-color: #fb923c; }}
.status-resolvido {{ background-color: #8b5cf6; }}
.status-avaliacao {{ background-color: #1d4ed8; }}
.status-concluido {{ background-color:  #10b981; }}
.status-outros {{ background-color: #ef4444; }}
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
    <span class='item-bar status-aguardando'></span> Aguardando execução<br>
    <span class='item-bar status-emexecucao'></span> Em execução<br>
    <span class='item-bar status-resolvido'></span> Resolvido<br>
    <span class='item-bar status-avaliacao'></span> Em avaliação<br>
    <span class='item-bar status-concluido'></span> Concluído<br>
    <span class='item-bar status-outros'></span> Outros status
</div>
<div class='mes-header'>
    <h2>{nome_mes} {ano}</h2>
    <div class='atualizacao'>Última atualização: {hoje.strftime("%d/%m/%Y %H:%M:%S")}</div>
</div>
<table>
<tr>
<th>Dom</th><th>Seg</th><th>Ter</th><th>Qua</th><th>Qui</th><th>Sex</th><th>Sáb</th>
</tr>
"""

primeiro_dia_semana, total_dias = monthrange(ano, mes)
dia = 1
linha = "<tr>" + "<td></td>" * primeiro_dia_semana

def gerar_jql_link(data):
    data_str = data.strftime("%Y-%m-%d")
    jql_dia = f'project=10323 AND "Data e hora de início da execução" >= "{data_str}" AND "Data e hora de início da execução" < "{data_str} 23:59"'
    return f"https://{JIRA_DOMAIN}/issues/?jql={quote(jql_dia)}"

def cor_status(status):
    status = status.lower()
    if "aguardando" in status:
        return "status-aguardando"
    elif "execução" in status:
        return "status-emexecucao"
    elif "resolvido" in status:
        return "status-resolvido"
    elif "avaliação" in status:
        return "status-avaliacao"
    elif "concluído" in status or "concluido" in status:
        return "status-concluido"
    else:
        return "status-outros"

for i in range(primeiro_dia_semana, 7):
    data_atual = datetime(ano, mes, dia).date()
    itens = mudancas_por_data.get(data_atual, [])
    linha += f"<td><div class='data-dia'>{dia}</div><div class='item-container'>"
    for item in itens:
        key = item["key"]
        status_nome = item["fields"].get("status", {}).get("name", "")
        cor = cor_status(status_nome)
        link = f"https://{JIRA_DOMAIN}/browse/{key}"
        tooltip = gerar_tooltip(item)
        linha += f"<a href='{link}' target='_blank' title=\"{tooltip}\"><div class='item-bar {cor}'></div></a>"
    linha += "</div>"
    if itens:
        jql_link = gerar_jql_link(data_atual)
        linha += f"<div class='contador'><a href='{jql_link}' target='_blank'>Total de mudanças: {len(itens)}</a></div>"
    linha += "</td>"
    dia += 1
html += linha + "</tr>\n"

while dia <= total_dias:
    linha = "<tr>"
    for _ in range(7):
        if dia > total_dias:
            linha += "<td></td>"
        else:
            data_atual = datetime(ano, mes, dia).date()
            itens = mudancas_por_data.get(data_atual, [])
            linha += f"<td><div class='data-dia'>{dia}</div><div class='item-container'>"
            for item in itens:
                key = item["key"]
                status_nome = item["fields"].get("status", {}).get("name", "")
                cor = cor_status(status_nome)
                link = f"https://{JIRA_DOMAIN}/browse/{key}"
                tooltip = gerar_tooltip(item)
                linha += f"<a href='{link}' target='_blank' title=\"{tooltip}\"><div class='item-bar {cor}'></div></a>"
            linha += "</div>"
            if itens:
                jql_link = gerar_jql_link(data_atual)
                linha += f"<div class='contador'><a href='{jql_link}' target='_blank'>Total de mudanças: {len(itens)}</a></div>"
            linha += "</td>"
        dia += 1
    html += linha + "</tr>\n"

html += "</table></body></html>"

# SALVAR

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

if not JIRA_API_TOKEN:
    print("❌ JIRA_API_TOKEN não foi carregado.")
else:
    print("✅ Token carregado com sucesso.")


# print("✅ Calendário atualizado com nova distinção de cores.")
