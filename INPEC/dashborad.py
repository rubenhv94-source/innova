# ===================================
# 🔧 CONFIGURACIÓN Y LIBRERÍAS
# ===================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

st.set_page_config(
    page_title="Dashboard Modular",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #ffffff; padding: 16px; }
    h1, h2, h3 { color: #1F9924; text-align: center; }
    [data-testid="stSidebar"] { background-color: #e8f5e9; }
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
        transform: translateY(-1px) !important;
        box-shadow: 0 8px 16px rgba(46,125,50,0.30) !important;
    }
</style>
""", unsafe_allow_html=True)

COLOR_PALETTE = px.colors.sequential.Greens

# ===================================
# 📥 CARGA DE DATOS
# ===================================
@st.cache_data(ttl=600)
def cargar_csv(url: str) -> pd.DataFrame:
    return pd.read_csv(url, dtype=str).fillna("")

URLS = {
    "Cronograma": "https://docs.google.com/spreadsheets/d/e/2PACX-1vThSek_BzK-DeNwhsjcmqSWJLz4vNQ_bBQJ8cXV_pEjCLGN8T64WcIqsLEfQIYcO9dVLCPHfdnNdfhC/pub?gid=1775323779&single=true&output=csv",
    "Entregables": "https://docs.google.com/spreadsheets/d/e/2PACX-1vTXU3Fh-35s_7ZysWWnWQpQhhHxMst_qqFznNeBA1xmvMVYpo7yVODZTaHTqh12ptDViA6CYLLaZWre/pub?gid=1749869584&single=true&output=csv",
    "VRM": "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ1ZNrmbDDZPZbj0-ovO6HRgW7m2MAp3efItgdv8QjOny04F4D5knQ4E2RvMcmQB-L6OS00F13xiiWQ/pub?gid=1175528082&single=true&output=csv",
    "Reclamaciones": "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ1ZNrmbDDZPZbj0-ovO6HRgW7m2MAp3efItgdv8QjOny04F4D5knQ4E2RvMcmQB-L6OS00F13xiiWQ/pub?gid=1175528082&single=true&output=csv"
}

@st.cache_data(ttl=600)
def get_datos_por_modulo(modulo: str) -> pd.DataFrame:
    url = URLS.get(modulo)
    return cargar_csv(url) if url else pd.DataFrame()

def limpiar_datos_por_modulo(modulo: str, df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()

    if modulo == "Cronograma" and "Fecha Inicio" in df.columns:
        df["Fecha Inicio"] = pd.to_datetime(df["Fecha Inicio"], errors="coerce")

    if modulo == "Entregables":
        df["ESTADO"] = np.where((df["REALIZADO POR LA FUAA"] == "VERDADERO")&(df["APROBADO POR LA CNSC"] == "VERDADERO"), "Aprobado", 
                                np.where((df["REALIZADO POR LA FUAA"] == "VERDADERO")&(df["APROBADO POR LA CNSC"] == "FALSO")&(df["OBSERVACIÓN Y/O STATUS"].str.lower().str.contains("rechaz")), "Rechazado",
                                        np.where(df["REALIZADO POR LA FUAA"] == "VERDADERO", "Entregado", "Pendiente")))
    
    return df

def detectar_columnas_filtrables(df: pd.DataFrame, max_unicos=20) -> list:
    return [col for col in df.columns if df[col].nunique() <= max_unicos and not col.lower().startswith("unnamed")]

# ===================================
# 🧰 FUNCIONES UTILITARIAS
# ===================================
def aplicar_filtros_dinamicos(df: pd.DataFrame, filtros: dict) -> pd.DataFrame:
    for col, val in filtros.items():
        if val != "Todos":
            df = df[df[col] == val]
    return df

def generar_filtros_sidebar(df: pd.DataFrame, claves: list[str], clave_prefix: str) -> dict:
    if "filtros" not in st.session_state:
        st.session_state["filtros"] = {}
    if clave_prefix not in st.session_state["filtros"]:
        st.session_state["filtros"][clave_prefix] = {}

    filtros = {}
    for col in claves:
        opciones = ["Todos"] + sorted(df[col].unique())
        default = st.session_state["filtros"][clave_prefix].get(col, "Todos")
        selected = st.sidebar.selectbox(f"Filtrar por {col}", opciones, index=opciones.index(default) if default in opciones else 0)
        st.session_state["filtros"][clave_prefix][col] = selected
        filtros[col] = selected
    return filtros

def semaforizar(valor: int | float, limites: tuple[int, int]) -> str:
    if valor <= limites[0]: return "🟢"
    elif valor <= limites[1]: return "🟡"
    else: return "🔴"

# ===================================
# 📊 FUNCIONES DE VISUALIZACIÓN
# ===================================
def tabla_resaltada(df: pd.DataFrame, columnas: list[str], col_semaforo: str = None, limites=(10, 20)):
    columnas = [c for c in columnas if not c.lower().startswith("unnamed")]
    df_out = df[columnas].copy()
    if col_semaforo and col_semaforo in df_out.columns:
        df_out["Indicador"] = df_out[col_semaforo].astype(float).apply(lambda x: semaforizar(x, limites))
    st.dataframe(df_out, use_container_width=True)

def grafico_barras(df: pd.DataFrame, columna: str, titulo: str):
    conteo = df[columna].value_counts().reset_index()
    conteo.columns = [columna, "cantidad"]
    conteo["porcentaje"] = (conteo["cantidad"] / conteo["cantidad"].sum() * 100).round(1)
    fig = px.bar(conteo, x=columna, y="cantidad", text="porcentaje", color=columna,
                 color_discrete_sequence=COLOR_PALETTE, title=f"<b>{titulo}</b>")
    fig.update_layout(showlegend=False, plot_bgcolor="white", margin=dict(t=50))
    st.plotly_chart(fig, use_container_width=True)

def grafico_embudo(df: pd.DataFrame, columna: str, titulo: str):
    conteo = df[columna].value_counts().reset_index()
    conteo.columns = ["etapa", "cantidad"]
    fig = go.Figure(go.Funnel(y=conteo["etapa"], x=conteo["cantidad"], textinfo="value+percent initial",
                              marker={"color": COLOR_PALETTE[2]}))
    fig.update_layout(title=f"<b>{titulo}</b>", margin=dict(t=50))
    st.plotly_chart(fig, use_container_width=True)

def grafico_anillo(df: pd.DataFrame, columna: str, titulo: str):
    conteo = df[columna].value_counts().reset_index()
    conteo.columns = [columna, "cantidad"]
    fig = px.pie(conteo, names=columna, values="cantidad", hole=0.45,
                 color_discrete_sequence=COLOR_PALETTE, title=f"<b>{titulo}</b>")
    fig.update_traces(textinfo="label+percent", textfont_size=12)
    st.plotly_chart(fig, use_container_width=True)

# ===================================
# 🚦 NAVEGACIÓN Y RENDER
# ===================================
st.sidebar.title("🔎 Navegación")
mod_actual = st.sidebar.radio("Selecciona módulo:", list(URLS.keys()))

if st.sidebar.button("🔄 Refrescar datos"):
    st.cache_data.clear()
    st.rerun()

if st.sidebar.button("🧹 Borrar filtros"):
    if "filtros" in st.session_state:
        st.session_state["filtros"].pop(mod_actual, None)
    st.rerun()

df_base = get_datos_por_modulo(mod_actual)
df_base = limpiar_datos_por_modulo(mod_actual, df_base)

if df_base.empty:
    st.warning("No hay datos disponibles.")
    st.stop()

# Filtros automáticos
cols_filtro = detectar_columnas_filtrables(df_base)
filtros = generar_filtros_sidebar(df_base, cols_filtro, mod_actual)
df_filtrado = aplicar_filtros_dinamicos(df_base, filtros)

st.title(f"📌 {mod_actual}")

# Visualizaciones por módulo (fijas)
vis_default = {
    "Cronograma": ["Tabla", "Barras", "Anillo", "Embudo"],
    "Entregables": ["Tabla", "Barras", "Anillo"],
    "VRM": ["Tabla", "Barras", "Anillo"],
    "Reclamaciones": ["Tabla", "Embudo"]
}.get(mod_actual, ["Tabla"])
vis_seleccionadas = vis_default

# Configuración columnas por módulo
COLUMNAS_TABLA = {
    "Cronograma": ["NO.", "Etapa", "Actividad", "F INICIO P", "F FIN P", "Estado", "Fecha de cumplimiento", "Responsable_contractual"],
    "Entregables": ["NO. DE ENTREGABLE", "NO. DE PAGO", "ENTREGABLE", "ESTADO"],
    "VRM": ["numero_opec", "nivel_x", "estado_carpeta"],
    "Reclamaciones": ["numero_opec", "nivel_x", "estado_carpeta"]
}

COLUMNAS_GRAFICOS = {
    "Cronograma": {"barras": "Estado", "anillo": "Estado", "embudo": "Etapa"},
    "Entregables": {"barras": "ESTADO", "anillo": "ESTADO", "embudo": "ESTADO"},
    "VRM": {"barras": "estado_carpeta", "anillo": "estado_carpeta", "embudo": "estado_carpeta"},
    "Reclamaciones": {"barras": "estado_carpeta", "anillo": "estado_carpeta", "embudo": "estado_carpeta"}
}
cols_graficos = COLUMNAS_GRAFICOS.get(mod_actual, {})
cols_vis = COLUMNAS_TABLA.get(mod_actual, df_filtrado.columns[:5].tolist())

# === Visualización: TABLA ===
if "Tabla" in vis_seleccionadas:
    st.subheader("📋 Tabla de datos")
    tabla_resaltada(df_filtrado, columnas=cols_vis)

# === Visualización: BARRAS ===
if "Barras" in vis_seleccionadas and "barras" in cols_graficos:
    grafico_barras(df_filtrado, columna=cols_graficos["barras"], titulo="Distribución")

# === Visualización: ANILLO ===
if "Anillo" in vis_seleccionadas and "anillo" in cols_graficos:
    grafico_anillo(df_filtrado, columna=cols_graficos["anillo"], titulo="Distribución Anillo")

# === Visualización: EMBUDO ===
if "Embudo" in vis_seleccionadas and "embudo" in cols_graficos:
    grafico_embudo(df_filtrado, columna=cols_graficos["embudo"], titulo="Embudo por etapa")
