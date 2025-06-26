import requests
import base64
from datetime import datetime
from urllib.parse import quote
from calendar import monthrange, Calendar
from collections import defaultdict
import locale

# CONFIGURAÇÕES
JIRA_USER_EMAIL = "SEU_EMAIL@exemplo.com"
JIRA_API_TOKEN = "SEU_TOKEN"
JIRA_URL = "https://SEU_DOMINIO.atlassian.net"
PROJETO = "10323"
locale.setlocale(locale.LC_TIME, "pt_BR.UTF-8")

# MÊS E ANO ATUAL
hoje = datetime.now()
ano = hoje.year
mes = hoje.month
nome_mes = hoje.strftime('%B').capitalize()

# INTERVALO DO MÊS
data_inicio = f"{ano}-{mes:02d}-01"
_, ultimo_dia = monthrange(ano, mes)
data_fim = f"{ano}-{mes:02d}-{ultimo_dia}"

# JQL
campo_data = "Data e hora de início da execução"
jql = f'project={PROJETO} AND "{campo_data}" >= "{data_inicio}" AND "{campo_data}" <= "{data_fim}" ORDER BY "{campo_data}" ASC'

# HEADERS
auth = base64.b64encode(f"{JIRA_USER_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
headers = {
    "Authorization": f"Basic {auth}",
    "Content-Type": "application/json"
}

# CAMPOS PERSONALIZADOS (ajuste conforme necessário)
custom_fields = {
    "tipo": "customfield_10088",
    "unidade": "customfield_10056"
}

# CONSULTA PAGINADA
issues = []
start_at = 0
max_results = 100

while True:
    url = f"{JIRA_URL}/rest/api/3/search?jql={quote(jql)}&startAt={start_at}&maxResults={max_results}"
    response = requests.get(url, headers=headers)
    data = response.json()
    issues.extend(data["issues"])
    if start_at + max_results >= data["total"]:
        break
    start_at += max_results

# AGRUPAMENTO POR DIA
calendario = defaultdict(list)

for issue in issues:
    campos = issue["fields"]
    data_inicio_exec = campos.get(campo_data.replace(" ", "_").lower())
    if data_inicio_exec:
        data_obj = datetime.strptime(data_inicio_exec[:10], "%Y-%m-%d")
        status = campos["status"]["name"]
        chave = issue["key"]
        resumo = campos["summary"]
        tipo = campos.get(custom_fields["tipo"], {}).get("value", "")
        unidade = campos.get(custom_fields["unidade"], {}).get("value", "")
        url_chave = f"{JIRA_URL}/browse/{chave}"
        calendario[data_obj.day].append({
            "status": status,
            "chave": chave,
            "resumo": resumo,
            "tipo": tipo,
            "unidade": unidade,
            "url": url_chave
        })

# HTML
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
.atualizacao-wrapper {{
    width: 94%;
    max-width: 860px;
    margin: auto;
    display: flex;
    justify-content: space-between;
    color: #6b7280;
    font-size: 12px;
    margin-bottom: 4px;
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
<div class='atualizacao-wrapper'>
    <div>Última atualização: {hoje.strftime("%d/%m/%Y %H:%M:%S")}</div>
    <div>Total de mudanças no mês: {len(issues)}</div>
</div>
<table>
<tr>
<th>Seg</th><th>Ter</th><th>Qua</th><th>Qui</th><th>Sex</th><th>Sáb</th><th>Dom</th>
</tr>
"""

# CALENDÁRIO
cal = Calendar(firstweekday=0)
semanas = cal.monthdayscalendar(ano, mes)

for semana in semanas:
    html += "<tr>"
    for dia in semana:
        if dia == 0:
            html += "<td></td>"
        else:
            items = calendario[dia]
            html += f"<td><div class='data-dia'>{dia}</div>"
            for item in items:
                status = item["status"].lower().replace(" ", "")
                if "aprova" in status:
                    cor = "status-aprovacao"
                elif "aguardando" in status:
                    cor = "status-aguardando"
                elif "execuç" in status or "emexecucao" in status:
                    cor = "status-emexecucao"
                elif "resolvido" in status:
                    cor = "status-resolvido"
                elif "avalia" in status:
                    cor = "status-avaliacao"
                elif "conclu" in status:
                    cor = "status-concluido"
                else:
                    cor = "status-outros"
                html += f"<a href='{item['url']}' title='{item['chave']} - {item['resumo']}' target='_blank'><span class='item-bar {cor}'></span></a>"
            if items:
                html += f"<div class='contador'>{len(items)} mudança(s)</div>"
            html += "</td>"
    html += "</tr>"

# RODAPÉ
html += """
</table>
<div class='rodape'>Desenvolvido por Herbert HBT - Versão 2.0</div>
</body></html>
"""

# SALVAR ARQUIVO
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ HTML salvo como index.html")
