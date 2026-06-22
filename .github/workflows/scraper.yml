#!/usr/bin/env python3
# =====================================================================
# FASE 2 — Scraper de multas de tránsito
#
# Flujo:
#   1. Lee las patentes desde Supabase (tabla `vehiculos`).
#   2. Consulta cada patente en el sitio de multas con Playwright (headless).
#   3. Hace UPSERT de los resultados en la tabla `multas`.
#   4. Espera un tiempo aleatorio entre consultas (anti-bloqueo).
#
# Modo DEMO:
#   El sitio `https://ejemplo-multas.gov.ar/consulta` no existe.
#   Con DEMO_MODE=true el script genera multas ficticias pero realistas,
#   así podés probar TODO el pipeline (Supabase -> scraper -> Supabase ->
#   Streamlit) antes de enchufar el sitio real. Cuando tengas el sitio
#   real, poné DEMO_MODE=false y completá `consultar_patente_real()`.
# =====================================================================

import os
import sys
import time
import random
import logging
from datetime import date, timedelta

from supabase import create_client, Client
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# --------------------------- Configuración ---------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("scraper-multas")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")          # service_role (bypassa RLS)
CONSULTA_URL = os.environ.get("CONSULTA_URL", "https://ejemplo-multas.gov.ar/consulta")

DEMO_MODE = os.environ.get("DEMO_MODE", "true").lower() == "true"

# Rango de espera aleatoria entre consultas, en segundos.
MIN_DELAY = float(os.environ.get("MIN_DELAY", "3"))
MAX_DELAY = float(os.environ.get("MAX_DELAY", "8"))

# Pool de User-Agents para rotar y parecer tráfico humano.
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


# --------------------------- Supabase --------------------------------
def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        log.error("Faltan SUPABASE_URL o SUPABASE_KEY en el entorno.")
        sys.exit(1)
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def obtener_vehiculos(sb: Client) -> list[dict]:
    resp = sb.table("mlt_vehiculos").select("id, patente").execute()
    vehiculos = resp.data or []
    log.info("Se obtuvieron %d vehículos para consultar.", len(vehiculos))
    return vehiculos


def guardar_multas(sb: Client, vehiculo_id: int, multas: list[dict]) -> int:
    """UPSERT por `acta` (UNIQUE). Inserta nuevas, actualiza existentes."""
    guardadas = 0
    for m in multas:
        registro = {
            "vehiculo_id": vehiculo_id,
            "acta": m["acta"],
            "monto": m["monto"],
            "fecha_infraccion": m["fecha_infraccion"],
            "estado": m.get("estado", "pendiente"),
        }
        sb.table("mlt_multas").upsert(registro, on_conflict="acta").execute()
        guardadas += 1
    return guardadas


# ------------------------ Scraping (REAL) ----------------------------
def consultar_patente_real(page, patente: str) -> list[dict]:
    """
    Consulta REAL en el sitio de multas.

    >>> ADAPTAR LOS SELECTORES a la página objetivo. <<<
    Cada jurisdicción argentina (CABA, provincia de Bs As, infracciones
    nacionales, municipios) tiene su propio formulario; este es el
    esqueleto genérico que vas a ajustar.
    """
    multas: list[dict] = []
    try:
        page.goto(CONSULTA_URL, wait_until="domcontentloaded", timeout=30000)

        # 1) Completar el campo de patente  (TODO: ajustar selector)
        page.fill("input[name='patente']", patente)

        # 2) Enviar el formulario            (TODO: ajustar selector)
        page.click("button[type='submit']")

        # 3) Esperar la tabla de resultados  (TODO: ajustar selector)
        page.wait_for_selector("table.resultados tbody tr", timeout=15000)

        # 4) Parsear las filas
        filas = page.query_selector_all("table.resultados tbody tr")
        for fila in filas:
            celdas = fila.query_selector_all("td")
            if len(celdas) < 4:
                continue
            acta  = celdas[0].inner_text().strip()
            fecha = celdas[1].inner_text().strip()           # 'YYYY-MM-DD'
            monto = celdas[2].inner_text().strip()           # '12345.67'
            estado = celdas[3].inner_text().strip().lower()  # 'pendiente'/'pagada'/...

            multas.append({
                "acta": acta,
                "fecha_infraccion": fecha or None,
                "monto": float(monto.replace("$", "").replace(".", "").replace(",", ".") or 0),
                "estado": estado if estado in
                          {"pendiente", "pagada", "en_gestion", "prescripta", "no_aplica"}
                          else "pendiente",
            })

    except PlaywrightTimeout:
        # Sin tabla de resultados normalmente significa "sin multas".
        log.info("  [%s] sin resultados (timeout esperando tabla).", patente)
    except Exception as e:  # noqa: BLE001
        log.warning("  [%s] error durante el scraping: %s", patente, e)

    return multas


# ------------------------ Scraping (DEMO) ----------------------------
def consultar_patente_demo(patente: str) -> list[dict]:
    """Genera multas ficticias deterministas por patente (re-ejecutable)."""
    rnd = random.Random(patente)            # misma patente -> mismas multas
    cantidad = rnd.choice([0, 0, 1, 1, 2, 3])
    multas = []
    estados = ["pendiente", "pendiente", "pendiente", "pagada", "en_gestion"]
    for i in range(cantidad):
        f = date.today() - timedelta(days=rnd.randint(10, 400))
        multas.append({
            "acta": f"{patente}-{f.year}-{1000 + i}",
            "fecha_infraccion": f.isoformat(),
            "monto": round(rnd.uniform(25_000, 380_000), 2),
            "estado": rnd.choice(estados),
        })
    return multas


# ------------------------ Browser / stealth --------------------------
def nuevo_contexto(browser):
    ctx = browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={"width": 1366, "height": 768},
        locale="es-AR",
        timezone_id="America/Argentina/Buenos_Aires",
    )
    # Ocultar la huella de automatización más obvia.
    ctx.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    )
    return ctx


# ------------------------------ Main ---------------------------------
def main() -> None:
    sb = get_supabase()
    vehiculos = obtener_vehiculos(sb)
    if not vehiculos:
        log.warning("No hay vehículos cargados. Nada que hacer.")
        return

    total_multas = 0

    if DEMO_MODE:
        log.info(">>> DEMO_MODE activo: generando multas ficticias (sin navegador).")
        for v in vehiculos:
            multas = consultar_patente_demo(v["patente"])
            n = guardar_multas(sb, v["id"], multas)
            total_multas += n
            log.info("  [%s] %d multa(s) guardada(s).", v["patente"], n)
        log.info("Listo. Total de multas procesadas: %d", total_multas)
        return

    # ---- Modo real con Playwright ----
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = nuevo_contexto(browser)
        page = ctx.new_page()

        for v in vehiculos:
            patente = v["patente"]
            log.info("Consultando patente %s ...", patente)
            multas = consultar_patente_real(page, patente)
            n = guardar_multas(sb, v["id"], multas)
            total_multas += n
            log.info("  [%s] %d multa(s) guardada(s).", patente, n)

            # Espera aleatoria anti-bloqueo entre consultas.
            espera = random.uniform(MIN_DELAY, MAX_DELAY)
            log.info("  Esperando %.1f s antes de la próxima...", espera)
            time.sleep(espera)

        ctx.close()
        browser.close()

    log.info("Listo. Total de multas procesadas: %d", total_multas)


if __name__ == "__main__":
    main()
