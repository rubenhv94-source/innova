# ===================================
# 🔧 CONFIGURACIÓN Y LIBRERÍAS
# ===================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
from typing import Literal

st.set_page_config(
    page_title="Dashboard Modular",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo visual (heredado del tablero original)
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

COLOR_PALETTE = px.colors.sequential.Greens

# ===================================
# 📥 CARGA DE DATOS
# ===================================
@st.cache_data(ttl=600)
def cargar_csv(url: str) -> pd.DataFrame:
    df = pd.read_csv(url, dtype=str).fillna("")
    return df

URLS = {
    "Cronograma": "https://URL_1",
    "Entregables": "https://URL_2",
    "VRM": "https://URL_3",
    "Reclamaciones": "https://URL_4"
}

datos = {nombre: cargar_csv(url) for nombre, url in URLS.items()}

# ===================================
# 🧰 FUNCIONES UTILITARIAS
# ===================================

def aplicar_filtros_dinamicos(df: pd.DataFrame, filtros: dict) -> pd.DataFrame:
    for col, val in filtros.items():
        if val != "Todos":
            df = df[df[col] == val]
    return df

def generar_filtros_sidebar(df: pd.DataFrame, claves: list[str], clave_prefix: str) -> dict:
    filtros = {}
    for col in claves:
        opciones = ["Todos"] + sorted(df[col].unique())
        key = f"{clave_prefix}_{col}"
        default = st.session_state.get(key, "Todos")
        selected = st.sidebar.selectbox(f"Filtrar por {col}", opciones, index=opciones.index(default) if default in opciones else 0, key=key)
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
    df_out = df[columnas].copy()
    if col_semaforo and col_semaforo in df_out.columns:
        df_out["Indicador"] = df_out[col_semaforo].astype(float).apply(lambda x: semaforizar(x, limites))
    st.dataframe(df_out, use_container_width=True)

def grafico_barras(df: pd.DataFrame, columna: str, titulo: str):
    conteo = df[columna].value_counts().reset_index()
    conteo.columns = [columna, "cantidad"]
    conteo["porcentaje"] = (conteo["cantidad"] / conteo["cantidad"].sum() * 100).round(1)
    fig = px.bar(
        conteo,
        x=columna,
        y="cantidad",
        text="porcentaje",
        color=columna,
        color_discrete_sequence=COLOR_PALETTE,
        title=f"<b>{titulo}</b>",
    )
    fig.update_layout(showlegend=False, plot_bgcolor="white", margin=dict(t=50))
    st.plotly_chart(fig, use_container_width=True)

def grafico_embudo(df: pd.DataFrame, columna: str, titulo: str):
    conteo = df[columna].value_counts().reset_index()
    conteo.columns = ["etapa", "cantidad"]
    conteo["porcentaje"] = (conteo["cantidad"] / conteo["cantidad"].sum() * 100).round(1)
    fig = go.Figure(go.Funnel(
        y=conteo["etapa"],
        x=conteo["cantidad"],
        textinfo="value+percent initial",
        marker={"color": COLOR_PALETTE[2]}
    ))
    fig.update_layout(title=f"<b>{titulo}</b>", margin=dict(t=50))
    st.plotly_chart(fig, use_container_width=True)

def grafico_anillo(df: pd.DataFrame, columna: str, titulo: str):
    conteo = df[columna].value_counts().reset_index()
    conteo.columns = [columna, "cantidad"]
    fig = px.pie(
        conteo,
        names=columna,
        values="cantidad",
        hole=0.45,
        color_discrete_sequence=COLOR_PALETTE,
        title=f"<b>{titulo}</b>"
    )
    fig.update_traces(textinfo="label+percent", textfont_size=12)
    st.plotly_chart(fig, use_container_width=True)

# ===================================
# 🚦 NAVEGACIÓN Y RENDER POR MÓDULO
# ===================================

st.sidebar.title("🔎 Navegación")
modulos = list(URLS.keys())
mod_actual = st.sidebar.radio("Selecciona módulo:", modulos)

if st.sidebar.button("🔄 Refrescar datos"):
    st.cache_data.clear()
    st.rerun()

st.title(f"📌 {mod_actual}")

df_base = datos[mod_actual]
if df_base.empty:
    st.warning("No hay datos disponibles.")
    st.stop()

# Define aquí las columnas filtrables para cada módulo
COLUMNAS_FILTRO = {
    "Cronograma": ["estado", "responsable"],
    "Entregables": ["tipo", "prioridad"],
    "VRM": ["categoria", "estado"],
    "Reclamaciones": ["motivo", "estado"]
}
cols_filtro = COLUMNAS_FILTRO.get(mod_actual, [])
filtros = generar_filtros_sidebar(df_base, cols_filtro, mod_actual)
df_filtrado = aplicar_filtros_dinamicos(df_base, filtros)

# Ejemplo de visualizaciones básicas
st.subheader("📋 Tabla de datos")
tabla_resaltada(df_filtrado, columnas=df_filtrado.columns[:5].tolist(), col_semaforo=df_filtrado.columns[-1])

col1, col2 = st.columns(2)
with col1:
    grafico_barras(df_filtrado, columna=df_filtrado.columns[0], titulo="Distribución")
with col2:
    grafico_anillo(df_filtrado, columna=df_filtrado.columns[1], titulo="Distribución Anillo")

grafico_embudo(df_filtrado, columna=df_filtrado.columns[2], titulo="Embudo por etapa")
