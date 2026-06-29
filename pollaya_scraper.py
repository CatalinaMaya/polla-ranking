"""
Web scraper para https://game.pollaya.com/mis-grupos/120344/posiciones
Requiere: pip install playwright && playwright install chromium
"""

import json
import csv
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────
EMAIL    = "cmayairegui@gmail.com"       # <-- cambia esto
PASSWORD = "ca230600ta"       # <-- cambia esto
GROUP_URL = "https://game.pollaya.com/mis-grupos/120344/posiciones"
SESSION_FILE = "pollaya_session.json"   # guarda la sesión para no re-loguearse
# ──────────────────────────────────────────────────────────────────────────────


def login(page, context):
    print("🔐 Iniciando sesión...")
    page.goto("https://game.pollaya.com", wait_until="networkidle")
    page.wait_for_timeout(3000)
 
    # Paso 1: ingresar email en el formulario visible en la home
    print("📧 Esperando campo de email...")
    page.wait_for_selector("div.new-login input", timeout=10000)
    page.locator("div.new-login input").first.fill(EMAIL)
    page.screenshot(path="paso1_email.png", full_page=True)
 
    # Clic en "Siguiente"
    print("➡️  Clic en Siguiente...")
    page.locator("div.new-login button:has-text('Siguiente')").click()
    page.wait_for_timeout(2000)
    page.screenshot(path="paso2_password.png", full_page=True)
 
    # Paso 2: ingresar contraseña
    print("🔑 Ingresando contraseña...")
    inputs_paso2 = page.query_selector_all("input")
    print(f"   Inputs visibles ahora: {len(inputs_paso2)}")
    for i, inp in enumerate(inputs_paso2):
        print(f"   [{i}] type={inp.get_attribute('type')} placeholder={inp.get_attribute('placeholder')}")
 
    page.locator("input[type='password']").fill(PASSWORD)
 
    # Buscar botón de submit
    page.locator("button[type='submit'], button:has-text('Entrar'), button:has-text('Iniciar sesión')").first.click()
    page.wait_for_timeout(4000)
 
    page.screenshot(path="paso3_resultado.png", full_page=True)
    print(f"✅ Login completado. URL: {page.url}")
    context.storage_state(path=SESSION_FILE)
    print(f"💾 Sesión guardada en {SESSION_FILE}")
 
 
def scrape_posiciones(page) -> list:
    print(f"\n🌐 Navegando a {GROUP_URL}")
    page.goto(GROUP_URL, wait_until="networkidle")
    page.wait_for_timeout(3000)
 
    page.screenshot(path="posiciones_screenshot.png", full_page=True)
    print("📸 Captura guardada en posiciones_screenshot.png")
 
    if "login" in page.url or "auth" in page.url:
        print("❌ Redirigió al login — sesión inválida. Borra pollaya_session.json y reintenta.")
        return []
 
    rows = []
 
    table_rows = page.query_selector_all("table tr")
    if table_rows:
        print(f"📊 Tabla encontrada: {len(table_rows)} filas")
        for row in table_rows:
            cells = row.query_selector_all("td, th")
            if cells:
                rows.append([c.inner_text().strip() for c in cells])
    else:
        items = page.query_selector_all(
            "[class*='posicion'], [class*='ranking'], [class*='position'], "
            "[class*='standing'], [class*='player'], [class*='usuario'], "
            "[class*='participante']"
        )
        print(f"📊 Elementos alternativos: {len(items)}")
        for item in items:
            texto = item.inner_text().strip()
            if texto:
                rows.append([texto])
 
    if not rows:
        print("⚠️  Sin datos. Guardando HTML para inspección...")
        with open("posiciones_raw.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        print("💾 HTML guardado en posiciones_raw.html")
 
    return rows
 
 
def guardar_csv(rows, filename="posiciones.csv"):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    print(f"💾 CSV guardado: {filename} ({len(rows)} filas)")
 
 
def guardar_json(rows, filename="posiciones.json"):
    if len(rows) < 2:
        return
    headers = rows[0]
    data = [dict(zip(headers, row)) for row in rows[1:]]
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 JSON guardado: {filename} ({len(data)} registros)")
 
 
def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
 
        if os.path.exists(SESSION_FILE):
            print(f"♻️  Reutilizando sesión desde {SESSION_FILE}")
            context = browser.new_context(storage_state=SESSION_FILE)
        else:
            context = browser.new_context()
 
        page = context.new_page()
 
        if not os.path.exists(SESSION_FILE):
            login(page, context)
 
        rows = scrape_posiciones(page)
 
        if rows:
            print("\n--- PREVIEW ---")
            for row in rows[:5]:
                print(row)
            guardar_csv(rows)
            guardar_json(rows)
        else:
            print("❌ No se encontraron datos")
 
        input("\n⏸  Presiona ENTER para cerrar el navegador...")
        browser.close()
 
 
if __name__ == "__main__":
    main()