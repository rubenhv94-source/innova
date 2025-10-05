import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio

# 🎨 Tema de gráficos
pio.templates.default = "seaborn"
color_palette = px.colors.sequential.Greens

# 📂 URL del CSV
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQVxG-bO1D5mkgUFCU35drRV4tyXT9aRaW6q4zzWGa9nFAqkLVdZxaIjwD1cEMJIAXuI4xTBlhHS1og/pub?gid=991630809&single=true&output=csv"

@st.cache_data
def cargar_datos():
    df = pd.read_csv(CSV_URL, dtype=str)
    return df

df = cargar_datos()

# 🚧 Configuración de página
st.set_page_config(
    page_title="Dashboard VA",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🎨 Estilos personalizados
st.markdown("""
<style>
    .stApp {
        background-color: #f0fdf4;
        padding: 20px;
    }
    .css-1d391kg {  /* Título principal */
        color: #2e7d32 !important;
    }
    [data-testid="stSidebar"] {
        background-color: #e8f5e9;
    }
</style>
""", unsafe_allow_html=True)

# 📚 Menú lateral
st.sidebar.title("📁 Módulos disponibles")
# Lee el parámetro si existe, si no muestra "Inicio"
pagina_actual = st.query_params.get("pagina", "Inicio")
pagina = st.sidebar.radio("Ir a la sección:", ["Inicio", "Resumen", "Analistas", "Supervisores", "Equipos"], index=["Inicio", "Resumen", "Analistas", "Supervisores", "Equipos"].index(pagina_actual))

# 🎛 Filtros generales
with st.sidebar:
    st.header("🔎 Filtros generales")

    analistas = df['analista'].dropna().unique()
    analista_sel = st.selectbox("👤 Analista", ["Todos"] + list(analistas))

    estados = df['estado_carpeta'].dropna().unique()
    estado_sel = st.selectbox("📂 Estado de carpeta", ["Todos"] + list(estados))

# Aplicar filtros
df_filtrado = df.copy()
if analista_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado['analista'] == analista_sel]
if estado_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado['estado_carpeta'] == estado_sel]

# 🏠 Página de INICIO con índice visual
if pagina == "Inicio":
    st.title("🎯 Dashboard de Valoración de Antecedentes DIAN")
    st.markdown("### Bienvenido, selecciona una sección para comenzar:")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 Resumen"):
            st.query_params["pagina"] = "Resumen"
    with col2:
        if st.button("👤 Analistas"):
            st.query_params["pagina"] = "Analistas"

    col3, col4 = st.columns(2)
    with col3:
        if st.button("🧑‍🏫 Supervisores"):
            st.query_params["pagina"] = "Supervisores"
    with col4:
        if st.button("🤝 Equipos"):
            st.query_params["pagina"] = "Equipos"

# 📈 Página de RESUMEN
elif pagina == "Resumen":
    st.title("📊 Resumen general")

    col1, col2, col3 = st.columns(3)
    col1.metric("📁 Total carpetas", len(df_filtrado))
    col2.metric("✅ Auditadas", (df_filtrado['estado_carpeta'] == 'auditada').sum())
    col3.metric("👥 Analistas activos", df_filtrado['analista'].nunique())

    col4, col5 = st.columns(2)
    with col4:
        st.subheader("📈 Estado de carpetas")
        fig_estado = px.histogram(
            df_filtrado, x="estado_carpeta", color="estado_carpeta",
            text_auto=True, color_discrete_sequence=color_palette
        )
        st.plotly_chart(fig_estado, use_container_width=True)
    with col5:
        st.subheader("👤 Carpetas por analista")
        fig_analista = px.histogram(
            df_filtrado, x="analista", color="estado_carpeta",
            barmode="group", color_discrete_sequence=color_palette
        )
        st.plotly_chart(fig_analista, use_container_width=True)

    with st.expander("📄 Ver registros detallados"):
        st.dataframe(df_filtrado.head(100))

# 👤 Página de ANALISTAS
elif pagina == "Analistas":
    st.title("👨‍💼 Análisis por Analista")
    fig = px.histogram(
        df_filtrado, x="analista", color="estado_carpeta",
        barmode="group", color_discrete_sequence=color_palette
    )
    st.plotly_chart(fig, use_container_width=True)

# 🧑‍🏫 Página de SUPERVISORES
elif pagina == "Supervisores":
    st.title("🧑‍🏫 Supervisión general")
    if "supervisor" in df_filtrado.columns:
        fig = px.histogram(
            df_filtrado, x="supervisor", color="estado_carpeta",
            barmode="group", color_discrete_sequence=color_palette
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay datos de supervisores disponibles.")

# 👥 Página de EQUIPOS
elif pagina == "Equipos":
    st.title("🤝 Equipos de trabajo")
    if "equipo" in df_filtrado.columns:
        fig = px.histogram(
            df_filtrado, x="equipo", color="estado_carpeta",
            barmode="group", color_discrete_sequence=color_palette
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay datos de equipos disponibles.")
