import requests
import base64
from datetime import datetime, timedelta
from urllib.parse import quote
from calendar import monthrange
from collections import defaultdict
import locale
import os
from dateutil.parser import parse

# CONFIGURAÇÕES
JIRA_USER_EMAIL = "herbert.branco@stf.jus.br"
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_DOMAIN = "stfjira.atlassian.net"
JQL = 'project = 10323 and status NOT IN (Cancelado)'
CAMPOS = "summary,customfield_10065,customfield_10088,customfield_10057,customfield_10056,status,assignee"

# VERIFICAÇÃO DO TOKEN
if not JIRA_API_TOKEN:
    print("❌ JIRA_API_TOKEN não foi carregado.")
    exit(1)
else:
    print("✅ Token carregado com sucesso.")

# AUTENTICAÇÃO
auth = base64.b64encode(f"{JIRA_USER_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
headers = {
    "Authorization": f"Basic {auth}",
    "Accept": "application/json"
}

# CONSULTA AO JIRA COM PAGINAÇÃO
issues = []
start_at = 0
max_results = 100

print("⏳ Buscando mudanças no Jira...")

while True:
    url = (
        f"https://{JIRA_DOMAIN}/rest/api/3/search"
        f"?jql={quote(JQL)}"
        f"&fields={quote(CAMPOS)}"
        f"&startAt={start_at}"
        f"&maxResults={max_results}"
    )
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"❌ Erro na requisição: {response.status_code}")
        print(response.text)
        exit(1)

    data = response.json()
    page_issues = data.get("issues", [])
    issues.extend(page_issues)

    print(f"📄 Página com {len(page_issues)} mudanças carregadas (startAt={start_at})")

    if len(page_issues) < max_results:
        break  # Última página
    start_at += max_results

print(f"✅ {len(issues)} mudanças recebidas da API do Jira.")

# AGRUPAR MUDANÇAS POR DATA
mudancas_por_data = defaultdict(list)
for issue in issues:
    start = issue["fields"].get("customfield_10065")
    print(f"{issue['key']} - Data de início bruta: {start}")
    if isinstance(start, dict):
        start = start.get("value")
    if start:
        try:
            start_dt = parse(start).date()
            mudancas_por_data[start_dt].append(issue)
        except Exception as e:
            print(f"❌ Erro ao interpretar data da issue {issue['key']}: {start} - {e}")

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

# Filtrar mudanças do mês atual
mudancas_mes = [
    i for d, lst in mudancas_por_data.items()
    if d.month == mes and d.year == ano
    for i in lst
]
total_mes = len(mudancas_mes)

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

# HTML INICIAL
html = f"""
<html><head><meta charset="utf-8">
<title>Calendário de Mudanças</title>
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
.status-superior {{
    display: flex;
    justify-content: space-between;
    width: 94%;
    max-width: 860px;
    margin: 0 auto 8px auto;
    font-size: 12px;
    color: #6b7280;
}}
.legenda-status {{
    position: fixed;
    top: 72px;
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
.rodape {{
    margin: 30px auto;
    text-align: center;
    font-size: 12px;
    color: #6b7280;
}}
</style>
</head><body>
<div class='legenda-status'>
    <strong>Status das Mudanças:</strong><br>
    <span class='item-bar status-aprovacao'></span> Em aprovação<br>
    <span class='item-bar status-aguardando'></span> Aguardando execução<br>
    <span class='item-bar status-emexecucao'></span> Em execução<br>
    <span class='item-bar status-resolvido'></span> Resolvido<br>
    <span class='item-bar status-avaliacao'></span> Em avaliação<br>
    <span class='item-bar status-concluido'></span> Concluído<br>
    <span class='item-bar status-outros'></span> Outros status
</div>
<div class='mes-header'>
    <h2>Calendário de Mudanças - {nome_mes} {ano}</h2>
</div>
<div class='status-superior'>
    <div>Total de mudanças no mês: {total_mes}</div>
    <div>Última atualização: {hoje.strftime("%d/%m/%Y %H:%M:%S")}</div>
</div>
<table>
<tr>
<th>Seg</th><th>Ter</th><th>Qua</th><th>Qui</th><th>Sex</th><th>Sáb</th><th>Dom</th>
</tr>
"""

# FUNÇÕES AUXILIARES E MONTAGEM DO CALENDÁRIO (continua igual)

# ⬇️ (continue a partir da parte que renderiza os dias da tabela — igual ao seu código anterior)

# SALVAR HTML
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ HTML salvo como index.html")
