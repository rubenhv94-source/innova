import streamlit as st
import pandas as pd
import plotly.express as px

# URL pública al CSV de Google Sheets
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQVxG-bO1D5mkgUFCU35drRV4tyXT9aRaW6q4zzWGa9nFAqkLVdZxaIjwD1cEMJIAXuI4xTBlhHS1og/pub?gid=991630809&single=true&output=csv"

@st.cache_data
def cargar_datos():
    df = pd.read_csv(CSV_URL, dtype=str)
    return df

df = cargar_datos()

st.set_page_config(page_title="Dashboard VA", layout="wide")
st.title("📊 Dashboard VA - Consolidado Final")

# Filtros laterales
with st.sidebar:
    st.header("Filtros")
    analistas = df['analista'].dropna().unique()
    analista_sel = st.selectbox("Analista", ["Todos"] + list(analistas))

    estado_sel = st.multiselect(
        "Estado de carpeta",
        options=df['estado_carpeta'].dropna().unique(),
        default=df['estado_carpeta'].dropna().unique()
    )

# Aplicar filtros
df_filtrado = df.copy()
if analista_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado['analista'] == analista_sel]

df_filtrado = df_filtrado[df_filtrado['estado_carpeta'].isin(estado_sel)]

# Métricas
st.subheader("Resumen")
col1, col2, col3 = st.columns(3)
col1.metric("Total carpetas", len(df_filtrado))
col2.metric("Auditadas", (df_filtrado['estado_carpeta'] == 'auditada').sum())
col3.metric("Analistas", df_filtrado['analista'].nunique())

# Gráficos
st.subheader("Distribución por estado de carpeta")
fig_estado = px.histogram(df_filtrado, x="estado_carpeta", color="estado_carpeta", text_auto=True)
st.plotly_chart(fig_estado, use_container_width=True)

st.subheader("Carpetas por analista")
fig_analista = px.histogram(df_filtrado, x="analista", color="estado_carpeta", barmode="group")
st.plotly_chart(fig_analista, use_container_width=True)

# Tabla
st.subheader("Detalle de registros")
st.dataframe(df_filtrado.head(100))
