import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio

# 🎨 Tema de gráficos
pio.templates.default = "seaborn"
color_palette = px.colors.sequential.Greens

# 📂 Cargar datos desde Google Sheets (CSV público)
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQVxG-bO1D5mkgUFCU35drRV4tyXT9aRaW6q4zzWGa9nFAqkLVdZxaIjwD1cEMJIAXuI4xTBlhHS1og/pub?gid=991630809&single=true&output=csv"

@st.cache_data
def cargar_datos():
    return pd.read_csv(CSV_URL, dtype=str)

df = cargar_datos()

# 🛠 Configuración de página
st.set_page_config(
    page_title="Dashboard VA",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🌟 Estilos generales con fondo blanco
st.markdown("""
<style>
    .stApp {
        background-color: #ffffff;
        padding: 20px;
    }
    h1, h2, h3 {
        color: #2e7d32;
    }
    [data-testid="stSidebar"] {
        background-color: #e8f5e9;
    }
    /* 💨 Animación de entrada global */
    [data-testid="stAppViewContainer"] {
        animation: fadeIn 0.6s ease-in-out;
    }
    @keyframes fadeIn {
        from {opacity: 0;}
        to {opacity: 1;}
    }
</style>
""", unsafe_allow_html=True)

# 🧭 Navegación moderna con query_params + rerun
pagina_actual = st.query_params.get("pagina", "Inicio")
secciones = ["Inicio", "Resumen", "Analistas", "Supervisores", "Equipos"]

seleccion = st.sidebar.radio("Ir a la sección:", secciones, index=secciones.index(pagina_actual))
if seleccion != pagina_actual:
    st.query_params["pagina"] = seleccion
    st.rerun()

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

# 🏠 PÁGINA DE INICIO (institucional + animada)
if pagina_actual == "Inicio":
    st.markdown("""
    <style>
        /* 🔹 Animaciones */
        @keyframes fadeIn {
            from {opacity: 0; transform: translateY(-10px);}
            to {opacity: 1; transform: translateY(0);}
        }
        @keyframes slideUp {
            from {opacity: 0; transform: translateY(30px);}
            to {opacity: 1; transform: translateY(0);}
        }

        /* 🔹 Título y botones */
        .titulo {
            text-align: center;
            color: #2e7d32;
            font-size: 40px;
            font-weight: 700;
            margin-bottom: 25px;
            opacity: 0;
            animation: fadeIn 1s ease-in-out forwards;
            animation-delay: 0.3s;
        }
        .boton-verde {
            display: block;
            background-color: #ffffff;
            color: #2e7d32;
            border: 2px solid #2e7d32;
            border-radius: 40px;
            text-align: center;
            font-size: 18px;
            font-weight: 600;
            margin: 15px 0;
            padding: 12px 20px;
            width: 250px;
            transition: all 0.25s ease;
            text-decoration: none;
            opacity: 0;
            animation: slideUp 1s ease-in-out forwards;
        }
        .boton-verde:nth-child(1) { animation-delay: 0.5s; }
        .boton-verde:nth-child(2) { animation-delay: 0.7s; }
        .boton-verde:nth-child(3) { animation-delay: 0.9s; }
        .boton-verde:nth-child(4) { animation-delay: 1.1s; }

        .boton-verde:hover {
            background-color: #2e7d32;
            color: #ffffff;
            box-shadow: 0 4px 10px rgba(46, 125, 50, 0.3);
            transform: scale(1.04);
        }
    </style>
    """, unsafe_allow_html=True)

    # --- LOGOS SUPERIORES ---
    col_logo1, col_logo2, col_logo3 = st.columns([1, 1, 1])
    with col_logo1:
        st.image("assets/Logp GP FUAA.png", use_container_width=True)
    with col_logo2:
        st.image("assets/Logo Tablero.jpg", use_container_width=True)
    with col_logo3:
        st.image("assets/Dian.png", use_container_width=True)

    # --- TÍTULO PRINCIPAL ---
    st.markdown("<h1 class='titulo'>Seguimiento Metas</h1>", unsafe_allow_html=True)

    # --- BOTONES Y IMAGEN PRINCIPAL ---
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📊 Resumen", key="btn_resumen"):
            st.query_params["pagina"] = "Resumen"
            st.rerun()
        if st.button("👤 Analistas", key="btn_analistas"):
            st.query_params["pagina"] = "Analistas"
            st.rerun()
        if st.button("🧑‍🏫 Supervisores", key="btn_supervisores"):
            st.query_params["pagina"] = "Supervisores"
            st.rerun()
        if st.button("🤝 Equipos", key="btn_equipos"):
            st.query_params["pagina"] = "Equipos"
            st.rerun()

    with col2:
        st.image("assets/Logo Tablero.jpg", use_container_width=True)

# 📈 RESUMEN
elif pagina_actual == "Resumen":
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

# 👤 ANALISTAS
elif pagina_actual == "Analistas":
    st.title("👨‍💼 Análisis por Analista")
    fig = px.histogram(
        df_filtrado, x="analista", color="estado_carpeta",
        barmode="group", color_discrete_sequence=color_palette,
        title="Estado de carpetas por analista"
    )
    st.plotly_chart(fig, use_container_width=True)

# 🧑‍🏫 SUPERVISORES
elif pagina_actual == "Supervisores":
    st.title("🧑‍🏫 Supervisión general")
    if "supervisor" in df_filtrado.columns:
        fig = px.histogram(
            df_filtrado, x="supervisor", color="estado_carpeta",
            barmode="group", color_discrete_sequence=color_palette,
            title="Carpetas por supervisor"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay datos de supervisores disponibles.")

# 🤝 EQUIPOS
elif pagina_actual == "Equipos":
    st.title("🤝 Equipos de trabajo")
    if "equipo" in df_filtrado.columns:
        fig = px.histogram(
            df_filtrado, x="equipo", color="estado_carpeta",
            barmode="group", color_discrete_sequence=color_palette,
            title="Estado por equipo"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay datos de equipos disponibles.")
