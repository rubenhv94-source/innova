import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime, date, timedelta
import math
from pytz import timezone


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

@st.cache_data(ttl=600)
def cargar_datos(url: str) -> pd.DataFrame:
    df = pd.read_csv(url, dtype=str)
    for c in ["analista", "supervisor", "auditor", "estado_carpeta", "profesional", "nivel", "EQUIPO"]:
        if c in df.columns:
            df[c] = df[c].fillna("").str.strip()
    return df

df = cargar_datos(CSV_URL)

METAS_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQVxG-bO1D5mkgUFCU35drRV4tyXT9aRaW6q4zzWGa9nFAqkLVdZxaIjwD1cEMJIAXuI4xTBlhHS1og/pub?gid=1199329439&single=true&output=csv"  # <-- Pega aquí la URL real

@st.cache_data(ttl=600)
def cargar_metas(url: str) -> pd.DataFrame:
    df = pd.read_csv(url, dtype=str)
    df.columns = df.columns.str.strip()
    
    # Limpieza de columnas numéricas
    for col in ["META EQUIPO A LA FECHA", "META DIARIA", "META DIARIA A LA FECHA", "META DIARIA EQUIPO"]:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.replace("-", "0")
                .str.replace(".", "", regex=False)
                .str.replace(",", "", regex=False)
                .fillna("0")
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    
    # Fecha como datetime.date
    if "FECHA" in df.columns:
        df["FECHA"] = pd.to_datetime(df["FECHA"].astype(str).str.strip(), errors="coerce").dt.date

    return df

archivo_metas = cargar_metas(METAS_CSV_URL)

# ============ UTILIDADES ============

# Estados estandarizados
ESTADOS_ORDEN = ["asignada", "devuelta", "calificada", "aprobada", "auditada"]
ESTADOS_RENOM = {
    "asignada": "Asignada",
    "devuelta": "Devuelta",
    "calificada": "Calificada",
    "aprobada": "Aprobada",
    "auditada": "Auditada"
}

def obtener_fecha_corte_valida(archivo_metas: pd.DataFrame) -> date | None:
    # Convertir FECHA a datetime.date
    archivo_metas = archivo_metas.copy()
    archivo_metas["FECHA"] = pd.to_datetime(archivo_metas["FECHA"], errors="coerce").dt.date

    hoy = datetime.now(timezone("America/Bogota")).date()

    # Filtrar solo fechas <= hoy
    fechas_validas = archivo_metas[archivo_metas["FECHA"] <= hoy]["FECHA"]

    if fechas_validas.empty:
        return None  # No hay datos válidos

    return fechas_validas.max()  # La última disponible

def limpiar_datos_por_modulo(df: pd.DataFrame, archivo_metas: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    archivo_metas = archivo_metas.copy()

    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()

    # === Fecha de referencia ===
    tz = timezone("America/Bogota")
    hoy = datetime.now(tz).date()
    fecha_referencia = obtener_fecha_corte_valida(archivo_metas)

    # === Asegurar consistencia en FECHA ===
    archivo_metas["FECHA"] = pd.to_datetime(archivo_metas["FECHA"], errors="coerce").dt.date
    metas_dia = archivo_metas[archivo_metas["FECHA"] == fecha_referencia]

    # === Agrupar metas por ROL ===
    metas_usuario = (
        metas_dia.groupby("CLAS")["META EQUIPO A LA FECHA"]
        .sum()
        .reset_index()
        .rename(columns={
            "CLAS": "ROL",
            "META EQUIPO A LA FECHA": "Meta Proyectada a la Fecha"
        })
    )

    # === Normalizar estado en df principal ===
    df["estado_carpeta"] = df["estado_carpeta"].str.lower().fillna("")

    condiciones = {
        "Análisis": ["calificada", "aprobada", "auditada"],
        "Supervisión": ["aprobada", "auditada"],
        "Auditoria": ["auditada"]
    }

    resultados = []
    for rol, estados in condiciones.items():
        revisadas = df["estado_carpeta"].isin(estados).sum()
        resultados.append({
            "ROL": rol,
            "Carpetas Revisadas": revisadas
        })

    df_revisadas = pd.DataFrame(resultados)

    # === Fusionar metas + revisadas ===
    resumen = pd.merge(metas_usuario, df_revisadas, on="ROL", how="outer").fillna(0)

    resumen["Meta Proyectada a la Fecha"] = pd.to_numeric(resumen["Meta Proyectada a la Fecha"], errors="coerce").fillna(0)
    resumen["Carpetas Revisadas"] = pd.to_numeric(resumen["Carpetas Revisadas"], errors="coerce").fillna(0)

    resumen["% Avance"] = np.where(
        resumen["Meta Proyectada a la Fecha"] == 0,
        0,
        (resumen["Carpetas Revisadas"] / resumen["Meta Proyectada a la Fecha"] * 100).round(2),
    )

    # Guardar en sesión
    st.session_state["df_resumen_vrm"] = resumen

    return resumen

def sujetos_col(modulo: str) -> str:
    return {"Analistas": "analista", "Supervisores": "supervisor", "Equipos": "auditor"}[modulo]

def estados_validos(modulo: str) -> list[str]:
    if modulo == "Analistas":
        return ["auditada", "aprobada", "calificada"]
    if modulo == "Supervisores":
        return ["auditada", "aprobada"]        
    return ["auditada"]

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

# ============ GRAFICOS ============

def grafico_avance_total(total: int, avance: int, meta: int):
    if meta <= 0:
        porcentaje = 0
    else:
        porcentaje = min((avance / meta) * 100, 150)  # Limita al 150% por estética

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=porcentaje,
        number={"suffix": "%"},
        title={"text": "<b>Avance total</b>"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#1F9924"},
            "steps": [
                {"range": [0, 50], "color": "#e8f5e9"},
                {"range": [50, 100], "color": "#c8e6c9"}
            ],
            "threshold": {
                "line": {"color": "red", "width": 3},
                "thickness": 0.75,
                "value": 100
            }
        }
    ))

    fig.update_layout(
        height=300,
        margin=dict(t=40, b=20, l=20, r=20)
    )

    return fig

