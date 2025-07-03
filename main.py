import requests
import base64
from datetime import datetime, timedelta
from urllib.parse import quote
from calendar import monthrange, Calendar
from collections import defaultdict
import locale
import os
from dateutil.parser import parse
from html import escape

# CONFIGURAÇÕES
JIRA_USER_EMAIL = "herbert.branco@stf.jus.br"
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
if not JIRA_API_TOKEN:
    print("❌ JIRA_API_TOKEN não foi carregado.")
    exit(1)
JIRA_DOMAIN = "stfjira.atlassian.net"
JQL = 'project = 10323 and status NOT IN (Cancelado)'
CAMPOS = "summary,customfield_10065,customfield_10067,customfield_10088,customfield_10057,customfield_10056,status,assignee,customfield_10902"

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
    url = f"https://{JIRA_DOMAIN}/rest/api/3/search"
    params = {
        "jql": JQL,
        "fields": CAMPOS,
        "startAt": start_at,
        "maxResults": max_results
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"❌ Erro na requisição: {response.status_code}")
        print(response.text)
        exit(1)

    data = response.json()
    batch = data.get("issues", [])
    issues.extend(batch)

    print(f"📄 Página com {len(batch)} mudanças carregadas (startAt={start_at})")

    if len(batch) < max_results:
        break
    start_at += max_results

print(f"✅ {len(issues)} mudanças recebidas da API do Jira.")

# AGRUPAR MUDANÇAS POR DATA INCLUINDO INTERVALO ENTRE INÍCIO E FIM
mudancas_por_data = defaultdict(list)
for issue in issues:
    start_raw = issue["fields"].get("customfield_10065")
    end_raw = issue["fields"].get("customfield_10067")
    if isinstance(start_raw, dict):
        start_raw = start_raw.get("value")
    if isinstance(end_raw, dict):
        end_raw = end_raw.get("value")
    if start_raw:
        try:
            start_dt = parse(start_raw).date()
            end_dt = parse(end_raw).date() if end_raw else start_dt
            delta = (end_dt - start_dt).days
            for i in range(delta + 1):
                dia = start_dt + timedelta(days=i)
                mudancas_por_data[dia].append(issue)
        except Exception as e:
            print(f"Erro ao processar intervalo '{start_raw}' a '{end_raw}': {e}")

# DEFINIÇÕES
hoje = datetime.now() - timedelta(hours=3)
ano = hoje.year

# LOCALE PT-BR
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    pass

meses_pt = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

meses_pt_abrev = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

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
    unidade_filho = unidade.get("child", {}).get("value") if isinstance(unidade, dict) and unidade.get("child") else ""
    assignee = issue["fields"].get("assignee")
    responsavel = assignee.get("displayName") if assignee else "Sem responsável"
    status = issue["fields"].get("status", {}).get("name", "Sem status")
    area_tecnologia = issue["fields"].get("customfield_10902")
    area_tecnologia_val = area_tecnologia["value"] if isinstance(area_tecnologia, dict) else "Sem área"
    inicio_raw = issue["fields"].get("customfield_10065")
    fim_raw = issue["fields"].get("customfield_10067")
    inicio_fmt = parse(inicio_raw).strftime("%d/%m/%Y %H:%M") if inicio_raw else "Sem data"
    fim_fmt = parse(fim_raw).strftime("%d/%m/%Y %H:%M") if fim_raw else "Sem data"


    return (
        f"{key}\n"
        f"Tipo: {tipo_valor}\n"
        f"Status: {status}\n"
        f"Área de Tecnologia: {area_tecnologia_val}\n"
        f"Resumo: {summary}\n"
        f"Motivo: {motivo_valor}\n"
        f"Unidade executora: {unidade_pai} / {unidade_filho}\n"
        f"Responsável: {responsavel}\n"
        f"Início: {inicio_fmt}\n"
        f"Fim: {fim_fmt}\n"
    )

# CORES
def cor_status(nome):
    nome = nome.lower()
    if "aprovação" in nome:
        return "status-aprovacao"
    elif "aguardando" in nome:
        return "status-aguardando"
    elif "execução" in nome:
        return "status-emexecucao"
    elif "resolvido" in nome:
        return "status-resolvido"
    elif "avaliação" in nome:
        return "status-avaliacao"
    elif "concluído" in nome or "concluido" in nome:
        return "status-concluido"
    else:
        return "status-outros"

