#!/usr/bin/env python3
# =====================================================================
# FASE 4 — Panel visual (Streamlit)
#
#   1. Se conecta a Supabase (anon key, solo lectura) y muestra el
#      estado de los vehículos con sus multas.
#   2. Muestra métricas clave (monto total adeudado, etc.).
#   3. Botón "Actualizar datos ahora" que dispara el workflow de
#      GitHub Actions vía POST a la API REST de GitHub.
#
# Configuración de secrets (.streamlit/secrets.toml o Streamlit Cloud):
#
#   SUPABASE_URL      = "https://xxxx.supabase.co"
#   SUPABASE_ANON_KEY = "eyJhbGci...."          # anon key (NO la service_role)
#   GITHUB_TOKEN      = "github_pat_...."        # PAT con permiso "Actions: write"
#   GITHUB_REPO       = "tu-usuario/flota-multas"
#   WORKFLOW_FILE     = "scraper.yml"
#   GITHUB_REF        = "main"
# =====================================================================

import requests
import pandas as pd
import streamlit as st
from supabase import create_client

st.set_page_config(page_title="Multas de la Flota", page_icon="🚦", layout="wide")

# --------------------------- Conexiones ------------------------------
@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])


@st.cache_data(ttl=60)
def cargar_datos() -> pd.DataFrame:
    """Trae multas + datos del vehículo usando la relación FK (join embebido)."""
    sb = get_supabase()
    resp = (
        sb.table("mlt_multas")
        .select("acta, monto, fecha_infraccion, estado, mlt_vehiculos(patente, marca, modelo)")
        .execute()
    )
    filas = []
    for m in resp.data or []:
        v = m.get("mlt_vehiculos") or {}
        filas.append({
            "Patente": v.get("patente"),
            "Marca": v.get("marca"),
            "Modelo": v.get("modelo"),
            "Acta": m.get("acta"),
            "Fecha": m.get("fecha_infraccion"),
            "Monto": float(m.get("monto") or 0),
            "Estado": m.get("estado"),
        })
    return pd.DataFrame(filas)


@st.cache_data(ttl=60)
def cargar_vehiculos() -> pd.DataFrame:
    sb = get_supabase()
    resp = sb.table("mlt_vehiculos").select("patente, marca, modelo").execute()
    return pd.DataFrame(resp.data or [])


def disparar_workflow() -> tuple[bool, str]:
    """POST a la API de GitHub para ejecutar el workflow on-demand."""
    repo = st.secrets["GITHUB_REPO"]
    wf   = st.secrets.get("WORKFLOW_FILE", "scraper.yml")
    ref  = st.secrets.get("GITHUB_REF", "main")
    url  = f"https://api.github.com/repos/{repo}/actions/workflows/{wf}/dispatches"
    headers = {
        "Authorization": f"Bearer {st.secrets['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    r = requests.post(url, headers=headers, json={"ref": ref}, timeout=20)
    if r.status_code == 204:
        return True, "Workflow disparado. Los datos se actualizarán en unos minutos."
    return False, f"Error {r.status_code}: {r.text}"


# ------------------------------ UI -----------------------------------
st.title("🚦 Control de multas de la flota")

col_btn, col_info = st.columns([1, 3])
with col_btn:
    if st.button("🔄 Actualizar datos ahora", use_container_width=True):
        ok, msg = disparar_workflow()
        (st.success if ok else st.error)(msg)
        st.cache_data.clear()
with col_info:
    st.caption("El botón ejecuta el scraper en GitHub Actions. "
               "Refrescá la página en 1-2 minutos para ver los datos nuevos.")

df = cargar_datos()
df_vehiculos = cargar_vehiculos()

# --------- Métricas clave ---------
pendientes = df[df["Estado"] == "pendiente"] if not df.empty else df
total_adeudado = pendientes["Monto"].sum() if not df.empty else 0
veh_con_deuda = pendientes["Patente"].nunique() if not df.empty else 0
total_vehiculos = len(df_vehiculos)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Vehículos en la flota", total_vehiculos)
c2.metric("Vehículos con deuda", veh_con_deuda)
c3.metric("Multas pendientes", len(pendientes))
c4.metric("Monto total adeudado", f"$ {total_adeudado:,.0f}")

st.divider()

# --------- Filtros ---------
if not df.empty:
    estados = ["(todos)"] + sorted(df["Estado"].dropna().unique().tolist())
    f1, f2 = st.columns(2)
    estado_sel = f1.selectbox("Filtrar por estado", estados)
    patente_sel = f2.text_input("Filtrar por patente").strip().upper()

    vista = df.copy()
    if estado_sel != "(todos)":
        vista = vista[vista["Estado"] == estado_sel]
    if patente_sel:
        vista = vista[vista["Patente"].str.contains(patente_sel, na=False)]

    st.subheader(f"Detalle de multas ({len(vista)} registros)")
    st.dataframe(
        vista.sort_values(["Estado", "Patente"]),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Monto": st.column_config.NumberColumn("Monto", format="$ %.2f"),
        },
    )

    # --------- Resumen por vehículo ---------
    st.subheader("Resumen por vehículo (solo pendientes)")
    if not pendientes.empty:
        resumen = (
            pendientes.groupby(["Patente", "Marca", "Modelo"])
            .agg(Multas=("Acta", "count"), Adeudado=("Monto", "sum"))
            .reset_index()
            .sort_values("Adeudado", ascending=False)
        )
        st.dataframe(
            resumen, use_container_width=True, hide_index=True,
            column_config={"Adeudado": st.column_config.NumberColumn("Adeudado", format="$ %.2f")},
        )
    else:
        st.info("No hay multas pendientes. 🎉")
else:
    st.info("Todavía no hay multas cargadas. Ejecutá el scraper con el botón de arriba.")
