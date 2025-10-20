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
    [data-testid="stSidebar"] { background-color: #8ECD93; }
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

COLOR_PALETTE = [
    "#31A354",  # Verde medio
    "#74C476",  # Verde claro
    "#A1D99B",  # Verde pastel
    "#C7E9C0"   # Verde muy claro
]

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
    #"Reclamaciones": "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ1ZNrmbDDZPZbj0-ovO6HRgW7m2MAp3efItgdv8QjOny04F4D5knQ4E2RvMcmQB-L6OS00F13xiiWQ/pub?gid=1175528082&single=true&output=csv"
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
        df["ESTADO"] = np.where((df["REALIZADO POR LA FUAA"] == "TRUE")&(df["APROBADO POR LA CNSC"] == "TRUE"), "Aprobado", 
                                np.where((df["REALIZADO POR LA FUAA"] == "TRUE")&(df["APROBADO POR LA CNSC"] == "FALSE")&(df["OBSERVACIÓN Y/O STATUS"].str.lower().str.contains("rechaz")), "Rechazado",
                                        np.where(df["REALIZADO POR LA FUAA"] == "TRUE", "Entregado", "Pendiente")))
    
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

# ===================================
# 📊 FUNCIONES DE VISUALIZACIÓN
# ===================================
def tabla_resaltada(
    df: pd.DataFrame,
    columnas: list[str],
    col_estado: str = None,
    colores_estado: dict = None
):
    columnas = [c for c in columnas if not c.lower().startswith("unnamed")]
    df_out = df[columnas].copy()

    if col_estado and colores_estado and col_estado in df_out.columns:
        def color_columna(val):
            estado = str(val).strip().upper()
            color = colores_estado.get(estado)
            return f"background-color: {color}" if color else ""

        styled = df_out.style.applymap(color_columna, subset=[col_estado])
        st.dataframe(styled, use_container_width=True, hide_index=True)
    else:
        st.dataframe(df_out, use_container_width=True, hide_index=True)

def grafico_barras(df: pd.DataFrame, columna: str, titulo: str):
    conteo = df[columna].value_counts().reset_index()
    conteo.columns = [columna, "cantidad"]
    conteo["porcentaje"] = (conteo["cantidad"] / conteo["cantidad"].sum() * 100).round(1)
    conteo["texto"] = conteo["cantidad"].astype(str) + " (" + conteo["porcentaje"].astype(str) + "%)"

    fig = px.bar(
        conteo,
        x=columna,
        y="cantidad",
        text="texto",
        color=columna,
        color_discrete_sequence=COLOR_PALETTE,
        title=f"<b>{titulo}</b>"
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False, plot_bgcolor="white", margin=dict(t=50))
    st.plotly_chart(fig, use_container_width=True)

def grafico_embudo(df: pd.DataFrame, columna: str, titulo: str):
    conteo = df[columna].value_counts().reset_index()
    conteo.columns = ["etapa", "cantidad"]
    total = conteo["cantidad"].sum()
    conteo["porcentaje"] = (conteo["cantidad"] / total * 100).round(1)
    conteo["texto"] = conteo["cantidad"].astype(str) + " (" + conteo["porcentaje"].astype(str) + "%)"

    fig = go.Figure(go.Funnel(
        y=conteo["etapa"],
        x=conteo["cantidad"],
        text=conteo["texto"],
        textposition="outside",
        marker={"color": COLOR_PALETTE[2]}
    ))

    fig.update_layout(title=f"<b>{titulo}</b>", margin=dict(t=50))
    st.plotly_chart(fig, use_container_width=True)

def grafico_anillo(df: pd.DataFrame, columna: str, titulo: str):
    conteo = df[columna].value_counts().reset_index()
    conteo.columns = [columna, "cantidad"]
    conteo["porcentaje"] = (conteo["cantidad"] / conteo["cantidad"].sum() * 100).round(1)
    conteo["texto"] = conteo[columna] + ": " + conteo["cantidad"].astype(str) + " (" + conteo["porcentaje"].astype(str) + "%)"

    fig = px.pie(
        conteo,
        names="texto",
        values="cantidad",
        hole=0.45,
        color_discrete_sequence=COLOR_PALETTE,
        title=f"<b>{titulo}</b>"
    )
    fig.update_traces(textinfo="label+percent", textfont_size=12)
    st.plotly_chart(fig, use_container_width=True)

# ===================================
# 🚦 NAVEGACIÓN Y RENDER
# ===================================
st.title("Proceso de Selección INPEC Cuerpo de Custodia y Vigilancia 11")
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

st.title(f"{mod_actual}")

# Visualizaciones por módulo (fijas)
vis_default = {
    "Cronograma": ["Tabla", "Barras", "Barras", "Anillo", "Embudo"],
    "Entregables": ["Tabla", "Barras", "Anillo"],
    "VRM": ["Tabla", "Barras"],
    "Reclamaciones": ["Tabla", "Embudo"]
}.get(mod_actual, ["Tabla"])
vis_seleccionadas = vis_default

# Configuración columnas por módulo
COLUMNAS_TABLA = {
    "Cronograma": ["NO.", "Etapa", "Actividad", "F INICIO P", "F FIN P", "Estado", "Fecha de cumplimiento", "Responsable_contractual"],
    "Entregables": ["NO. DE ENTREGABLE", "NO. DE PAGO", "ENTREGABLE", "ESTADO"],
    "VRM": ["convocatoria", "numero_opec", "nivel_x", "estado_rm", "estado_carpeta"],
    "Reclamaciones": ["numero_opec", "nivel_x", "estado_carpeta"]
}

COLUMNAS_GRAFICOS = {
    "Cronograma": {"barras": ["Estado", "Etapa"]},
    "Entregables": {"barras": ["ESTADO"], "anillo": "NO. DE PAGO"},
    "VRM": {"anillo": "estado_rm", "embudo": "estado_carpeta"},
    "Reclamaciones": {"barras": "estado_carpeta", "anillo": "estado_carpeta", "embudo": "estado_carpeta"}
}
cols_graficos = COLUMNAS_GRAFICOS.get(mod_actual, {})
cols_vis = COLUMNAS_TABLA.get(mod_actual, df_filtrado.columns[:5].tolist())

# === Visualización: TABLA ===

colores_cronograma = {
    "VENCIDO": "#f8d7da",             # rojo claro
    "PROXIMO A VENCER": "#fff3cd",    # amarillo claro
    "EN GESTIÓN": "#d4edda"           # verde claro
}

if "Tabla" in vis_seleccionadas:
    st.subheader("📋 Tabla de datos")
    tabla_resaltada(
        df_filtrado,
        columnas=cols_vis,
        col_estado="Estado",
        colores_estado=colores_cronograma
    )

# === Visualización: BARRAS ===
if "Barras" in vis_seleccionadas and "barras" in cols_graficos:
    for col in cols_graficos["barras"]:
        grafico_barras(df_filtrado, columna=col, titulo=f"Distribución por {col}")

# === Visualización: ANILLO ===
if "Anillo" in vis_seleccionadas and "anillo" in cols_graficos:
    grafico_anillo(df_filtrado, columna=cols_graficos["anillo"], titulo=f"Distribución por {cols_graficos["anillo"]}")

# === Visualización: EMBUDO ===
if "Embudo" in vis_seleccionadas and "embudo" in cols_graficos:
    grafico_embudo(df_filtrado, columna=cols_graficos["embudo"], titulo=f"Embudo por {cols_graficos["embudo"]}")