def gerar_jql_link(data):
    data_str = data.strftime("%Y-%m-%d")
    jql_dia = f'project=10323 AND "Data e hora de início da execução" >= "{data_str}" AND "Data e hora de início da execução" < "{(data + timedelta(days=1)).strftime("%Y-%m-%d")}"'
    return f"https://{JIRA_DOMAIN}/issues/?jql={quote(jql_dia)}"

def gerar_jql_link_mes(ano, mes):
    inicio = datetime(ano, mes, 1).date()
    ultimo = datetime(ano, mes, monthrange(ano, mes)[1]).date()
    jql = f'project=10323 AND "Data e hora de início da execução" >= "{inicio}" AND "Data e hora de início da execução" <= "{ultimo}"'
    return f"https://{JIRA_DOMAIN}/issues/?jql={quote(jql)}"

# Preparar totais por mês (contando cada issue uma única vez no mês, mesmo que tenha múltiplos dias)
totais_por_mes = []
for m in range(1, 13):
    dias_do_mes = [datetime(ano, m, d).date() for d in range(1, monthrange(ano, m)[1] + 1)]
    issues_unicos = set()
    for d in dias_do_mes:
        for issue in mudancas_por_data.get(d, []):
            issues_unicos.add(issue["key"])
    totais_por_mes.append(len(issues_unicos))

# HTML INICIAL
html = f"""<html><head><meta charset="utf-8">
<title>Calendário de Mudanças</title>
<style>
body {{
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
    background-color: #f9fafb;
    margin: 0;
    padding: 0 16px 40px 16px;
}}
.titulo-principal {{
    font-weight: 700;
    font-size: 28px;
    color: #111827;
    margin-top: 10px;
    margin-bottom: 8px;
    text-align: center;
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
    justify-content: space-between;
    align-items: center;
    margin: 24px 0 12px 0;
    color: #1f2937;
    max-width: 860px;
    margin-left: 200px;
}}
.mes-header h2 {{
    font-size: 20px;
    font-weight: 600;
    margin: 0;
    text-align: left;
}}
.atualizacao {{
    font-size: 12px;
    color: #6b7280;
    margin: 0;
}}
.legenda-status {{
    position: fixed;
    top: 80px;
    left: 16px;
    width: 160px;
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
/* Gráfico com barra horizontal e mesma largura da legenda */
#grafico-sazonalidade-container {{
    position: fixed;
    top: 270px;
    left: 16px;
    width: 200px;
    background: rgba(255, 255, 255, 0.95);
    padding: 10px 12px;
    border-radius: 10px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    font-size: 12px;
    color: #1f2937;
    z-index: 1000;
    max-width: 160px;
    line-height: 1.5;
    overflow-y: auto;
    max-height: 400px;
}}
.barra-horizontal {{
    display: flex;
    flex-direction: column;
    gap: 6px;
}}
.barra-horizontal .linha {{
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
}}
.barra-horizontal .barra {{
    height: 14px;
    background-color: #a3a3a3;
    border-radius: 6px;
    transition: background-color 0.3s;
    flex-grow: 1;
    max-width: 140px;
    position: relative;
}}
.barra-horizontal .barra .preenchimento {{
    height: 100%;
    background-color: #2563eb;
    border-radius: 6px 0 0 6px;
    transition: width 0.3s;
}}
.barra-horizontal .barra.mes-ativo .preenchimento {{
    background-color: #1e40af;
}}
.barra-horizontal .label-mes {{
    width: 60px;
    text-align: left;
    font-weight: 600;
    user-select: none;
}}
.barra-horizontal .total-mes {{
    width: 40px;
    text-align: right;
    font-size: 12px;
    color: #374151;
    user-select: none;
}}
.titulo-principal {{
    font-weight: 700;
    font-size: 28px;
    color: #111827;
    margin-top: 20px;
    margin-bottom: 8px;
    text-align: center;
}}
body {{
    padding-top: 40px;
}}
</style>
</head><body>

<h1 class="titulo-principal">Calendário de Mudanças</h1>

<div class='legenda-status'>
    <strong>Status das Mudanças</strong><br>
    <span class='item-bar status-aprovacao'></span> Em aprovação<br>
    <span class='item-bar status-aguardando'></span> Aguardando execução<br>
    <span class='item-bar status-emexecucao'></span> Em execução<br>
    <span class='item-bar status-resolvido'></span> Resolvido<br>
    <span class='item-bar status-avaliacao'></span> Em avaliação<br>
    <span class='item-bar status-concluido'></span> Concluído<br>
    <span class='item-bar status-outros'></span> Outros status
</div>

<div id="grafico-sazonalidade-container">
  <strong>Total de Mudanças por Mês</strong>
  <div class="barra-horizontal" id="grafico-sazonalidade">
  </div>
</div>
"""

