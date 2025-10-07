import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime, date, timedelta
import math

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
    h1, h2, h3 { color: #1F9924; text-align: center; }
    [data-testid="stSidebar"] { background-color: #e8f5e9; }
    [data-testid="stAppViewContainer"] { animation: fadeIn 0.5s ease-in-out; }
    @keyframes fadeIn { from {opacity:0;} to {opacity:1;} }
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
    for c in ["analista", "supervisor", "auditor", "estado_carpeta", "profesional", "nivel", "EQUIPO"]:
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
    if modulo == "Analistas":
        return ["auditada", "aprobada", "calificada"]
    return ["auditada", "aprobada"]

def sujetos_col(modulo: str) -> str:
    return {"Analistas": "analista", "Supervisores": "supervisor", "Equipos": "auditor"}[modulo]

def prepara_df_modulo(df_in: pd.DataFrame, modulo: str) -> pd.DataFrame:
    dfm = df_in.copy()
    col = sujetos_col(modulo)
    if col not in dfm.columns:
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
        # Supervisores: <0 Al dia; 0-68 normal; 69-101 medio; >102 alto
        if atraso < 0:
            return "Al día"
        elif atraso <= 68:
            return "Atraso normal"
        elif atraso <= 101:
            return "Atraso medio"
        else:
            return "Atraso alto"
    else:
        # Analistas: <0 Al día; 0-10 normal; 11-34 medio; >35 alto
        if atraso < 0:
            return "Al día"
        elif atraso <= 10:
            return "Atraso normal"
        elif atraso <= 34:
            return "Atraso medio"
        else:
            return "Atraso alto"
            
def grafico_estado_con_meta(df_mod: pd.DataFrame, modulo: str, total_meta: int):
    # --- Conteo por estado ---
    conteo = (
        df_mod["estado_carpeta"]
        .fillna("")
        .str.lower()
        .map(ESTADOS_RENOM)
        .value_counts()
        .reindex(
            [ESTADOS_RENOM.get(e, e) for e in ["asignada", "devuelta", "calificada", "aprobada", "auditada"] + ["Por asignar"]],
            fill_value=0
        )
        .reset_index()
    )

    conteo.columns = ["estado_carpeta", "cantidad"]
    total = conteo["cantidad"].sum()
    conteo["porcentaje"] = (conteo["cantidad"] / total * 100).round(1)
    conteo["label"] = conteo["cantidad"].astype(str) + " (" + conteo["porcentaje"].astype(str) + "%)"

    # --- Gráfico de barras ---
    fig = px.bar(
        conteo,
        x="estado_carpeta",
        y="cantidad",
        color="estado_carpeta",
        color_discrete_sequence=COLOR_PALETTE,
        text="label",
        title="<b>Distribución por estado</b>",
    )

    # --- Línea de meta (azul discontinua sin puntos) ---
    fig.add_scatter(
        x=conteo["estado_carpeta"],
        y=[total_meta] * len(conteo),
        mode="lines",
        name="Meta acumulada",
        line=dict(color="#007BFF", width=2, dash="dash"),
    )

    # --- Texto fijo de la meta ---
    fig.add_annotation(
        text=f"<b>Meta: {total_meta:,.0f}</b>".replace(",", "X").replace(".", ",").replace("X", "."),
        xref="paper", yref="paper",
        x=0.98, y=1.05,  # esquina superior derecha
        showarrow=False,
        font=dict(size=13, color="#007BFF", family="Arial"),
        align="right",
    )

    # --- Ajustes visuales ---
    fig.update_layout(
        showlegend=False,
        xaxis_title="",
        yaxis_title="Cantidad",
        font=dict(family="Arial", size=12),
        plot_bgcolor="white",
        margin=dict(l=20, r=20, t=80, b=40),
        title_font=dict(size=18, color="#1F9924", family="Arial"),
    )

    return fig

def grafico_categorias_barh(df_mod: pd.DataFrame, modulo: str, per_subject_meta: int):
    col = sujetos_col(modulo)
    # desarrolladas por sujeto
    dev = desarrolladas_por_sujeto(df_mod, modulo)
    if dev.empty:
        return px.bar(title="<b>Sin datos para mostrar</b>")

    # meta por sujeto (constante)
    dev["meta"] = per_subject_meta
    dev["atraso"] = dev["meta"] - dev["desarrolladas"]
    dev["categoria"] = dev["atraso"].apply(lambda x: clasifica_categoria(int(x), modulo))

    # conteo por categoría
    cat_count = dev.groupby("categoria").size().reset_index(name="cantidad")
    orden = ["Al día", "Atraso normal", "Atraso medio", "Atraso alto"]
    cat_count["categoria"] = pd.Categorical(cat_count["categoria"], categories=orden, ordered=True)
    cat_count = cat_count.sort_values("categoria")

    # gráfico de barras horizontal
    fig = px.bar(
        cat_count,
        x="cantidad",
        y="categoria",
        orientation="h",
        color="categoria",
        color_discrete_sequence=COLOR_PALETTE,
        title="<b>Cantidad por seguimiento individual</b>",
        text_auto=True,
    )

    # --- Ajustes de diseño ---
    fig.update_layout(
        showlegend=False,
        xaxis_title="Cantidad",
        yaxis_title="",
        font=dict(family="Arial", size=12),
        title_font=dict(size=18, color="#1F9924", family="Arial"),
        plot_bgcolor="white",
        margin=dict(l=20, r=20, t=60, b=40),
    )

    return fig

def grafico_avance_total(total: int, avance: int, meta_ref: int | None = None):
    """
    Gauge semicircular compacto, con:
    - Valor centrado dentro del arco
    - Porcentaje dentro, un poco más arriba
    - Total fuera del gauge
    - Línea roja (meta)
    - Separador de miles con punto fijo
    """

    # Calcular porcentaje
    porcentaje = (avance / total * 100) if total > 0 else 0

    # Crear figura base
    fig = go.Figure(go.Indicator(
        mode="gauge",
        value=avance,
        title={
            "text": "<b>Avance total de carpetas</b>",
            "font": {"size": 18, "color": "#1F9924"}
        },
        gauge={
            "axis": {
                "range": [0, total],
                "tickwidth": 1,
                "tickcolor": "#ccc",
                "tickfont": {"size": 10}
            },
            "bar": {"color": "#2e7d32", "thickness": 0.5},
            "bgcolor": "white",
            "steps": [
                {"range": [0, total * 0.5], "color": "#e0f2f1"},
                {"range": [total * 0.5, total], "color": "#e0f2f1"}
            ],
            "borderwidth": 2,
            "bordercolor": "#cccccc"
        },
        domain={'x': [0, 1], 'y': [0, 1]}
    ))

    # --- Valor central (separador de miles con punto) ---
    valor_formateado = f"{avance:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    fig.add_annotation(
        text=f"<b style='font-size:36px; color:#000;'>{valor_formateado}</b>",
        x=0.5, y=0, showarrow=False,
        xanchor="center"
    )

    # --- Porcentaje (un poco más arriba del número) ---
    fig.add_annotation(
        text=f"<b style='font-size:16px; color:#1F9924;'>{porcentaje:,.1f}%</b>".replace(",", "X").replace(".", ",").replace("X", "."),
        x=0.5, y=0.3, showarrow=False,
        xanchor="center"
    )

    # --- Total debajo del gauge ---
    total_formateado = f"{total:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    fig.add_annotation(
        text=f"Total: {total_formateado}",
        x=0.5, y=-0.1, showarrow=False,
        font=dict(size=13, color="#444", family="Arial"),
        xanchor="center"
    )

    # --- Línea roja (meta esperada) ---
    if meta_ref and 0 < meta_ref < total:
        theta = 180 * (meta_ref / total)
        x0 = 0.5 - 0.35 * math.cos(math.radians(theta))
        y0 = 0.5 + 0.35 * math.sin(math.radians(theta))
        x1 = 0.5 - 0.42 * math.cos(math.radians(theta))
        y1 = 0.5 + 0.42 * math.sin(math.radians(theta))

        fig.add_shape(
            type="line",
            x0=x0, y0=y0, x1=x1, y1=y1,
            line=dict(color="red", width=3)
        )
        fig.add_annotation(
            text="Meta",
            x=x1, y=y1 + 0.05,
            showarrow=False,
            font=dict(size=11, color="red"),
            xanchor="center"
        )

    # --- Ajustes visuales ---
    fig.update_layout(
        margin=dict(l=20, r=20, t=70, b=60),
        height=320,
        paper_bgcolor="#ffffff",
        font={"family": "Arial", "color": "#1a1a1a"}
    )

    return fig

