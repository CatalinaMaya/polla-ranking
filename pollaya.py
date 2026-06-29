"""
Web scraper + ranking para https://game.pollaya.com/mis-grupos/120344/posiciones
Requiere: pip install playwright && playwright install chromium
"""

import json
import os
import webbrowser
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────
EMAIL    = os.environ.get("POLLAYA_EMAIL", "tu@correo.com")
PASSWORD = os.environ.get("POLLAYA_PASSWORD", "tu_contraseña")
GROUP_URL = "https://game.pollaya.com/mis-grupos/120344/posiciones"
SESSION_FILE = "pollaya_session.json"

# Puntajes fijos de 1era ronda (nombre exacto en Pollaya → puntaje)
PRIMERA_RONDA = {
    "Marcela Maya Iregui":               299,
    "Yenifer Avendaño Montoya":          296,
    "Carlos Hernan cadavid gonzalez":    294,
    "Catalina Maya Iregui":              287,
    "Alejandro Morales":                 284,
    "Leopaispaisa":                      280,
    "LUIS FERNANDO BUSTAMANTE MONSALVE": 272,
    "Soraya Iregui lotero":              265,
    "Hernando Maya":                     234,
}
# ──────────────────────────────────────────────────────────────────────────────


def login(page, context):
    print("🔐 Iniciando sesión...")
    page.goto(GROUP_URL, wait_until="domcontentloaded", timeout=60000)


    print("📧 Ingresando email...")
    page.wait_for_selector("div.new-login input", timeout=10000)
    page.locator("div.new-login input").first.fill(EMAIL)

    print("➡️  Clic en Siguiente...")
    page.locator("div.new-login button:has-text('Siguiente')").click()
    page.wait_for_timeout(2000)

    print("🔑 Ingresando contraseña...")
    page.locator("input[type='password']").fill(PASSWORD)
    page.locator("button[type='submit'], button:has-text('Entrar'), button:has-text('Iniciar sesión')").first.click()
    page.wait_for_timeout(4000)

    print(f"✅ Login completado. URL: {page.url}")
    context.storage_state(path=SESSION_FILE)
    print(f"💾 Sesión guardada en {SESSION_FILE}")


def scrape_puntajes(page) -> dict:
    """Devuelve {nombre: puntaje_actual} desde Pollaya."""
    print(f"\n🌐 Navegando a {GROUP_URL}")
    page.goto(GROUP_URL, wait_until="networkidle")
    page.wait_for_timeout(3000)

    if "login" in page.url or "auth" in page.url:
        print("❌ Sesión inválida. Borra pollaya_session.json y reintenta.")
        return {}

    # Guardar HTML para inspección si hace falta
    html = page.content()
    with open("posiciones_raw.html", "w", encoding="utf-8") as f:
        f.write(html)

    puntajes = {}

    # La página usa una lista, no una tabla.
    # Cada ítem tiene: posición, avatar (letra), nombre, puntaje
    # Intentamos varios selectores comunes de Angular rankings
    selectores = [
        "[class*='item']",
        "[class*='row']",
        "[class*='posicion']",
        "[class*='ranking']",
        "[class*='position']",
        "li",
    ]

    items = []
    for sel in selectores:
        items = page.query_selector_all(sel)
        if items:
            print(f"📊 Selector '{sel}' encontró {len(items)} elementos")
            break

    nombres_validos = set(PRIMERA_RONDA.keys())

    for item in items:
        texto = item.inner_text().strip()
        lineas = [l.strip() for l in texto.splitlines() if l.strip()]
        # Buscar si alguna línea es un nombre conocido
        for i, linea in enumerate(lineas):
            if linea in nombres_validos:
                # El puntaje suele estar en la siguiente línea numérica
                for j in range(i + 1, len(lineas)):
                    try:
                        puntaje = int(lineas[j].replace(".", "").replace(",", ""))
                        puntajes[linea] = puntaje
                        print(f"   ✓ {linea}: {puntaje}")
                        break
                    except ValueError:
                        continue
                break

    if not puntajes:
        print("⚠️  No se pudieron extraer puntajes con selectores.")
        print("   Intentando extracción por texto completo de la página...")
        import re
        texto_pagina = page.inner_text("body")
        for nombre in nombres_validos:
            # Buscar el nombre seguido de un número en el texto
            patron = re.escape(nombre) + r"[\s\S]{0,30}?(\d{3,4})"
            match = re.search(patron, texto_pagina)
            if match:
                puntajes[nombre] = int(match.group(1))
                print(f"   ✓ {nombre}: {puntajes[nombre]}")

    print(f"✅ Puntajes extraídos: {len(puntajes)} participantes")
    return puntajes


def calcular_ranking(puntajes_actuales: dict) -> list:
    """Cruza con 1era ronda y calcula Real = Actual - 1era ronda."""
    ranking = []
    for nombre, primera in PRIMERA_RONDA.items():
        actual = puntajes_actuales.get(nombre)
        if actual is None:
            print(f"⚠️  '{nombre}' no encontrado en Pollaya. Usando puntaje manual si existe.")
            actual = primera  # fallback: real = 0
        real = actual - primera
        ranking.append({"nombre": nombre, "actual": actual, "primera": primera, "real": real})

    ranking.sort(key=lambda x: x["real"], reverse=True)
    for i, p in enumerate(ranking):
        if i == 0 or p["real"] != ranking[i - 1]["real"]:
            p["pos"] = i + 1
        else:
            p["pos"] = ranking[i - 1]["pos"]

