import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime, date, timedelta

# ============ CONFIG VISUAL ============
pio.templates.default = "seaborn"
COLOR_PALETTE = px.colors.sequential.Greens

st.set_page_config(
    page_title="Dashboard VA",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { background-color: #ffffff; padding: 16px; }
    h1, h2, h3 { color: #2e7d32; }

    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #e8f5e9; }

    /* Animación global suave al cambiar de página */
    [data-testid="stAppViewContainer"] { animation: fadeIn 0.5s ease-in-out; }
    @keyframes fadeIn { from {opacity:0;} to {opacity:1;} }

    /* Botones Inicio: estilo como la imagen (borde verde + sombra suave) */
    .stButton>button {
        background-color: #ffffff !important;
        color: #2e7d32 !important;
        border: 2px solid #2e7d32 !important;
        border-radius: 999px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        width: 260px !important;
        box-shadow: 0 4px 10px rgba(46,125,50,0.20) !important;
        transition: all 0.2s ease-in-out !important;
    }
    .stButton>button:hover {
        background-color: #ffffff !important;
        color: #2e7d32 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 8px 16px rgba(46,125,50,0.30) !important;
    }
</style>
""", unsafe_allow_html=True)

# ============ DATOS ============
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQVxG-bO1D5mkgUFCU35drRV4tyXT9aRaW6q4zzWGa9nFAqkLVdZxaIjwD1cEMJIAXuI4xTBlhHS1og/pub?gid=991630809&single=true&output=csv"

@st.cache_data
def cargar_datos(url: str) -> pd.DataFrame:
    df = pd.read_csv(url, dtype=str)
    for c in ["analista", "supervisor", "equipo", "estado_carpeta", "profesional", "nivel"]:
        if c in df.columns:
            df[c] = df[c].fillna("").str.strip()
    return df

df = cargar_datos(CSV_URL)

# ============ UTILIDADES ============
START_DATE = date(2025, 9, 16)
ESTADOS_ORDEN = ["asignada", "devuelta", "calificada", "aprobada", "auditada"]
ESTADOS_RENOM = {
    "": "Por asignar",
    "asignada": "0. asignada",
    "devuelta": "1. devuelta",
    "calificada": "2. calificada",
    "aprobada": "3. aprobada",
    "auditada": "4. auditada"
}

def business_days_since_start(end_date: date) -> int:
    """Días hábiles (L-V) entre START_DATE y end_date (inclusive)."""
    if end_date < START_DATE:
        return 0
    rng = pd.bdate_range(START_DATE, end_date)
    return len(rng)

def meta_acumulada(modulo: str, df_mod: pd.DataFrame, today: date | None = None) -> tuple[int, int]:
    """
    Retorna la meta acumulada y el número de sujetos únicos del módulo.
    """
    if today is None:
        today = date.today()
    ayer = today - timedelta(days=1)
    dias_habiles = business_days_since_start(ayer)
    if dias_habiles <= 0:
        return 0, 0

    col = sujetos_col(modulo)
    if col not in df_mod.columns:
        return 0, 0

    sujetos_unicos = (
        df_mod[col]
        .astype(str)
        .str.strip()
        .str.lower()
        .replace("", pd.NA)
        .dropna()
        .unique()
    )

    n_sujetos = len(sujetos_unicos)
    if n_sujetos == 0:
        return 0, 0

    por_sujeto = 34 if modulo == "Supervisores" else 17
    meta = dias_habiles * por_sujeto * n_sujetos
    return meta, n_sujetos

def estados_validos(modulo: str) -> list[str]:
    if modulo == "Supervisores":
        return ["auditada", "aprobada"]
    # Analistas y Equipos
    return ["auditada", "aprobada", "calificada"]

def sujetos_col(modulo: str) -> str:
    return {"Analistas": "analista", "Supervisores": "supervisor", "Equipos": "equipo"}[modulo]

def prepara_df_modulo(df_in: pd.DataFrame, modulo: str) -> pd.DataFrame:
    dfm = df_in.copy()
    col = sujetos_col(modulo)
    if col not in dfm.columns:
        # Crear una columna vacía si no existe para evitar errores
        dfm[col] = ""
    return dfm

def desarrolladas_por_sujeto(df_mod: pd.DataFrame, modulo: str) -> pd.DataFrame:
    col = sujetos_col(modulo)
    validos = estados_validos(modulo)
    df_ok = df_mod[df_mod["estado_carpeta"].str.lower().isin(validos)]
    g = df_ok.groupby(col, dropna=False).size().reset_index(name="desarrolladas")
    return g

def clasifica_categoria(atraso: int, modulo: str) -> str:
    if modulo == "Supervisores":
        # rangos: <0 Al dia; 0-68 normal; 69-101 medio; >102 alto
        if atraso < 0:
            return "Al día"
        elif atraso <= 68:
            return "Atraso normal"
        elif atraso <= 101:
            return "Atraso medio"
        else:
            return "Atraso alto"
    else:
        # Analistas / Equipos: <0 Al día; 0-10 normal; 11-34 medio; >35 alto
        if atraso < 0:
            return "Al día"
        elif atraso <= 10:
            return "Atraso normal"
        elif atraso <= 34:
            return "Atraso medio"
        else:
            return "Atraso alto"

def grafico_estado_con_meta(df_mod: pd.DataFrame, modulo: str, total_meta: int):
    conteo = (
        df_mod["estado_carpeta"].fillna("").str.lower().map(ESTADOS_RENOM).value_counts()
        .reindex([ESTADOS_RENOM.get(e, e) for e in ["asignada", "devuelta", "calificada", "aprobada", "auditada"] + ["Por asignar"]], fill_value=0)
        .reset_index()
    )
    conteo.columns = ["estado_carpeta", "cantidad"]
    total = conteo["cantidad"].sum()
    conteo["porcentaje"] = (conteo["cantidad"] / total * 100).round(1)
    conteo["label"] = conteo["cantidad"].astype(str) + " (" + conteo["porcentaje"].astype(str) + "%)"

    fig = px.bar(
        conteo,
        x="estado_carpeta",
        y="cantidad",
        color="estado_carpeta",
        color_discrete_sequence=COLOR_PALETTE,
        text="label",
        title=f"Distribución por estado — Meta total a la fecha: {total_meta:,}".replace(",", "."),
    )
    fig.add_scatter(
        x=conteo["estado_carpeta"],
        y=[total_meta] * len(conteo),
        mode="lines+markers",
        name="Meta acumulada",
    )
    fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Cantidad")
    return fig

def grafico_categorias_barh(df_mod: pd.DataFrame, modulo: str, per_subject_meta: int):
    col = sujetos_col(modulo)
    # desarrolladas por sujeto
    dev = desarrolladas_por_sujeto(df_mod, modulo)
    if dev.empty:
        return px.bar(title="Sin datos para mostrar")
    # meta por sujeto (constante)
    dev["meta"] = per_subject_meta
    dev["atraso"] = dev["meta"] - dev["desarrolladas"]
    dev["categoria"] = dev["atraso"].apply(lambda x: clasifica_categoria(int(x), modulo))
    cat_count = dev.groupby("categoria").size().reset_index(name="cantidad")
    orden = ["Al día", "Atraso normal", "Atraso medio", "Atraso alto"]
    cat_count["categoria"] = pd.Categorical(cat_count["categoria"], categories=orden, ordered=True)
    cat_count = cat_count.sort_values("categoria")
    fig = px.bar(
        cat_count,
        x="cantidad",
        y="categoria",
        orientation="h",
        color="categoria",
        color_discrete_sequence=COLOR_PALETTE,
        title="Cantidad de sujetos por categoría de atraso",
        text_auto=True,
    )
    fig.update_layout(showlegend=False, xaxis_title="Cantidad de sujetos", yaxis_title="")
    return fig

def grafico_avance_total(total: int, avance: int):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = avance,
        title = {"text": "Avance total de carpetas"},
        gauge = {
            "axis": {"range": [0, total]},
            "bar": {"color": "green"},
            "steps" : [
                {"range": [0, total*0.5], "color": "#e0f2f1"},
                {"range": [total*0.5, total], "color": "#a5d6a7"}
            ],
        },
        domain={'x': [0, 1], 'y': [0, 1]}
    ))
    return fig

def tabla_resumen(df_mod: pd.DataFrame, modulo: str, per_subject_meta: int) -> pd.DataFrame:
    col = sujetos_col(modulo)
    dev = desarrolladas_por_sujeto(df_mod, modulo)
    if dev.empty:
        return pd.DataFrame(columns=["Categoria", col.capitalize(), "Desarrolladas", "Meta"])
    dev["meta"] = per_subject_meta
    dev["atraso"] = dev["meta"] - dev["desarrolladas"]
    dev["Categoria"] = dev["atraso"].apply(lambda x: clasifica_categoria(int(x), modulo))
    out = dev[[col, "desarrolladas", "meta", "Categoria"]].rename(
        columns={
            col: col.capitalize(),
            "desarrolladas": "Desarrolladas",
            "meta": "Meta",
        }
    )
    # Ordenar por prioridad de categoría
    orden = pd.Categorical(out["Categoria"], ["Al día", "Atraso normal", "Atraso medio", "Atraso alto"], ordered=True)
    out = out.assign(Categoria=orden).sort_values(["Categoria", out.columns[1]], ascending=[True, True])
    return out

# ============ NAVEGACION ============
pagina_actual = st.query_params.get("pagina", "Inicio")
secciones = ["Inicio", "Resumen", "Analistas", "Supervisores", "Equipos"]
seleccion = st.sidebar.radio("Ir a la sección:", secciones, index=secciones.index(pagina_actual))
if seleccion != pagina_actual:
    st.query_params["pagina"] = seleccion
    st.rerun()

# ============ SIDEBAR FILTROS ============
with st.sidebar:
    st.header("🔎 Filtros")
    sel_prof = sel_sup = sel_ana = sel_estado = sel_nivel = None

    if "profesional" in df.columns and df["profesional"].str.strip().any():
        opciones_prof = ["Todos"] + sorted(df["profesional"].unique())
        sel_prof = st.selectbox("👩‍⚕️ Profesional", opciones_prof)

    if "supervisor" in df.columns:
        opciones_sup = ["Todos"] + sorted(df["supervisor"].unique())
        sel_sup = st.selectbox("🧑‍🏫 Supervisor", opciones_sup)

    if "analista" in df.columns:
        opciones_ana = ["Todos"] + sorted(df["analista"].unique())
        sel_ana = st.selectbox("👤 Analista", opciones_ana)

    if "estado_carpeta" in df.columns:
        opciones_estado = ["Todos"] + sorted(set(df["estado_carpeta"].str.lower().dropna().unique()) | {""})
        sel_estado = st.selectbox("📂 Estado", opciones_estado)

    if "nivel" in df.columns:
        opciones_nivel = ["Todos"] + sorted(df["nivel"].dropna().unique())
        sel_nivel = st.selectbox("🔹 Nivel", opciones_nivel)

# Aplicar filtros
df_filtrado = df.copy()
if sel_prof and sel_prof != "Todos":
    df_filtrado = df_filtrado[df_filtrado["profesional"] == sel_prof]
if sel_sup and sel_sup != "Todos":
    df_filtrado = df_filtrado[df_filtrado["supervisor"] == sel_sup]
if sel_ana and sel_ana != "Todos":
    df_filtrado = df_filtrado[df_filtrado["analista"] == sel_ana]
if sel_estado and sel_estado != "Todos":
    df_filtrado = df_filtrado[df_filtrado["estado_carpeta"].str.lower() == sel_estado.lower()]
if sel_nivel and sel_nivel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["nivel"] == sel_nivel]

# ============ INICIO ============
if pagina_actual == "Inicio":
    # Encabezado de logos (SIN imagen de tablero arriba)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        st.image("assets/Logp GP FUAA.png", use_container_width=True)
    with c2:
        st.empty()  # vacío en el centro
    with c3:
        st.image("assets/Dian.png", use_container_width=True)

    st.markdown("<h1 style='text-align:center; font-weight:700;'>Seguimiento Metas</h1>", unsafe_allow_html=True)

    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.write("")  # espaciado
        if st.button("Resumen", key="btn_home_resumen"):
            st.query_params["pagina"] = "Resumen"
            st.rerun()
        if st.button("Analistas", key="btn_home_analistas"):
            st.query_params["pagina"] = "Analistas"
            st.rerun()
        if st.button("Supervisores", key="btn_home_supervisores"):
            st.query_params["pagina"] = "Supervisores"
            st.rerun()
        if st.button("Equipos", key="btn_home_equipos"):
            st.query_params["pagina"] = "Equipos"
            st.rerun()
    with col_right:
        st.image("assets/Logo Tablero.jpg", use_container_width=True)  # Imagen central (sí se mantiene)

# ============ RESUMEN ============
if pagina_actual == "Resumen":
    st.title("📊 Resumen general")
    dias_habiles = business_days_since_start(date.today() - timedelta(days=1))
    st.info(f"🗓️ Días hábiles considerados: **{dias_habiles}**")

    por_asignar = df_filtrado["estado_carpeta"].fillna("").eq("").sum()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📂 Total carpetas", len(df_filtrado))
    col2.metric("✅ Auditadas", (df_filtrado["estado_carpeta"].str.lower() == "auditada").sum())
    col3.metric("👤 Analistas activos", df_filtrado["analista"].nunique())
    col4.metric("📥 Por asignar", por_asignar)

    st.plotly_chart(grafico_estado_con_meta(df_filtrado, "Resumen", 0), use_container_width=True)

    avance = df_filtrado["estado_carpeta"].str.lower().isin(["auditada", "aprobada", "calificada"]).sum()
    total = len(df_filtrado)
    st.plotly_chart(grafico_avance_total(total, avance), use_container_width=True)

# ============ MÓDULOS CON METAS Y ATRASOS ============
def modulo_vista(nombre_modulo: str):
    st.title(f"🔎 {nombre_modulo}")
    dfm = prepara_df_modulo(df_filtrado, nombre_modulo)

    dias_habiles = business_days_since_start(date.today() - timedelta(days=1))

    # Calcular meta acumulada (y contar sujetos únicos)
    meta_total, n_sujetos = meta_acumulada(nombre_modulo, dfm)

    # Mostrar número de sujetos únicos
    st.info(f"👥 Equipo: **{n_sujetos}** — 🗓️ Días hábiles considerados: **{dias_habiles}**")

    # Desarrolladas totales del módulo (para KPI)
    validos = estados_validos(nombre_modulo)
    desarrolladas_total = (
        dfm["estado_carpeta"].str.lower().isin(validos)
    ).sum() if "estado_carpeta" in dfm.columns else 0
    diferencia_total = desarrolladas_total - meta_total

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📁 Total carpetas", len(dfm))
    c2.metric("✅ Desarrolladas", desarrolladas_total)
    c3.metric("🎯 Meta a la fecha", meta_total)
    c4.metric("Δ Diferencia (Desarrolladas - Meta)", diferencia_total)

    # Cálculo de meta individual
    per_subject = 34 if nombre_modulo == "Supervisores" else 17
    dias_habiles = business_days_since_start(date.today() - timedelta(days=1))
    meta_individual = per_subject * dias_habiles

    fig1 = grafico_estado_con_meta(dfm, nombre_modulo, meta_total)
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = grafico_categorias_barh(dfm, nombre_modulo, meta_individual)
    st.plotly_chart(fig2, use_container_width=True)

    tabla = tabla_resumen(dfm, nombre_modulo, meta_individual)
    st.subheader("📋 Resumen por sujeto")
    st.dataframe(tabla, use_container_width=True)

if pagina_actual == "Analistas":
    modulo_vista("Analistas")

elif pagina_actual == "Supervisores":
    modulo_vista("Supervisores")

elif pagina_actual == "Equipos":
    modulo_vista("Equipos")
