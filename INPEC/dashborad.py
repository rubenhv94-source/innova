# ===================================
# 🔧 CONFIGURACIÓN Y LIBRERÍAS
# ===================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
from pytz import timezone
from datetime import datetime, timedelta
import time, hmac, hashlib

# ===================================
# SEGURIDAD
# ===================================

def _hash_pwd(pwd: str, salt: str) -> str:
    return hashlib.sha256((salt + pwd).encode("utf-8")).hexdigest()

def password_gate(form_title: str = "Acceso"):
    # Lee secretos (Cloud: Settings → Secrets)
    SECRET = st.secrets.get("APP_PASSWORD", None)
    SALT = st.secrets.get("APP_SALT", "salt_por_defecto")
    if not SECRET:
        st.error("No se configuró APP_PASSWORD en Secrets. Ve a Settings → Secrets.")
        st.stop()

    # Estado de sesión
    st.session_state.setdefault("auth_ok", False)
    st.session_state.setdefault("tries", 0)
    st.session_state.setdefault("lock_until", 0.0)

    # Si autenticado, muestra logout y continúa
    if st.session_state["auth_ok"]:
        if st.sidebar.button("🔒 Cerrar sesión"):
            for k in ("auth_ok", "tries", "lock_until"):
                st.session_state.pop(k, None)
            st.rerun()
        return  # deja pasar

    # Antibrute-force sencillo: 5 intentos → 5 min de espera
    now = time.time()
    if now < st.session_state["lock_until"]:
        restante = int(st.session_state["lock_until"] - now)
        st.error(f"Demasiados intentos. Intenta de nuevo en {restante} s.")
        st.stop()

    with st.form(form_title):
        pwd = st.text_input("Contraseña", type="password")
        ok = st.form_submit_button("Entrar")

    if ok:
        # Comparación segura con HMAC
        given = _hash_pwd(pwd, SALT)
        expected = _hash_pwd(SECRET, SALT)
        if hmac.compare_digest(given, expected):
            st.session_state["auth_ok"] = True
            st.session_state["tries"] = 0
            st.rerun()
        else:
            st.session_state["tries"] += 1
            if st.session_state["tries"] >= 5:
                st.session_state["lock_until"] = time.time() + 5*60
                st.warning("Demasiados intentos. Bloqueado por 5 minutos.")
            else:
                st.error("Contraseña incorrecta.")
            st.stop()
    else:
        st.info("Ingresa la contraseña para continuar.")
        st.stop()

# 🔐 Activa el gate al inicio:
password_gate("🔐 Acceso al tablero")
# ====== FIN DEL GATE ======

# ===================================
# TABLERO
# ===================================

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
    "VRM": "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ1ZNrmbDDZPZbj0-ovO6HRgW7m2MAp3efItgdv8QjOny04F4D5knQ4E2RvMcmQB-L6OS00F13xiiWQ/pub?gid=1175528082&single=true&output=csv"#,
    #"Reclamaciones": "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ1ZNrmbDDZPZbj0-ovO6HRgW7m2MAp3efItgdv8QjOny04F4D5knQ4E2RvMcmQB-L6OS00F13xiiWQ/pub?gid=1175528082&single=true&output=csv"
}

hoja_metas = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ1ZNrmbDDZPZbj0-ovO6HRgW7m2MAp3efItgdv8QjOny04F4D5knQ4E2RvMcmQB-L6OS00F13xiiWQ/pub?gid=1567229219&single=true&output=csv"
archivo_metas = cargar_csv(hoja_metas)

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
        df["ESTADO"] = np.where(
            (df["REALIZADO POR LA FUAA"] == "TRUE") & (df["APROBADO POR LA CNSC"] == "TRUE"), "Aprobado",
            np.where(
                (df["REALIZADO POR LA FUAA"] == "TRUE") & 
                (df["APROBADO POR LA CNSC"] == "FALSE") & 
                (df["OBSERVACIÓN Y/O STATUS"].str.lower().str.contains("rechaz")),
                "Rechazado",
                np.where(df["REALIZADO POR LA FUAA"] == "TRUE", "Entregado", "Pendiente")
            )
        )

    if modulo == "VRM":
        # Obtener fecha de ayer en zona Bogotá
        tz = timezone("America/Bogota")
        hoy = datetime.now(tz).date()
        fecha_referencia = hoy - timedelta(days=1)

        # Asegurar tipo de fecha
        archivo_metas["FECHA"] = pd.to_datetime(archivo_metas["FECHA"]).dt.date
        archivo_metas["META EQUIPO A LA FECHA"] = (
            pd.to_numeric(
                archivo_metas["META EQUIPO A LA FECHA"].str.replace("-", "0").str.replace(".", ""), 
                errors="coerce"
            ).fillna(0).astype(int)
        )

        # Filtrar metas por fecha
        metas_dia = archivo_metas[archivo_metas["FECHA"] == fecha_referencia]

        # Agrupar por usuario
        metas_usuario = metas_dia.groupby("USUARIO")["META EQUIPO A LA FECHA"].sum().reset_index()
        metas_usuario.rename(columns={"META EQUIPO A LA FECHA": "Meta Proyectada a la Fecha"}, inplace=True)

        # Contar revisiones por usuario desde df VRM
        df["estado_carpeta"] = df["estado_carpeta"].str.lower()
        
        condiciones_estado = [
            df["estado_carpeta"].isin(["calificada", "aprobada", "auditada"]),
            df["estado_carpeta"].isin(["aprobada", "auditada"]),
            df["estado_carpeta"].isin(["auditada"])
        ]
        
        valores_usuario = ["Análisis", "Supervisión", "Auditoría"]
        
        df["USUARIO"] = np.select(condiciones_estado, valores_usuario, default="sin asignación")
        
        condiciones = {
            "Análisis": ["calificada", "aprobada", "auditada"],
            "Supervisión": ["aprobada", "auditada"],
            "Auditoría": ["auditada"]
        }
        
        df_revisiones = df.copy()
        resultados = []

        for usuario in df_revisiones["USUARIO"].unique():
            user_df = df_revisiones[df_revisiones["USUARIO"] == usuario]
            revisadas = user_df["estado_carpeta"].isin(condiciones["Auditoría"]).sum()  # Puedes ajustar a otra vista
            resultados.append({"USUARIO": usuario, "Carpetas Revisadas": revisadas})

        df_revisadas = pd.DataFrame(resultados)

        # Unir metas y revisiones
        resumen = pd.merge(metas_usuario, df_revisadas, on="USUARIO", how="outer").fillna(0)

        resumen["Meta Proyectada a la Fecha"] = (
            pd.to_numeric(resumen["Meta Proyectada a la Fecha"], errors="coerce").fillna(0).astype(int)
        )
        resumen["Carpetas Revisadas"] = (
            pd.to_numeric(resumen["Carpetas Revisadas"], errors="coerce").fillna(0).astype(int)
        )
        resumen["% Avance"] = np.where(
            resumen["Meta Proyectada a la Fecha"] == 0,
            0,
            (resumen["Carpetas Revisadas"] / resumen["Meta Proyectada a la Fecha"] * 100).round(1)
        )

        # Guardar en sesión para usarlo donde se necesite
        st.session_state["df_resumen_vrm"] = resumen

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
st.markdown("<h1 style='text-align:center; font-weight:700; color:#1F9924'>Proceso de Selección INPEC Cuerpo de Custodia y Vigilancia 11</h1>", unsafe_allow_html=True)
st.sidebar.image("assets/Andina_Blanco.png", width=400)

