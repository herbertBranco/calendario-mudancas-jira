# main.py

html_content = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Calendário de Mudanças</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            padding: 40px;
            background-color: #f9f9f9;
        }
        h1 {
            color: #333;
        }
        p {
            font-size: 18px;
        }
    </style>
</head>
<body>
    <h1>Calendário de Mudanças</h1>
    <p>Esta página foi gerada automaticamente por Python e publicada via GitHub Pages.</p>
</body>
</html>
"""

# Salvar na pasta correta
with open("public/index.html", "w", encoding="utf-8") as f:
    f.write(html_content)