cal = Calendar(firstweekday=0)

# GERAR CALENDÁRIOS DE TODOS OS MESES DO ANO COM IDs para controle de scroll
for mes in range(1, 13):
    nome_mes = meses_pt[mes]
    dias_do_mes = [datetime(ano, mes, d).date() for d in range(1, monthrange(ano, mes)[1] + 1)]
    issues_unicos_mes = set()
    for d in dias_do_mes:
        for issue in mudancas_por_data.get(d, []):
            issues_unicos_mes.add(issue["key"])
    total_mes = len(issues_unicos_mes)
    link_mes = gerar_jql_link_mes(ano, mes)

    html += f"""
    <div id='mes-{mes}' class='mes-header'>
        <h2><strong>{nome_mes}</strong></h2>
        <div class='atualizacao'>Última atualização: {hoje.strftime("%d/%m/%Y %H:%M:%S")} |
        Total de mudanças no mês: <a href="{link_mes}" target="_blank">{total_mes}</a></div>
    </div>
    <table><tr>
    <th>Seg</th><th>Ter</th><th>Qua</th><th>Qui</th><th>Sex</th><th>Sáb</th><th>Dom</th>
    </tr>
    """

    for semana in cal.monthdayscalendar(ano, mes):
        html += "<tr>"
        for dia in semana:
            if dia == 0:
                html += "<td></td>"
            else:
                data_atual = datetime(ano, mes, dia).date()
                itens = mudancas_por_data.get(data_atual, [])
                html += f"<td><div class='data-dia'>{dia}</div><div class='item-container'>"
                for item in itens:
                    key = item["key"]
                    status_nome = item["fields"].get("status", {}).get("name", "")
                    cor = cor_status(status_nome)
                    link = f"https://{JIRA_DOMAIN}/browse/{key}"
                    tooltip = escape(gerar_tooltip(item))
                    html += f"<a href='{link}' target='_blank' title=\"{tooltip}\"><div class='item-bar {cor}'></div></a>"
                html += "</div>"
                if itens:
                    jql_link = gerar_jql_link(data_atual)
                    html += f"<div class='contador'><a href='{jql_link}' target='_blank'>Total: {len(itens)}</a></div>"
                html += "</td>"
        html += "</tr>\n"
    html += "</table>"

# RODAPÉ
html += """
<div style="text-align: center; font-size: 12px; color: #718096; margin-top: 24px; padding-bottom: 16px;">
    Calendário mantido pela Gerência de Gestão de Mudanças e Implantações da Secretaria de Tecnologia e Inovação - GMUDI/STI.
</div>

""".format(hoje.strftime("%d/%m/%Y %H:%M:%S"))


# SCRIPT para gráfico de barras horizontal
html += """
<script>
const totais = """ + str(totais_por_mes) + """;
const meses = """ + str([meses_pt[m] for m in range(1,13)]) + """;

const container = document.getElementById("grafico-sazonalidade");

const maxTotal = Math.max(...totais);
for(let i=0; i<totais.length; i++){
    const linha = document.createElement("div");
    linha.classList.add("linha");
    linha.title = meses[i] + ": " + totais[i] + " mudanças";

    const labelMes = document.createElement("div");
    labelMes.classList.add("label-mes");
    labelMes.textContent = meses[i];
    linha.appendChild(labelMes);

    const barra = document.createElement("div");
    barra.classList.add("barra");
    if(i === new Date().getMonth()){
        barra.classList.add("mes-ativo");
    }

    const preenchimento = document.createElement("div");
    preenchimento.classList.add("preenchimento");
    let larguraPct = maxTotal > 0 ? (totais[i] / maxTotal) * 100 : 0;
    preenchimento.style.width = larguraPct + "%";
    barra.appendChild(preenchimento);

    linha.appendChild(barra);

    const totalDiv = document.createElement("div");
    totalDiv.classList.add("total-mes");
    totalDiv.textContent = totais[i];
    linha.appendChild(totalDiv);

    container.appendChild(linha);
}
</script>
"""

html += "</body></html>"

# SALVAR
caminho_html = r"index.html"
with open(caminho_html, "w", encoding="utf-8") as f:
    f.write(html)

print("✅ Calendário atualizado.")