modulos_con_iconos = {
    "Cronograma": "🗓️ Cronograma",
    "Entregables": "✔️ Entregables",
    "VRM": "📊 VRM"
}

mod_actual = st.sidebar.radio(
    "Selecciona módulo:",
    list(modulos_con_iconos.values())
)

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

# Filtros

COLUMNAS_FILTRO = {
    "Cronograma": ["Etapa", "Actividad", "Estado", "Responsable_contractual"],
    "Entregables": ["NO. DE PAGO", "NO. DE ENTREGABLE", "ENTREGABLE", "ESTADO"],
    "VRM": ["estado_carpeta", "numero_opec", "nivel_x", "estado_rm"],
    #"Reclamaciones": ["numero_opec", "nivel_x", "estado_carpeta"]
}

cols_filtro = COLUMNAS_FILTRO.get(mod_actual, [])
filtros = generar_filtros_sidebar(df_base, cols_filtro, mod_actual)
df_filtrado = aplicar_filtros_dinamicos(df_base, filtros)

st.title(f"{mod_actual}")

if mod_actual == "VRM":
    c1, c2, c3, c4 = st.columns(4)

    total = len(df_filtrado)
    ejecutadas = len(df_filtrado[df_filtrado["estado_carpeta"] == "auditada"])
    diferencia = total - ejecutadas
    porcentaje = (ejecutadas / total * 100) if total else 0

    c1.metric("🎯 Meta Proyectada", f"{total:,}".replace(",", "."))
    c2.metric("✔️ Meta Ejecutada", f"{ejecutadas:,}".replace(",", "."))
    c3.metric("↔️ Diferencia", f"{diferencia:,}".replace(",", "."))
    c4.metric("〽️ Porcentaje", f"{porcentaje:.1f}%")

    st.subheader("📈 Avance por Usuario")
    resumen = st.session_state.get("df_resumen_vrm")
    if resumen is not None:
        st.dataframe(resumen, use_container_width=True, hide_index=True)

# Visualizaciones por módulo (fijas)
vis_default = {
    "Cronograma": ["Tabla", "Barras", "Barras"],
    "Entregables": ["Tabla", "Barras", "Anillo"],
    "VRM": ["Tabla", "Embudo", "Anillo"],
    #"Reclamaciones": ["Tabla", "Embudo"]
}.get(mod_actual, ["Tabla"])
vis_seleccionadas = vis_default

# Configuración columnas por módulo
COLUMNAS_TABLA = {
    "Cronograma": ["NO.", "Etapa", "Actividad", "F INICIO P", "F FIN P", "Estado", "Fecha de cumplimiento", "Responsable_contractual"],
    "Entregables": ["NO. DE ENTREGABLE", "NO. DE PAGO", "ENTREGABLE", "ESTADO"],
    "VRM": ["convocatoria", "numero_opec", "nivel_x", "estado_rm", "estado_carpeta"],
    #"Reclamaciones": ["numero_opec", "nivel_x", "estado_carpeta"]
}

COLUMNAS_GRAFICOS = {
    "Cronograma": {"barras": ["Estado", "Etapa"]},
    "Entregables": {"barras": ["ESTADO"], "anillo": "NO. DE PAGO"},
    "VRM": {"anillo": "estado_rm", "embudo": "estado_carpeta"}#,
    #"Reclamaciones": {"barras": "estado_carpeta", "anillo": "estado_carpeta", "embudo": "estado_carpeta"}
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

# === Visualización: EMBUDO ===
if "Embudo" in vis_seleccionadas and "embudo" in cols_graficos:
    grafico_embudo(df_filtrado, columna=cols_graficos["embudo"], titulo=f"Embudo por {cols_graficos['embudo']}")

# === Visualización: ANILLO ===
if "Anillo" in vis_seleccionadas and "anillo" in cols_graficos:
    grafico_anillo(df_filtrado, columna=cols_graficos["anillo"], titulo=f"Distribución por {cols_graficos['anillo']}")
