# 🚦 Control de multas de la flota

Sistema 100% gratuito para consultar y centralizar las multas de tránsito de
una flota de vehículos en Argentina.

**Stack:** Supabase (PostgreSQL) · Python + Playwright · GitHub Actions · Streamlit

```
flota-multas/
├── .github/workflows/scraper.yml   # Fase 3 — automatización
├── sql/01_schema.sql               # Fase 1 — base de datos
├── scraper/
│   ├── scraper.py                  # Fase 2 — extracción de datos
│   └── requirements.txt
├── app.py                          # Fase 4 — panel Streamlit
├── requirements.txt                # deps del panel (Streamlit Cloud)
├── .env.example
└── .streamlit/secrets.toml.example
```

---

## Fase 1 — Base de datos (Supabase)

1. Creá un proyecto en [supabase.com](https://supabase.com) (plan free).
2. Andá a **SQL Editor → New query**, pegá el contenido de
   `sql/01_schema.sql` y ejecutá (**RUN**).
3. Cargá tus 40 patentes reales en la tabla `vehiculos` (al final del SQL
   hay un `INSERT` de ejemplo que podés copiar y ampliar).

**Claves que vas a necesitar** (Settings → API):
- `Project URL` → será `SUPABASE_URL`.
- `anon public` key → la usa el **panel** (solo lectura).
- `service_role` key → la usa el **scraper** (escribe; bypassa RLS).
  ⚠️ La service_role es secreta: nunca la pongas en el frontend.

---

## Fase 2 — Scraper (Python + Playwright)

Probarlo localmente en **modo demo** (genera multas ficticias, no necesita
el sitio real):

```bash
cd scraper
pip install -r requirements.txt
playwright install chromium

export SUPABASE_URL="https://xxxx.supabase.co"
export SUPABASE_KEY="tu_service_role_key"
export DEMO_MODE=true
python scraper.py
```

Para usar el **sitio real**: poné `DEMO_MODE=false`, definí `CONSULTA_URL`
y completá los selectores en `consultar_patente_real()`
(buscá los `# TODO: ajustar selector`). Cada jurisdicción (CABA, Pcia. de
Bs As, infracciones nacionales, municipios) tiene su propio formulario, así
que probablemente necesites una función por sitio.

Buenas prácticas ya incluidas: espera aleatoria entre consultas, rotación de
User-Agent, locale/timezone de Argentina y ocultamiento de `navigator.webdriver`.

---

## Fase 3 — Automatización (GitHub Actions)

1. Subí el repo a GitHub.
2. En **Settings → Secrets and variables → Actions → New repository secret**,
   cargá:

   | Secret          | Valor                                   |
   |-----------------|-----------------------------------------|
   | `SUPABASE_URL`  | URL del proyecto Supabase               |
   | `SUPABASE_KEY`  | **service_role** key                    |
   | `CONSULTA_URL`  | URL del sitio de multas (si usás real)  |

   Y opcionalmente, en la pestaña **Variables**, `DEMO_MODE` = `true`/`false`.

3. El workflow corre solo **todos los días a las 02:00 ART** (= 05:00 UTC; el
   cron de GitHub siempre es UTC) y también se puede disparar manualmente desde
   **Actions → Scraper de Multas → Run workflow**, o por API (lo hace el panel).

---

## Fase 4 — Panel (Streamlit)

**Local:**

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # y completá los valores
streamlit run app.py
```

**Deploy gratis** en [share.streamlit.io](https://share.streamlit.io):
conectá el repo, apuntá a `app.py` y cargá los mismos valores en
**App settings → Secrets**.

Secrets del panel:

| Clave               | Para qué sirve                                         |
|---------------------|--------------------------------------------------------|
| `SUPABASE_URL`      | conexión a Supabase                                    |
| `SUPABASE_ANON_KEY` | **anon** key (solo lectura)                            |
| `GITHUB_TOKEN`      | PAT con permiso *Actions: write* (botón de actualizar) |
| `GITHUB_REPO`       | `tu-usuario/flota-multas`                              |
| `WORKFLOW_FILE`     | `scraper.yml`                                          |
| `GITHUB_REF`        | rama, normalmente `main`                               |

El **GITHUB_TOKEN**: creá un *Fine-grained PAT* en GitHub → Settings →
Developer settings, con acceso al repo y permiso **Actions: Read and write**.
El botón "Actualizar datos ahora" hace `POST .../workflows/scraper.yml/dispatches`
(respuesta `204` = OK).

---

## Notas de seguridad

- El panel usa la **anon key** con RLS que solo permite `SELECT`: nadie puede
  escribir/borrar desde el frontend.
- El scraper usa la **service_role**, que solo vive en los Secrets de GitHub.
- Si el panel va a ser público, considerá agregar login (Streamlit auth o un
  password simple) para no exponer los datos de la flota.
