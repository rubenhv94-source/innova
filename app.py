import streamlit as st
import pandas as pd
import plotly.express as px

# Cargar los datos desde archivos temporales (los exportaremos desde Colab más abajo)
df_consolidado = pd.read_csv("df_consolidado.csv")
df_inscritos = pd.read_csv("df_inscritos.csv")
cruce_estado = pd.read_csv("cruce_estado.csv")

st.set_page_config(page_title="Dashboard VA", layout="wide")

st.title("📊 Dashboard VA - Visualización de Datos Consolidados")

# Filtros
with st.sidebar:
    st.header("Filtros")
    analistas = df_consolidado['analista'].dropna().unique()
    analista_sel = st.selectbox("Analista", ["Todos"] + list(analistas))

    estado_sel = st.multiselect(
        "Estado de carpeta",
        options=df_consolidado['estado_carpeta'].dropna().unique(),
        default=df_consolidado['estado_carpeta'].dropna().unique()
    )

# Aplicar filtros
df_filtrado = df_consolidado.copy()
if analista_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado['analista'] == analista_sel]

df_filtrado = df_filtrado[df_filtrado['estado_carpeta'].isin(estado_sel)]

# Métricas
st.subheader("Resumen")
col1, col2, col3 = st.columns(3)
col1.metric("Total carpetas", len(df_filtrado))
col2.metric("Carpetas auditadas", (df_filtrado['estado_carpeta'] == 'auditada').sum())
col3.metric("Inscritos", len(df_inscritos))

# Gráfico 1: Estado de carpeta
st.subheader("Distribución por estado de carpeta")
fig_estado = px.histogram(df_filtrado, x="estado_carpeta", color="estado_carpeta", text_auto=True)
st.plotly_chart(fig_estado, use_container_width=True)

# Gráfico 2: Carpetas por analista
st.subheader("Carpetas por analista")
fig_analista = px.histogram(df_filtrado, x="analista", color="estado_carpeta", barmode="group")
st.plotly_chart(fig_analista, use_container_width=True)

# Tabla
st.subheader("Detalle de registros")
st.dataframe(df_filtrado.head(100))