def generar_html(ranking: list, output="ranking.html"):
    medallas = {1: "🥇", 2: "🥈", 3: "🥉"}

    # Tabla 1: puntajes ordenados por nombre original
    filas_puntajes = ""
    for p in sorted(ranking, key=lambda x: list(PRIMERA_RONDA.keys()).index(x["nombre"])):
        filas_puntajes += f"""
        <tr>
            <td class=\"nombre\">{p['nombre']}</td>
            <td class=\"num\">{p['primera']}</td>
            <td class=\"num actual\">{p['actual']}</td>
            <td class=\"num real\">{p['real']:+}</td>
        </tr>"""

    # Tabla 2: ranking por puntaje real
    filas_ranking = ""
    for p in ranking:
        medalla = medallas.get(p["pos"], f"#{p['pos']}")
        top3_class = "top3" if p["pos"] <= 3 else ""
        filas_ranking += f"""
        <tr class=\"{top3_class}\">
            <td class=\"pos\">{medalla}</td>
            <td class=\"nombre\">{p['nombre']}</td>
            <td class=\"num real\">{p['real']:+}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang=\"es\">
<head>
<meta charset=\"UTF-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
<title>Ranking Pollaya — 2da Ronda</title>
<link href=\"https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;500;600;700&display=swap\" rel=\"stylesheet\">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0d1117; color: #e6edf3;
    font-family: 'Inter', sans-serif;
    min-height: 100vh; display: flex; flex-direction: column;
    align-items: center; padding: 40px 16px 60px; gap: 48px;
  }}
  header {{ text-align: center; }}
  .badge {{
    display: inline-block; background: #238636; color: #fff;
    font-size: 11px; font-weight: 600; letter-spacing: 1.5px;
    text-transform: uppercase; padding: 4px 12px; border-radius: 20px; margin-bottom: 12px;
  }}
  h1 {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: clamp(42px, 8vw, 72px); letter-spacing: 2px; line-height: 1;
    background: linear-gradient(135deg, #58a6ff 0%, #bc8cff 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  }}
  .subtitle {{ margin-top: 8px; font-size: 13px; color: #8b949e; }}
  section {{ width: 100%; max-width: 760px; }}
  .section-title {{
    font-family: 'Bebas Neue', sans-serif; font-size: 22px; letter-spacing: 1.5px;
    color: #8b949e; margin-bottom: 12px; border-left: 3px solid #58a6ff; padding-left: 10px;
  }}
  .card {{
    background: #161b22; border: 1px solid #30363d;
    border-radius: 12px; overflow: hidden;
  }}
  table {{ width: 100%; border-collapse: collapse; }}
  thead th {{
    background: #1c2128; font-size: 10px; font-weight: 600;
    letter-spacing: 1.2px; text-transform: uppercase; color: #8b949e;
    padding: 12px 18px; text-align: left;
  }}
  thead th.num {{ text-align: right; }}
  tbody tr {{ border-top: 1px solid #21262d; transition: background 0.15s; }}
  tbody tr:hover {{ background: #1c2128; }}
  tbody tr.top3 {{ background: #0d1f0f; }}
  tbody tr.top3:hover {{ background: #112613; }}
  td {{ padding: 14px 18px; font-size: 14px; }}
  td.pos {{ font-size: 18px; width: 52px; text-align: center; }}
  td.nombre {{ font-weight: 500; color: #c9d1d9; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; color: #8b949e; }}
  td.actual {{ color: #58a6ff; font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; }}
  td.real {{ font-weight: 700; font-size: 15px; color: #3fb950; text-align: right; font-variant-numeric: tabular-nums; }}
  .footer {{ font-size: 11px; color: #484f58; }}
</style>
</head>
<body>
  <header>
    <div class=\"badge\">⚽ Pollaya 2026</div>
    <h1>POLLA<br>2DA RONDA</h1>
    <p class=\"subtitle\">Real = Puntaje actual − 1ª ronda</p>
  </header>

  <section>
    <div class=\"section-title\">PUNTAJES</div>
    <div class=\"card\">
      <table>
        <thead>
          <tr>
            <th>Participante</th>
            <th class=\"num\">1ª Ronda</th>
            <th class=\"num\">Actual</th>
            <th class=\"num\">Real</th>
          </tr>
        </thead>
        <tbody>{filas_puntajes}</tbody>
      </table>
    </div>
  </section>

  <section>
    <div class=\"section-title\">RANKING 2DA RONDA</div>
    <div class=\"card\">
      <table>
        <thead>
          <tr>
            <th></th>
            <th>Participante</th>
            <th class=\"num\">Puntaje Real</th>
          </tr>
        </thead>
        <tbody>{filas_ranking}</tbody>
      </table>
    </div>
  </section>

  <p class=\"footer\">Actualizado automáticamente desde Pollaya</p>
</body>
</html>"""

    with open(output, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"🌐 Página generada: {output}")
    return output

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        if os.path.exists(SESSION_FILE):
            print(f"♻️  Reutilizando sesión desde {SESSION_FILE}")
            context = browser.new_context(storage_state=SESSION_FILE)
        else:
            context = browser.new_context()

        page = context.new_page()

        if not os.path.exists(SESSION_FILE):
            login(page, context)

        puntajes = scrape_puntajes(page)
        browser.close()

    ranking = calcular_ranking(puntajes)

    print("\n--- RANKING ---")
    for p in ranking:
        print(f"  #{p['pos']} {p['nombre']}: Real={p['real']:+} (Actual={p['actual']}, 1ra={p['primera']})")

    html_file = generar_html(ranking)
    webbrowser.open(f"file:///{os.path.abspath(html_file)}")


if __name__ == "__main__":
    main()