def tabla_resumen(df_mod: pd.DataFrame, modulo: str, per_subject_meta: int) -> pd.DataFrame:
    col = sujetos_col(modulo)

    if df_mod.empty or col not in df_mod.columns:
        return pd.DataFrame(columns=["Categoria", col.capitalize(), "Analizadas", "Meta", "Faltantes"])

    if modulo.lower() == "analistas":
        estados_efectivos = {"auditada", "aprobada", "calificada"}
    elif modulo.lower() == "supervisores":
        estados_efectivos = {"auditada", "aprobada"}
    else:
        estados_efectivos = set()

    # --- Preprocesamiento ---
    df_mod = df_mod.dropna(subset=["estado_carpeta", col])
    df_mod["estado_carpeta"] = df_mod["estado_carpeta"].str.strip().str.lower()

    # --- Pivot por estado ---
    pivot = (
        df_mod
        .groupby([col, "estado_carpeta"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    # --- Asegurar que todos los ESTADOS_ORDEN estén presentes ---
    for estado in ESTADOS_ORDEN:
        if estado not in pivot.columns:
            pivot[estado] = 0

    # --- Calcular "Analizadas" solo con estados efectivos ---
    pivot["Analizadas"] = pivot[[e for e in ESTADOS_ORDEN if e in estados_efectivos]].sum(axis=1)
    pivot["Meta"] = per_subject_meta
    pivot["Faltantes"] = pivot["Meta"] - pivot["Analizadas"]
    pivot["Categoria"] = pivot["Faltantes"].apply(lambda x: clasifica_categoria(int(x), modulo))

    # --- Orden final de columnas ---
    columnas_estado = ESTADOS_ORDEN
    out = pivot[[col] + columnas_estado + ["Analizadas", "Meta", "Faltantes", "Categoria"]]

    # --- Ordenar por categoría ---
    categorias = ["Al día", "Atraso normal", "Atraso medio", "Atraso alto"]
    out["Categoria"] = pd.Categorical(out["Categoria"], categories=categorias, ordered=True)
    out = out.sort_values(["Categoria", col], ascending=[True, True])

    # --- Renombrar columnas de estados ---
    out = out.rename(columns={col: col.capitalize(), **{e: ESTADOS_RENOM.get(e, e) for e in columnas_estado}})

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
        sel_prof = st.selectbox("👩‍💼 Profesional", opciones_prof)

    if "supervisor" in df.columns:
        opciones_sup = ["Todos"] + sorted(df["supervisor"].unique())
        sel_sup = st.selectbox("🕵️‍♀️ Supervisor", opciones_sup)

    if "analista" in df.columns:
        opciones_ana = ["Todos"] + sorted(df["analista"].unique())
        sel_ana = st.selectbox("👨‍💻 Analista", opciones_ana)

    if "estado_carpeta" in df.columns:
        opciones_estado = ["Todos"] + sorted(set(df["estado_carpeta"].str.lower().dropna().unique()) | {""})
        sel_estado = st.selectbox("📤 Estado", opciones_estado)

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
        st.empty()
    with c3:
        st.image("assets/Andina.png", width=200)

    st.markdown("<h1 style='text-align:center; font-weight:700; color:#1F9924'>Seguimiento de Metas VA DIAN 2667</h1>", unsafe_allow_html=True)

    col_left, col_center, col_right = st.columns([1, 1, 1])
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
    with col_center:
        st.image("assets/Logo Tablero.jpg", use_container_width=True)
        
# ============ RESUMEN ============
if pagina_actual == "Resumen":
    #st.title("Resumen general")
    st.markdown(f"<h1 style='color:#1F9924;'>Resumen general</h1>", unsafe_allow_html=True)
    dias_habiles = business_days_since_start(date.today() - timedelta(days=1))
    st.info(f"Días hábiles considerados: **{dias_habiles}**")

    por_asignar = df_filtrado["estado_carpeta"].fillna("").eq("").sum()
    equipo_va = df_filtrado["analista"].nunique() + df_filtrado["supervisor"].nunique()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📂 Total carpetas", f"{len(df_filtrado):,}".replace(",", "."))
    col2.metric("✔️ Auditadas", f"{(df_filtrado['estado_carpeta'].str.lower() == 'auditada').sum():,}".replace(",", "."))
    col3.metric("👨‍👧‍👧 Equipo VA", f"{equipo_va:,}".replace(",", "."))
    col4.metric("📌 Por asignar", f"{por_asignar:,}".replace(",", "."))

    avance = df_filtrado["estado_carpeta"].str.lower().isin(["auditada"]).sum()
    total = len(df_filtrado)
    dfm = prepara_df_modulo(df_filtrado, "Supervisores")
    meta_total, n_sujetos = meta_acumulada("Supervisores", dfm)
    fig_gauge = grafico_avance_total(total, avance, meta_total)
    st.plotly_chart(fig_gauge, use_container_width=True)

    fig_estado = grafico_estado_con_meta(df_filtrado, "Resumen", meta_total)
    st.plotly_chart(fig_estado, use_container_width=True)

# ============ MÓDULOS CON METAS Y ATRASOS ============
def modulo_vista(nombre_modulo: str):
    st.markdown(f"<h1 style='color:#1F9924;'>{nombre_modulo}</h1>", unsafe_allow_html=True)
    dfm = prepara_df_modulo(df_filtrado, nombre_modulo)

    dias_habiles = business_days_since_start(date.today() - timedelta(days=1))
    meta_total, n_sujetos = meta_acumulada(nombre_modulo, dfm)
    st.info(f"Equipo: **{n_sujetos:,}** — Días hábiles considerados: **{dias_habiles}**".replace(",", "."))

    validos = estados_validos(nombre_modulo)
    desarrolladas_total = (
        dfm["estado_carpeta"].str.lower().isin(validos)
    ).sum() if "estado_carpeta" in dfm.columns else 0
    diferencia_total = desarrolladas_total - meta_total

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📂 Total carpetas", f"{len(dfm):,}".replace(",", "."))
    c2.metric("✔️ Desarrolladas", f"{desarrolladas_total:,}".replace(",", "."))
    c3.metric("🎯 Meta a la fecha", f"{meta_total:,}".replace(",", "."))
    c4.metric("⚠️ Diferencia", f"{diferencia_total:,}".replace(",", "."))

    per_subject = 34 if nombre_modulo == "Supervisores" else 17
    meta_individual = per_subject * dias_habiles

    col_fig1, col_fig2 = st.columns(2)
    with col_fig1:
        fig1 = grafico_estado_con_meta(dfm, nombre_modulo, meta_total)
        st.plotly_chart(fig1, use_container_width=True)
    with col_fig2:
        fig2 = grafico_categorias_barh(dfm, nombre_modulo, meta_individual)
        st.plotly_chart(fig2, use_container_width=True)

    analistas_filtrados = sorted(df_filtrado["analista"].dropna().unique())
    supervisores_filtrados = sorted(df_filtrado["supervisor"].dropna().unique())
    auditores_filtrados = sorted(df_filtrado["auditor"].dropna().unique())

    if len(analistas_filtrados) == 0:
        analista_label_1 = "No disponible"
        analista_label_2 = "No disponible"
    elif len(analistas_filtrados) == 1:
        analista_label_1 = analistas_filtrados[0]
        analista_label_2 = ""
    elif len(analistas_filtrados) == 2:
        analista_label_1 = analistas_filtrados[0]
        analista_label_2 = analistas_filtrados[1]
    else:
        analista_label_1 = "Varios"
        analista_label_2 = "Varios"
    
    if len(supervisores_filtrados) == 1:
        supervisor_label = supervisores_filtrados[0]
    elif len(supervisores_filtrados) > 1:
        supervisor_label = "Varios"
    else:
        supervisor_label = "No disponible"

    if len(auditores_filtrados) == 1:
        auditor_label = auditores_filtrados[0]
    elif len(auditores_filtrados) > 1:
        auditor_label = "Varios"
    else:
        auditor_label = "No disponible"

    def custom_metric(label: str, value: str, color="#2e7d32"):
        st.markdown(
            f"""
            <div style="
                background-color: #ffffff;
                border: 2px solid {color};
                border-radius: 12px;
                padding: 10px 8px;
                text-align: center;
                box-shadow: 0 4px 10px rgba(46,125,50,0.15);
                transition: all 0.2s ease-in-out;
                ">
                <div style="font-size:13px; color:#666; font-weight:500;">{label}</div>
                <div style="font-size:15px; font-weight:700; color:#1a1a1a; margin-top:2px;">{value}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with st.container():
        cx1, cx2 = st.columns(2)
    
        if nombre_modulo == 'Analistas':
            with cx1:
                custom_metric("🕵️‍♀️ Supervisor", supervisor_label)
            with cx2:
                custom_metric("👩‍💼 Profesional", auditor_label)
    
        elif nombre_modulo == 'Supervisores':
            if analista_label_2:
                cxa1, cxa2 = cx1.columns(2)
                with cxa1:
                    custom_metric("👨‍💻 Analista1", analista_label_1)
                with cxa2:
                    custom_metric("👨‍💻 Analista2", analista_label_2)
            else:
                with cx1:
                    custom_metric("👨‍💻 Analista", analista_label_1)
            with cx2:
                custom_metric("👩‍💼 Profesional", auditor_label)
    
        else:
            if analista_label_2:
                cxa1, cxa2 = cx1.columns(2)
                with cxa1:
                    custom_metric("👨‍💻 Analista1", analista_label_1)
                with cxa2:
                    custom_metric("👨‍💻 Analista2", analista_label_2)
            else:
                with cx1:
                    custom_metric("👨‍💻 Analista", analista_label_1)
            with cx2:
                custom_metric("👩‍💼 Profesional", auditor_label)
    
    tabla = tabla_resumen(dfm, nombre_modulo, meta_individual)
    st.markdown(f"<h3 style='color:#1F9924; font-weight:600; margin-top: 1em;'>Resumen {nombre_modulo}</h3>", unsafe_allow_html=True)
    st.dataframe(tabla, use_container_width=True)

if pagina_actual == "Analistas":
    modulo_vista("Analistas")
elif pagina_actual == "Supervisores":
    modulo_vista("Supervisores")
elif pagina_actual == "Equipos":
    modulo_vista("Equipos")