def grafico_estado_con_meta(df_mod: pd.DataFrame, modulo: str, meta_total: int = 0):
    if "estado_carpeta" not in df_mod.columns:
        return px.bar(title="<b>Sin datos para mostrar</b>")

    # Recuento por estado estandarizado
    conteo = (
        df_mod["estado_carpeta"]
        .fillna("")
        .str.lower()
        .map(ESTADOS_RENOM)
        .value_counts()
        .reindex(
            [ESTADOS_RENOM.get(e, e) for e in ["asignada", "devuelta", "calificada", "aprobada", "auditada", "Por asignar"]],
            fill_value=0
        )
        .reset_index()
    )

    conteo.columns = ["estado_carpeta", "cantidad"]
    total = conteo["cantidad"].sum()

    if total == 0:
        return px.bar(title="<b>Sin datos para mostrar</b>")

    # Porcentajes y etiquetas
    conteo["porcentaje"] = (conteo["cantidad"] / total * 100).round(1)
    conteo["label"] = conteo["cantidad"].astype(str) + " (" + conteo["porcentaje"].astype(str) + "%)"

    # Gráfico base
    fig = px.bar(
        conteo,
        x="estado_carpeta",
        y="cantidad",
        color="estado_carpeta",
        color_discrete_sequence=COLOR_PALETTE,
        text="label",
        title=f"<b>Distribución por estado — {modulo}</b>",
    )

    # Meta como línea horizontal
    if meta_total > 0:
        fig.add_scatter(
            x=conteo["estado_carpeta"],
            y=[meta_total] * len(conteo),
            mode="lines",
            name="Meta acumulada",
            line=dict(color="#007BFF", width=2, dash="dash"),
        )

        fig.add_annotation(
            text=f"<b>Meta: {meta_total:,.0f}</b>".replace(",", "X").replace(".", ",").replace("X", "."),
            xref="paper", yref="paper",
            x=0.98, y=1.05,
            showarrow=False,
            font=dict(size=13, color="#007BFF", family="Arial"),
            align="right",
        )

    # Layout final
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

def grafico_avance_por_rol(df_resumen: pd.DataFrame, rol: str):
    # Validar existencia de ROL
    if df_resumen.empty or "ROL" not in df_resumen.columns:
        return go.Figure()

    row = df_resumen[df_resumen["ROL"] == rol]
    if row.empty:
        return go.Figure()

    # Extraer valores con tolerancia a errores
    meta = pd.to_numeric(row["Meta Proyectada a la Fecha"].values[0], errors="coerce") or 0
    revisadas = pd.to_numeric(row["Carpetas Revisadas"].values[0], errors="coerce") or 0
    porcentaje = pd.to_numeric(row["% Avance"].values[0], errors="coerce") or 0.0

    # Asegurar que porcentaje esté en rango válido
    porcentaje = min(max(porcentaje, 0), 150)

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=porcentaje,
        delta={
            "reference": 100,
            "increasing": {"color": "red"},
            "decreasing": {"color": "green"},
        },
        title={"text": f"<b>Avance — {rol}</b><br><span style='font-size:12px'>({revisadas:,} de {meta:,})</span>"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#1F9924"},
            "steps": [
                {"range": [0, 50], "color": "#e8f5e9"},
                {"range": [50, 100], "color": "#c8e6c9"},
            ],
        },
        domain={'x': [0, 1], 'y': [0, 1]}
    ))

    fig.update_layout(
        height=320,
        margin=dict(t=50, b=30, l=30, r=30),
        font=dict(family="Arial", size=12),
    )

    return fig

def grafico_categorias_barh(df_mod: pd.DataFrame, modulo: str, archivo_metas: pd.DataFrame):
    col = sujetos_col(modulo)
    if df_mod.empty or col not in df_mod.columns:
        return px.bar(title="<b>Sin datos para mostrar</b>")

    # === Fecha de corte válida ===
    fecha_ref = obtener_fecha_corte_valida(archivo_metas)

    # === Revisadas por persona ===
    estados = estados_validos(modulo)
    df_ok = df_mod[df_mod["estado_carpeta"].str.lower().isin(estados)]
    desarrolladas = (
        df_ok.groupby(col)
        .size()
        .reset_index(name="revisadas")
    )

    # === Metas por persona ===
    archivo_metas = archivo_metas.copy()
    archivo_metas["FECHA"] = pd.to_datetime(archivo_metas["FECHA"], errors="coerce").dt.date

    # Determinar CLAS correcta según módulo
    rol_map = {"Analistas": "Análisis", "Supervisores": "Supervisión", "Equipos": "Auditoria"}
    clas = rol_map.get(modulo, "").strip()
    
    metas_dia = archivo_metas[(archivo_metas["FECHA"] == fecha_ref) & (archivo_metas["USUARIO"].str.strip() == clas)]

    if metas_dia.empty or "META DIARIA A LA FECHA" not in metas_dia.columns:
        return px.bar(title=f"<b>Sin metas para {clas}</b>")

    metas_sujeto = (
        metas_dia
        .groupby("USUARIO")["META DIARIA A LA FECHA"]
        .sum()
        .reset_index()
        .rename(columns={
            "USUARIO": col,
            "META DIARIA A LA FECHA": "meta"
        })
    )
    metas_sujeto["meta"] = pd.to_numeric(metas_sujeto["meta"], errors="coerce").fillna(0).astype(int)

    # === Unión metas + desarrolladas ===
    df = pd.merge(desarrolladas, metas_sujeto, on=col, how="left").fillna(0)
    df["revisadas"] = pd.to_numeric(df["revisadas"], errors="coerce").fillna(0).astype(int)
    df["atraso"] = df["meta"] - df["revisadas"]
    df["categoria"] = df["atraso"].apply(lambda x: clasifica_categoria(int(x), modulo))

    # === Conteo por categoría ===
    cat_count = df.groupby("categoria").size().reset_index(name="cantidad")
    orden = ["Al día", "Atraso normal", "Atraso medio", "Atraso alto"]
    cat_count["categoria"] = pd.Categorical(cat_count["categoria"], categories=orden, ordered=True)
    cat_count = cat_count.sort_values("categoria")

    # === Gráfico ===
    fig = px.bar(
        cat_count,
        x="cantidad",
        y="categoria",
        orientation="h",
        color="categoria",
        color_discrete_sequence=COLOR_PALETTE,
        title=f"<b>Cantidad por seguimiento individual — {modulo}</b>",
        text_auto=True,
    )

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

