import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio

# 🎨 Tema de gráficos en gama de verdes
pio.templates.default = "seaborn"
color_palette = px.colors.sequential.Greens

# 📂 Fuente de datos
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQVxG-bO1D5mkgUFCU35drRV4tyXT9aRaW6q4zzWGa9nFAqkLVdZxaIjwD1cEMJIAXuI4xTBlhHS1og/pub?gid=991630809&single=true&output=csv"

@st.cache_data
def cargar_datos():
    df = pd.read_csv(CSV_URL, dtype=str)
    return df

df = cargar_datos()

# 🔧 Configuración de página
st.set_page_config(
    page_title="Dashboard VA",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 💅 Estilos visuales
st.markdown("""
    <style>
        .main { background-color: #f0fdf4; }
        h1, h2, h3 { color: #2e7d32; }
        .stApp {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 12px;
        }
    </style>
    """, unsafe_allow_html=True)

# 📚 Menú de navegación
st.sidebar.title("📁 Navegación")
pagina = st.sidebar.radio("Ir a la sección:", ["Resumen", "Analistas", "Supervisores", "Equipos"])

# 🎛 Filtros generales (visibles en todas las secciones)
with st.sidebar:
    st.header("🔎 Filtros generales")
    analistas = df['analista'].dropna().unique()
    analista_sel = st.selectbox("👤 Analista", ["Todos"] + list(analistas))

    estado_sel = st.multiselect(
        "📂 Estado de carpeta",
        options=df['estado_carpeta'].dropna().unique(),
        default=df['estado_carpeta'].dropna().unique()
    )

# Aplicar filtros
df_filtrado = df.copy()
if analista_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado['analista'] == analista_sel]
df_filtrado = df_filtrado[df_filtrado['estado_carpeta'].isin(estado_sel)]

# 🌐 Página: RESUMEN
if pagina == "Resumen":
    st.title("📊 Valoración de antecedentes - Resumen")

    col1, col2, col3 = st.columns(3)
    col1.metric("📁 Total carpetas", len(df_filtrado))
    col2.metric("✅ Auditadas", (df_filtrado['estado_carpeta'] == 'auditada').sum())
    col3.metric("👥 Analistas activos", df_filtrado['analista'].nunique())

    col4, col5 = st.columns(2)

    with col4:
        st.subheader("📈 Estado de carpetas")
        fig_estado = px.histogram(
            df_filtrado,
            x="estado_carpeta",
            color="estado_carpeta",
            text_auto=True,
            color_discrete_sequence=color_palette
        )
        st.plotly_chart(fig_estado, use_container_width=True)

    with col5:
        st.subheader("👤 Carpetas por analista")
        fig_analista = px.histogram(
            df_filtrado,
            x="analista",
            color="estado_carpeta",
            barmode="group",
            color_discrete_sequence=color_palette
        )
        st.plotly_chart(fig_analista, use_container_width=True)

    with st.expander("📄 Ver registros detallados"):
        st.dataframe(df_filtrado.head(100))

# 👤 Página: ANALISTAS
elif pagina == "Analistas":
    st.title("👨‍💼 Análisis por Analista")

    fig = px.histogram(
        df_filtrado,
        x="analista",
        color="estado_carpeta",
        barmode="group",
        color_discrete_sequence=color_palette,
        title="Estado de carpetas por analista"
    )
    st.plotly_chart(fig, use_container_width=True)

# 🧑‍🏫 Página: SUPERVISORES
elif pagina == "Supervisores":
    st.title("🧑‍🏫 Supervisión general")

    if "supervisor" in df_filtrado.columns:
        fig = px.histogram(
            df_filtrado,
            x="supervisor",
            color="estado_carpeta",
            barmode="group",
            color_discrete_sequence=color_palette,
            title="Carpetas por supervisor"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay datos de supervisores disponibles.")

# 🧑‍🤝‍🧑 Página: EQUIPOS
elif pagina == "Equipos":
    st.title("🤝 Equipos de trabajo")

    if "equipo" in df_filtrado.columns:
        fig = px.histogram(
            df_filtrado,
            x="equipo",
            color="estado_carpeta",
            barmode="group",
            color_discrete_sequence=color_palette,
            title="Estado por equipo"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay datos de equipos disponibles.")