def tabla_resumen(df_mod: pd.DataFrame, modulo: str, archivo_metas: pd.DataFrame) -> pd.DataFrame:
    col = sujetos_col(modulo)

    # Validación inicial
    if df_mod.empty or col not in df_mod.columns:
        st.warning(f"No se encontró la columna esperada '{col}' para el módulo '{modulo}'.")
        return pd.DataFrame(columns=["Categoria", col.capitalize(), "Analizadas", "Meta", "Faltantes"])

    # Estados válidos
    estados_efectivos = set(estados_validos(modulo))

    # Fecha de corte válida
    fecha_ref = obtener_fecha_corte_valida(archivo_metas)

    # Preprocesar archivo de metas
    archivo_metas = archivo_metas.copy()
    archivo_metas["FECHA"] = pd.to_datetime(archivo_metas["FECHA"], errors="coerce").dt.date
    archivo_metas["USUARIO"] = archivo_metas["USUARIO"].astype(str).str.strip().str.lower()

    rol_map = {"Analistas": "análisis", "Supervisores": "supervisión", "Equipos": "auditoria"}
    clas = rol_map.get(modulo, "").strip().lower()

    metas_dia = archivo_metas[
        (archivo_metas["FECHA"] == fecha_ref) &
        (archivo_metas["USUARIO"].str.lower() == clas)
    ].copy()

    # === LIMPIEZA NUMÉRICA ===
    if "META DIARIA A LA FECHA" in metas_dia.columns:
        metas_dia["META DIARIA A LA FECHA"] = pd.to_numeric(
            metas_dia["META DIARIA A LA FECHA"]
            .astype(str)
        )

    # === Limpieza del DF principal ===
    df_mod = df_mod.dropna(subset=["estado_carpeta", col])
    df_mod["estado_carpeta"] = df_mod["estado_carpeta"].str.strip().str.lower()

    # Agrupación de estados
    pivot = (
        df_mod
        .groupby([col, "estado_carpeta"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    for estado in ESTADOS_ORDEN:
        if estado not in pivot.columns:
            pivot[estado] = 0

    pivot["Analizadas"] = pivot[[e for e in ESTADOS_ORDEN if e in estados_efectivos]].sum(axis=1)

    # ============================
    # META desde archivo de metas (agregada por módulo)
    # ============================
    if metas_dia.empty or "META DIARIA A LA FECHA" not in metas_dia.columns:
        st.warning(f"No hay metas disponibles para '{clas}' en la fecha {fecha_ref}.")
        pivot["Meta"] = 0
    else:
        total_meta = metas_dia["META DIARIA A LA FECHA"].sum()
        pivot["Meta"] = total_meta  # Asigna la misma meta a todos los sujetos
        pivot["Meta"] = pivot["Meta"].astype(int)

    # Faltantes y clasificación
    pivot["Faltantes"] = pivot["Meta"] - pivot["Analizadas"]
    pivot["Categoria"] = pivot["Faltantes"].apply(lambda x: clasifica_categoria(int(x), modulo))

    # Orden final
    columnas_estado = ESTADOS_ORDEN
    out = pivot[[col] + columnas_estado + ["Analizadas", "Meta", "Faltantes", "Categoria"]]

    categorias = ["Al día", "Atraso normal", "Atraso medio", "Atraso alto"]
    out["Categoria"] = pd.Categorical(out["Categoria"], categories=categorias, ordered=True)

    out = out.sort_values(["Categoria", col], ascending=[True, True])
    out = out.rename(columns={col: col.capitalize(), **{e: ESTADOS_RENOM.get(e, e) for e in columnas_estado}})

    return out

def grafico_estado_supervisor(df: pd.DataFrame):
    # Validaciones mínimas
    if "EQUIPO_NUM" not in df.columns or "supervisor" not in df.columns or "estado_carpeta" not in df.columns:
        st.warning("Faltan columnas necesarias para graficar vista de Supervisor.")
        return go.Figure()

    # Mapeo de supervisor por equipo
    sup_info = (
        df[["EQUIPO_NUM", "supervisor"]]
        .dropna()
        .drop_duplicates()
        .groupby("EQUIPO_NUM")["supervisor"]
        .agg(lambda x: ', '.join(sorted(x.unique())))
        .to_dict()
    )

    df["supervisor"] = df["EQUIPO_NUM"].map(sup_info)
    df["estado_label"] = df["estado_carpeta"].map(ESTADOS_RENOM).fillna("Otro")

    df["estado_label"] = pd.Categorical(
        df["estado_label"],
        categories=[ESTADOS_RENOM.get(e, e) for e in ESTADOS_ORDEN],
        ordered=True
    )

    # Agrupar
    grp = (
        df.groupby(["EQUIPO_NUM", "estado_label", "supervisor"])
        .size()
        .reset_index(name="cantidad")
    )

    # Validación si no hay datos
    if grp.empty:
        return px.bar(title="<b>Sin datos válidos para mostrar</b>")

    fig = go.Figure()

    for estado in [ESTADOS_RENOM.get(e, e) for e in ESTADOS_ORDEN]:
        subset = grp[grp["estado_label"] == estado]
        fig.add_trace(
            go.Bar(
                x=subset["EQUIPO_NUM"],
                y=subset["cantidad"],
                name=estado,
                customdata=np.stack([
                    subset["EQUIPO_NUM"],
                    subset["supervisor"],
                    subset["estado_label"]
                ], axis=-1),
                hovertemplate="<b>Equipo:</b> %{customdata[0]}<br>"
                              "<b>Supervisor:</b> %{customdata[1]}<br>"
                              "<b>Estado:</b> %{customdata[2]}<br>"
                              "<b>Cantidad:</b> %{y}<extra></extra>",
            )
        )

    fig.update_layout(
        barmode="stack",
        title="<b>Estados por EQUIPO — Vista: Supervisor</b>",
        xaxis_title="Equipo",
        yaxis=dict(title="Cantidad", range=[0, grp["cantidad"].max() + 20]),
        font=dict(family="Arial", size=12),
        title_font=dict(size=18, color="#1F9924", family="Arial"),
        plot_bgcolor="white",
        legend_title_text="Estado",
        height=500,
        margin=dict(l=30, r=30, t=60, b=70),
        bargap=0.2,
        colorway=COLOR_PALETTE
    )

    return fig

def grafico_estado_analistas(df: pd.DataFrame):
    # Validación mínima
    required_cols = {"EQUIPO_NUM", "analista", "estado_carpeta"}
    if not required_cols.issubset(df.columns):
        st.warning("Faltan columnas necesarias para la vista de Analistas.")
        return go.Figure()

    # Asignar rol por analista en equipo
    analistas_unicos = (
        df[["EQUIPO_NUM", "analista"]]
        .dropna()
        .drop_duplicates()
        .sort_values(["EQUIPO_NUM", "analista"])
    )
    analistas_unicos["rol"] = analistas_unicos.groupby("EQUIPO_NUM").cumcount() + 1
    analistas_unicos["rol"] = "A" + analistas_unicos["rol"].astype(str)

    # Merge para agregar rol
    df = df.merge(analistas_unicos, on=["EQUIPO_NUM", "analista"], how="left")
    df["equipo_rol"] = df["EQUIPO_NUM"].astype(str) + " " + df["rol"]

    # Homologar estados
    df["estado_homol"] = df["estado_carpeta"].str.lower().map(ESTADOS_RENOM).fillna("Otro")

    # Agrupar
    grouped = (
        df.groupby(["EQUIPO_NUM", "analista", "equipo_rol", "estado_homol"])
        .size()
        .reset_index(name="cantidad")
    )

    # Pivotar para formato de gráfico
    pivot = grouped.pivot_table(
        index=["EQUIPO_NUM", "analista", "equipo_rol"],
        columns="estado_homol",
        values="cantidad",
        fill_value=0
    ).reset_index()

    estado_cols = [col for col in pivot.columns if col not in ["EQUIPO_NUM", "analista", "equipo_rol"]]

    # Crear gráfico
    fig = go.Figure()

    for estado in estado_cols:
        fig.add_trace(
            go.Bar(
                x=pivot["equipo_rol"],
                y=pivot[estado],
                name=estado,
                customdata=np.stack([
                    pivot["analista"],
                    [estado] * len(pivot),
                    pivot[estado]
                ], axis=-1),
                hovertemplate="<b>Analista:</b> %{customdata[0]}<br>"
                              "<b>Estado:</b> %{customdata[1]}<br>"
                              "<b>Cantidad:</b> %{customdata[2]}<extra></extra>",
            )
        )

    fig.update_layout(
        barmode="stack",
        title="<b>Estados por EQUIPO — Vista: Analistas</b>",
        xaxis_title="Equipo",
        yaxis=dict(title="Cantidad", range=[0, pivot[estado_cols].sum(axis=1).max() + 20]),
        font=dict(family="Arial", size=12),
        title_font=dict(size=18, color="#1F9924", family="Arial"),
        plot_bgcolor="white",
        legend_title_text="Estado",
        height=500,
        margin=dict(l=30, r=30, t=60, b=70),
        bargap=0.4,
        colorway=COLOR_PALETTE,
        xaxis=dict(
            tickmode="array",
            tickvals=pivot["equipo_rol"],
            ticktext=pivot["EQUIPO_NUM"].astype(str)
        )
    )

    return fig

# ---------- UTILIDADES de categorías globales (con metas reales) ----------

def categorias_por_sujeto(df_base: pd.DataFrame, archivo_metas: pd.DataFrame, modulo: str) -> pd.DataFrame:
    """
    Retorna un DataFrame con:
    - Sujeto (analista / supervisor / auditor)
    - Categoria ("Al día", "Atraso normal", etc)
    - EQUIPO
    - Modulo (Analistas, Supervisores, Equipos)
    """

    dfm = prepara_df_modulo(df_base, modulo)
    col_sujeto = sujetos_col(modulo)

    if col_sujeto not in dfm.columns:
        return pd.DataFrame(columns=["Sujeto", "Categoria", "EQUIPO", "Modulo"])

    # ======================
    # Revisadas por sujeto
    # ======================
    estados = estados_validos(modulo)
    dfm["estado_carpeta"] = dfm["estado_carpeta"].str.lower().fillna("")
    revisadas = (
        dfm[dfm["estado_carpeta"].isin(estados)]
        .groupby(col_sujeto)
        .size()
        .reset_index(name="revisadas")
    )

    # ============================
    # Metas reales por sujeto
    # ============================
    archivo_metas = archivo_metas.copy()
    archivo_metas["FECHA"] = pd.to_datetime(archivo_metas["FECHA"], errors="coerce").dt.date
    archivo_metas["USUARIO"] = archivo_metas["USUARIO"].astype(str).str.strip()
    dfm[col_sujeto] = dfm[col_sujeto].astype(str).str.strip()

    fecha_ref = obtener_fecha_corte_valida(archivo_metas)
    metas_dia = archivo_metas[archivo_metas["FECHA"] == fecha_ref]

    if "USUARIO" not in metas_dia.columns:
        return pd.DataFrame(columns=["Sujeto", "Categoria", "EQUIPO", "Modulo"])

    metas_sujeto = (
        metas_dia.groupby("USUARIO")["META DIARIA A LA FECHA"]
        .sum()
        .reset_index()
        .rename(columns={"USUARIO": col_sujeto, "META DIARIA A LA FECHA": "meta_sujeto"})
    )

    # ======================
    # Unión y clasificación
    # ======================
    resumen = pd.merge(revisadas, metas_sujeto, on=col_sujeto, how="left").fillna(0)
    resumen["faltantes"] = resumen["meta_sujeto"] - resumen["revisadas"]
    resumen["Categoria"] = resumen["faltantes"].apply(lambda x: clasifica_categoria(int(x), modulo))

    # ======================
    # Asociar equipo
    # ======================
    equipo_map = df_base[[col_sujeto, "EQUIPO"]].drop_duplicates()
    equipo_map[col_sujeto] = equipo_map[col_sujeto].astype(str).str.strip()
    resumen = resumen.merge(equipo_map, on=col_sujeto, how="left")

    resumen["Modulo"] = modulo
    resumen = resumen.rename(columns={col_sujeto: "Sujeto"})

    return resumen[["Sujeto", "Categoria", "EQUIPO", "Modulo"]]

def aplicar_filtro_categoria_transversal(df_in: pd.DataFrame, categoria_sel: str,
                                         cat_analistas: pd.DataFrame,
                                         cat_supervisores: pd.DataFrame,
                                         cat_equipos: pd.DataFrame) -> pd.DataFrame:
    if categoria_sel in (None, "", "Todos"):
        return df_in

    out = df_in.copy()

    # Asegurar consistencia de claves para merge
    for col in ["analista", "supervisor", "auditor"]:
        if col in out.columns:
            out[col] = out[col].astype(str).str.strip()

    if not cat_analistas.empty and "analista" in out.columns:
        cat_analistas["Sujeto"] = cat_analistas["Sujeto"].astype(str).str.strip()
        out = out.merge(
            cat_analistas[["Sujeto", "Categoria"]].rename(columns={"Sujeto": "analista", "Categoria": "cat_analista"}),
            on="analista", how="left"
        )
    if not cat_supervisores.empty and "supervisor" in out.columns:
        cat_supervisores["Sujeto"] = cat_supervisores["Sujeto"].astype(str).str.strip()
        out = out.merge(
            cat_supervisores[["Sujeto", "Categoria"]].rename(columns={"Sujeto": "supervisor", "Categoria": "cat_supervisor"}),
            on="supervisor", how="left"
        )
    if not cat_equipos.empty and "auditor" in out.columns:
        cat_equipos["Sujeto"] = cat_equipos["Sujeto"].astype(str).str.strip()
        out = out.merge(
            cat_equipos[["Sujeto", "Categoria"]].rename(columns={"Sujeto": "auditor", "Categoria": "cat_auditor"}),
            on="auditor", how="left"
        )

    # Crear columna global combinada
    out["categoria_global"] = (
        out.get("cat_analista")
        .combine_first(out.get("cat_supervisor"))
        .combine_first(out.get("cat_auditor"))
    )

    return out[out["categoria_global"] == categoria_sel].copy()

# ============ NAVEGACIÓN ============

SECCIONES_DISPONIBLES = ["Inicio", "Resumen", "Analistas", "Supervisores", "Equipos"]

pagina_param = st.query_params.get("pagina", "Inicio")
pagina_actual = pagina_param if pagina_param in SECCIONES_DISPONIBLES else "Inicio"
st.session_state.pagina = st.session_state.get("pagina", pagina_actual)

seleccion = st.sidebar.radio(
    "Ir a la sección:",
    SECCIONES_DISPONIBLES,
    index=SECCIONES_DISPONIBLES.index(st.session_state.pagina),
    key="nav_radio"
)

if seleccion != st.session_state.pagina:
    st.session_state.pagina = seleccion
    st.query_params["pagina"] = seleccion
    st.rerun()

# ============ SIDEBAR FILTROS (persistentes) ============
with st.sidebar:
    st.header("🔎 Filtros")

    # 🔄 Botón para recargar datos desde Google Sheets (limpia la caché)
    if st.button("🔄 Recargar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Inicializar estados si no existen
    for k in ["sel_prof", "sel_sup", "sel_ana", "sel_estado", "sel_nivel", "sel_categoria"]:
        if k not in st.session_state:
            st.session_state[k] = "Todos"

    # 🧹 Botón para limpiar filtros sin cambiar de página
    if st.button("🧹 Borrar filtros", use_container_width=True):
        for k in ["sel_prof", "sel_sup", "sel_ana", "sel_estado", "sel_nivel", "sel_categoria"]:
            st.session_state[k] = "Todos"
        st.rerun()

    # Filtros dependientes (cascada)
    df_temp = df.copy()
    if st.session_state.sel_prof != "Todos":
        df_temp = df_temp[df_temp["auditor"] == st.session_state.sel_prof]
    if st.session_state.sel_sup != "Todos":
        df_temp = df_temp[df_temp["supervisor"] == st.session_state.sel_sup]
    if st.session_state.sel_ana != "Todos":
        df_temp = df_temp[df_temp["analista"] == st.session_state.sel_ana]

    # Opciones para selectboxes según datos filtrados
    opciones_prof = ["Todos"] + sorted(df_temp["auditor"].dropna().unique())
    opciones_sup = ["Todos"] + sorted(df_temp["supervisor"].dropna().unique())
    opciones_ana = ["Todos"] + sorted(df_temp["analista"].dropna().unique())
    opciones_estado = ["Todos"] + sorted(set(df["estado_carpeta"].str.lower().dropna().unique()) | {""})
    opciones_nivel = ["Todos"] + sorted(df_temp["nivel"].dropna().unique()) if "nivel" in df_temp.columns else ["Todos"]

    # Mostrar filtros
    st.selectbox("👩‍💼 Profesional", opciones_prof,
                 index=opciones_prof.index(st.session_state.sel_prof) if st.session_state.sel_prof in opciones_prof else 0,
                 key="sel_prof")
    st.selectbox("🕵️‍♀️ Supervisor", opciones_sup,
                 index=opciones_sup.index(st.session_state.sel_sup) if st.session_state.sel_sup in opciones_sup else 0,
                 key="sel_sup")
    st.selectbox("👨‍💻 Analista", opciones_ana,
                 index=opciones_ana.index(st.session_state.sel_ana) if st.session_state.sel_ana in opciones_ana else 0,
                 key="sel_ana")
    st.selectbox("📤 Estado", opciones_estado,
                 index=opciones_estado.index(st.session_state.sel_estado) if st.session_state.sel_estado in opciones_estado else 0,
                 key="sel_estado")
    st.selectbox("🔹 Nivel", opciones_nivel,
                 index=opciones_nivel.index(st.session_state.sel_nivel) if st.session_state.sel_nivel in opciones_nivel else 0,
                 key="sel_nivel")

    # 🔄 Categoría de desempeño individual (con metas reales)
    df_filtro_prev = df_temp.copy()  # ya contiene filtros previos

    cat_ana_sub = categorias_por_sujeto(df_filtro_prev, archivo_metas, "Analistas")
    cat_sup_sub = categorias_por_sujeto(df_filtro_prev, archivo_metas, "Supervisores")
    cat_equ_sub = categorias_por_sujeto(df_filtro_prev, archivo_metas, "Equipos")

    categorias_disponibles = pd.concat([
        cat_ana_sub["Categoria"],
        cat_sup_sub["Categoria"],
        cat_equ_sub["Categoria"]
    ]).dropna().unique().tolist()

    orden_categorias = ["Al día", "Atraso normal", "Atraso medio", "Atraso alto"]
    opciones_categoria = ["Todos"] + [cat for cat in orden_categorias if cat in categorias_disponibles]

    st.selectbox("🏷️ Categoría", opciones_categoria,
                 index=opciones_categoria.index(st.session_state.sel_categoria) if st.session_state.sel_categoria in opciones_categoria else 0,
                 key="sel_categoria")

# ========= Preparar categorías por sujeto (para filtro transversal global) =========
cat_analistas_df = categorias_por_sujeto(df, archivo_metas, "Analistas")
cat_supervisores_df = categorias_por_sujeto(df, archivo_metas, "Supervisores")
cat_equipos_df = categorias_por_sujeto(df, archivo_metas, "Equipos")

# ========= Aplicar filtros al DataFrame principal =========
df_filtrado = df.copy()

if st.session_state.sel_prof != "Todos":
    df_filtrado = df_filtrado[df_filtrado["auditor"] == st.session_state.sel_prof]
if st.session_state.sel_sup != "Todos":
    df_filtrado = df_filtrado[df_filtrado["supervisor"] == st.session_state.sel_sup]
if st.session_state.sel_ana != "Todos":
    df_filtrado = df_filtrado[df_filtrado["analista"] == st.session_state.sel_ana]
if st.session_state.sel_estado != "Todos":
    df_filtrado = df_filtrado[df_filtrado["estado_carpeta"].str.lower() == st.session_state.sel_estado.lower()]
if st.session_state.sel_nivel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["nivel"] == st.session_state.sel_nivel]

# ➕ Filtro por categoría (transversal)
df_filtrado = aplicar_filtro_categoria_transversal(
    df_filtrado,
    st.session_state.sel_categoria,
    cat_analistas_df,
    cat_supervisores_df,
    cat_equipos_df
)

# ============ INICIO ============
if st.session_state.pagina == "Inicio":
    c1, c2, c3 = st.columns([1, 1, 1])

    with c1:
        st.image("assets/Logp GP FUAA.png", use_container_width=True)
    with c2:
        st.empty()
    with c3:
        st.image("assets/Andina.png", width=200)

    st.markdown(
        "<h1 style='text-align:center; font-weight:700; color:#1F9924'>"
        "Seguimiento de Metas VA DIAN 2667"
        "</h1>", unsafe_allow_html=True
    )

    st.markdown("---")

    col_left, col_center, col_right = st.columns([1, 1, 1])

    with col_left:
        st.write("")  # Espacio
        # Mapeo de botones a secciones
        botones = {
            "Resumen": "Resumen",
            "Analistas": "Analistas",
            "Supervisores": "Supervisores",
            "Equipos": "Equipos"
        }

        for label, pagina in botones.items():
            if st.button(label, key=f"btn_home_{pagina.lower()}"):
                st.session_state.pagina = pagina
                st.query_params["pagina"] = pagina
                st.rerun()

    with col_center:
        st.image("assets/Logo Tablero.jpg", use_container_width=True)

    with col_right:
        st.empty()

# ============ RESUMEN ============
if st.session_state.pagina == "Resumen":
    st.markdown(f"<h1 style='color:#1F9924;'>Resumen general</h1>", unsafe_allow_html=True)

    # Fecha de corte = ayer
    tz = timezone("America/Bogota")
    fecha_corte = obtener_fecha_corte_valida(archivo_metas)
    st.info(f"Fecha de corte: **{fecha_corte}**")

    # Métricas clave
    por_asignar = df_filtrado["estado_carpeta"].fillna("").eq("").sum()
    equipo_va = df_filtrado["analista"].nunique() + df_filtrado["supervisor"].nunique()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📂 Total carpetas", f"{len(df_filtrado):,}".replace(",", "."))
    col2.metric("✔️ Auditadas", f"{(df_filtrado['estado_carpeta'].str.lower() == 'auditada').sum():,}".replace(",", "."))
    col3.metric("👨‍👧‍👧 Equipo VA", f"{equipo_va:,}".replace(",", "."))
    col4.metric("📌 Por asignar", f"{por_asignar:,}".replace(",", "."))

    # =======================
    # 📊 Indicador de avance
    # =======================
    avance = df_filtrado["estado_carpeta"].str.lower().isin(["auditada"]).sum()
    total = len(df_filtrado)

    # 📈 Meta global real desde archivo de metas
    metas_corte = archivo_metas[archivo_metas["FECHA"] == fecha_corte]
    meta_total = metas_corte["META EQUIPO A LA FECHA"].sum()

    fig_gauge = grafico_avance_total(total, avance, meta_total)
    st.plotly_chart(fig_gauge, use_container_width=True)

    # ================================
    # 📊 Gráfico por estado + meta
    # ================================
    fig_estado = grafico_estado_con_meta(df_filtrado, "Supervisores", meta_total)
    st.plotly_chart(fig_estado, use_container_width=True)

# ============ VISTA MÓDULOS ============
def modulo_vista(nombre_modulo: str, archivo_metas: pd.DataFrame):
    st.markdown(f"<h1 style='color:#1F9924;'>{nombre_modulo}</h1>", unsafe_allow_html=True)
    dfm = prepara_df_modulo(df_filtrado, nombre_modulo)

    # === Mapear nombre del módulo a USUARIO en metas ===
    rol_map = {
        "Analistas": "Análisis",
        "Supervisores": "Supervisión",
        "Equipos": "Auditoria"
    }
    rol_usuario = rol_map.get(nombre_modulo, "")

    # === Preparar archivo metas ===
    archivo_metas = archivo_metas.copy()
    archivo_metas["FECHA"] = pd.to_datetime(archivo_metas["FECHA"], errors="coerce").dt.date
    archivo_metas["USUARIO"] = archivo_metas["USUARIO"].astype(str).str.strip().str.title()

    # === Obtener fecha válida (última si no hay de hoy) ===
    fecha_corte = obtener_fecha_corte_valida(archivo_metas)
    st.info(f"Fecha de corte: **{fecha_corte}**")

    # === Filtrar metas para rol y fecha ===
    metas_rol_fecha = archivo_metas[
        (archivo_metas["FECHA"] == fecha_corte) &
        (archivo_metas["USUARIO"] == rol_usuario)
    ]

    meta_total = metas_rol_fecha["META EQUIPO A LA FECHA"].sum() if "META EQUIPO A LA FECHA" in metas_rol_fecha.columns else 0

    # === Carpeta desarrolladas válidas ===
    validos = estados_validos(nombre_modulo)
    desarrolladas_total = dfm["estado_carpeta"].str.lower().isin(validos).sum() if "estado_carpeta" in dfm.columns else 0
    diferencia_total = desarrolladas_total - meta_total

    # === Mostrar métricas ===
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📂 Total carpetas", f"{len(dfm):,}".replace(",", "."))
    c2.metric("✔️ Desarrolladas", f"{desarrolladas_total:,}".replace(",", "."))
    c3.metric("🎯 Meta a la fecha", f"{meta_total:,}".replace(",", "."))
    c4.metric("⚠️ Diferencia", f"{diferencia_total:,}".replace(",", "."))

    # ===================== CONTEXTO FILTRADO =====================
    analistas_filtrados = sorted(df_filtrado["analista"].dropna().unique()) if "analista" in df_filtrado.columns else []
    supervisores_filtrados = sorted(df_filtrado["supervisor"].dropna().unique()) if "supervisor" in df_filtrado.columns else []
    auditores_filtrados = sorted(df_filtrado["auditor"].dropna().unique()) if "auditor" in df_filtrado.columns else []
    equipos_filtrados = sorted(df_filtrado["EQUIPO"].dropna().unique()) if "EQUIPO" in df_filtrado.columns else []

    analista_label_1, analista_label_2 = ("No disponible", "") if not analistas_filtrados else (
        (analistas_filtrados[0], "") if len(analistas_filtrados) == 1 else
        (analistas_filtrados[0], analistas_filtrados[1]) if len(analistas_filtrados) == 2 else
        ("Varios", "Varios")
    )

    supervisor_label = (
        "No disponible" if not supervisores_filtrados else
        supervisores_filtrados[0] if len(supervisores_filtrados) == 1 else
        "Varios"
    )

    auditor_label = (
        "No disponible" if not auditores_filtrados else
        auditores_filtrados[0] if len(auditores_filtrados) == 1 else
        "Varios"
    )

    equipo_label = (
        "No disponible" if not equipos_filtrados else
        equipos_filtrados[0] if len(equipos_filtrados) == 1 else
        "Varios"
    )

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

    # ==================== GRAFICOS MODULARES ====================
    if nombre_modulo != "Equipos":
        col_fig1, col_fig2 = st.columns(2)
        with col_fig1:
            fig1 = grafico_estado_con_meta(dfm, nombre_modulo, meta_total)
            st.plotly_chart(fig1, use_container_width=True)
        with col_fig2:
            fig2 = grafico_categorias_barh(dfm, nombre_modulo, archivo_metas)
            st.plotly_chart(fig2, use_container_width=True)

        with st.container():
            if nombre_modulo == 'Analistas':
                cx1, cx2, cx3 = st.columns(3)
                with cx1: custom_metric("💯 Equipo", equipo_label)
                with cx2: custom_metric("🕵️‍♀️ Supervisor", supervisor_label)
                with cx3: custom_metric("👩‍💼 Profesional", auditor_label)
            elif nombre_modulo == 'Supervisores':
                cx1, cx2, cx3, cx4 = st.columns(4)
                with cx1: custom_metric("💯 Equipo", equipo_label) 
                with cx2: custom_metric("👨‍💻 Analista1", analista_label_1)
                with cx3: custom_metric("👨‍💻 Analista2", analista_label_2)
                with cx4: custom_metric("👩‍💼 Profesional", auditor_label)

        tabla = tabla_resumen(dfm, nombre_modulo, archivo_metas)
        st.markdown(f"<h3 style='color:#1F9924; font-weight:600; margin-top: 1em;'>Resumen {nombre_modulo}</h3>", unsafe_allow_html=True)
        st.dataframe(tabla, use_container_width=True)
        return
    
    # ==================== MÓDULO EQUIPOS ====================
    # a) Torta completa por auditor (sin vacíos ni ceros)
    if "auditor" in dfm.columns:
        aud_count = (
            dfm[dfm["auditor"].str.strip() != ""]
            .groupby("auditor")
            .size()
            .reset_index(name="cantidad")
        )
        aud_count = aud_count[aud_count["cantidad"] > 0]
    
        if not aud_count.empty:
            fig_aud = px.pie(
                aud_count,
                names="auditor",
                values="cantidad",
                hole=0.45,
                color_discrete_sequence=COLOR_PALETTE,
                title="<b>Distribución por Auditor</b>",
            )
            fig_aud.update_traces(textinfo="label+percent", textfont_size=12)
            fig_aud.update_layout(
                margin=dict(l=20, r=20, t=60, b=0),
                height=420,
                showlegend=False
            )
            st.plotly_chart(fig_aud, use_container_width=True)
        else:
            st.warning("No hay datos válidos de auditor para graficar.")
    else:
        st.warning("No existe columna 'auditor' en los datos.")

    if nombre_modulo == "Equipos":        
        with st.container():
            if nombre_modulo == 'Analistas':
                cx1, cx2, cx3 = st.columns(3)
                with cx1: custom_metric("💯 Equipo", equipo_label)
                with cx2: custom_metric("🕵️‍♀️ Supervisor", supervisor_label)
                with cx3: custom_metric("👩‍💼 Profesional", auditor_label)
        
            elif nombre_modulo == 'Supervisores':
                cx1, cx2, cx3, cx4 = st.columns(4)
                with cx1: custom_metric("💯 Equipo", equipo_label) 
                with cx2: custom_metric("👨‍💻 Analista1", analista_label_1)
                with cx3: custom_metric("👨‍💻 Analista2", analista_label_2)
                with cx4: custom_metric("👩‍💼 Profesional", auditor_label)                    
            else:
                cx1, cx2, cx3, cx4 = st.columns(4)
                with cx1: custom_metric("💯 Equipo", equipo_label) 
                with cx2: custom_metric("👨‍💻 Analista1", analista_label_1)
                with cx3: custom_metric("👨‍💻 Analista2", analista_label_2)
                with cx4: custom_metric("🕵️‍♀️ Supervisor", supervisor_label)
    
    # b) Barras por estado para cada EQUIPO (gráficos modulares y corregidos)
    if {"EQUIPO", "estado_carpeta"}.issubset(dfm.columns):
        st.subheader("📊 Estados por EQUIPO")
    
        tab_sup, tab_ana = st.tabs(["🕵️ Supervisor", "👨‍💻 Analistas"])
    
        # --- Configuración general base ---
        tmp_base = dfm.copy()
        tmp_base["estado_carpeta"] = tmp_base["estado_carpeta"].str.lower().fillna("")
        tmp_base = tmp_base[~tmp_base["estado_carpeta"].isin(["", "por asignar"])]
    
        tmp_base["EQUIPO_NUM"] = pd.to_numeric(tmp_base["EQUIPO"], errors="coerce")
        tmp_base = tmp_base.dropna(subset=["EQUIPO_NUM"])
        tmp_base["EQUIPO_NUM"] = tmp_base["EQUIPO_NUM"].astype(int)
    
        estado_cat = [ESTADOS_RENOM.get(e, e) for e in ESTADOS_ORDEN]
    
        # =======================================================
        # 🕵️ VISTA SUPERVISOR
        # =======================================================
        with tab_sup:
            fig_sup = grafico_estado_supervisor(tmp_base)
            st.plotly_chart(fig_sup, use_container_width=True)
    
        # =======================================================
        # 👨‍💻 VISTA ANALISTAS
        # =======================================================
        with tab_ana:
            fig_ana = grafico_estado_analistas(tmp_base)
            st.plotly_chart(fig_ana, use_container_width=True)

    else:
        st.warning("No hay datos válidos de EQUIPO/estado para graficar.")

    # c) Barras horizontales por Categoría (segmentadas por rol)
    #    Usamos categorías ya calculadas por sujeto: cat_supervisores_df y cat_analistas_df
    def barh_categorias_por_rol(cat_df: pd.DataFrame, rol_titulo: str):
        if cat_df.empty:
            return px.bar(title=f"<b>Sin datos de {rol_titulo}</b>")
        cnt = (cat_df.groupby("Categoria").size().reset_index(name="cantidad"))
        orden = ["Al día", "Atraso normal", "Atraso medio", "Atraso alto"]
        cnt["Categoria"] = pd.Categorical(cnt["Categoria"], categories=orden, ordered=True)
        cnt = cnt.sort_values("Categoria")
        fig = px.bar(
            cnt, x="cantidad", y="Categoria", orientation="h",
            color="Categoria", color_discrete_sequence=COLOR_PALETTE,
            title=f"<b>Categoría — {rol_titulo}</b>", text_auto=True
        )
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

    # Limitar a los sujetos presentes en dfm filtrado (para contexto de vista)
    sup_presentes = dfm["supervisor"].unique().tolist() if "supervisor" in dfm.columns else []
    ana_presentes = dfm["analista"].unique().tolist() if "analista" in dfm.columns else []

    sup_cat_local = cat_supervisores_df[cat_supervisores_df["Sujeto"].isin(sup_presentes)]
    ana_cat_local = cat_analistas_df[cat_analistas_df["Sujeto"].isin(ana_presentes)]

    colh1, colh2 = st.columns(2)
    with colh1:
        fig_sup = barh_categorias_por_rol(sup_cat_local, "Supervisores")
        st.plotly_chart(fig_sup, use_container_width=True)
    with colh2:
        fig_ana = barh_categorias_por_rol(ana_cat_local, "Analistas")
        st.plotly_chart(fig_ana, use_container_width=True)

    # Tabla resumen a nivel de "Equipos": usamos auditor como sujeto base
    ttabla = tabla_resumen(dfm, "Equipos", archivo_metas)
    st.markdown(f"<h3 style='color:#1F9924; font-weight:600; margin-top: 1em;'>Resumen {nombre_modulo}</h3>", unsafe_allow_html=True)
    st.dataframe(ttabla, use_container_width=True)

# ============ ENRUTAMIENTO ============ 
if st.session_state.pagina == "Analistas": 
    modulo_vista("Analistas", archivo_metas)
elif st.session_state.pagina == "Supervisores": 
    modulo_vista("Supervisores", archivo_metas)
elif st.session_state.pagina == "Equipos": 
    modulo_vista("Equipos", archivo_metas)
