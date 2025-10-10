import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime, date, timedelta
import math


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

# ============ UTILIDADES ============
START_DATE = date(2025, 9, 16)
ESTADOS_ORDEN = ["asignada", "devuelta", "calificada", "aprobada", "auditada"]
ESTADOS_RENOM = {
    "": "Por asignar",
    "asignada": "0. asignada",
    "devuelta": "1. devuelta",
    "calificada": "2. calificada",
    "aprobada": "3. aprobada",
    "auditada": "4. auditada"
}

def business_days_since_start(end_date: date) -> int:
    """Días hábiles (L-V) entre START_DATE y end_date (inclusive)."""
    if end_date < START_DATE:
        return 0
    rng = pd.bdate_range(START_DATE, end_date)
    return len(rng)

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

def meta_acumulada(modulo: str, df_mod: pd.DataFrame, today: date | None = None) -> tuple[int, int]:
    if today is None:
        today = date.today()
    ayer = today - timedelta(days=1)
    dias_habiles = business_days_since_start(ayer)
    if dias_habiles <= 0:
        return 0, 0

    col = sujetos_col('Supervisores') if modulo == "Equipos" else sujetos_col(modulo)
    if col not in df_mod.columns:
        return 0, 0

    sujetos_unicos = (
        df_mod[col]
        .astype(str)
        .str.strip()
        .str.lower()
        .replace("", pd.NA)
        .dropna()
        .unique()
    )

    n_sujetos = len(sujetos_unicos)
    if n_sujetos == 0:
        return 0, 0

    por_sujeto = 17 if modulo == "Analistas" else 34
    meta = dias_habiles * por_sujeto * n_sujetos
    return meta, n_sujetos

def grafico_estado_con_meta(df_mod: pd.DataFrame, modulo: str, total_meta: int):
    conteo = (
        df_mod["estado_carpeta"]
        .fillna("")
        .str.lower()
        .map(ESTADOS_RENOM)
        .value_counts()
        .reindex(
            [ESTADOS_RENOM.get(e, e) for e in ["asignada", "devuelta", "calificada", "aprobada", "auditada"] + ["Por asignar"]],
            fill_value=0
        )
        .reset_index()
    )

    conteo.columns = ["estado_carpeta", "cantidad"]
    total = conteo["cantidad"].sum()
    if total == 0:
        return px.bar(title="<b>Sin datos para mostrar</b>")

    conteo["porcentaje"] = (conteo["cantidad"] / total * 100).round(1)
    conteo["label"] = conteo["cantidad"].astype(str) + " (" + conteo["porcentaje"].astype(str) + "%)"

    fig = px.bar(
        conteo,
        x="estado_carpeta",
        y="cantidad",
        color="estado_carpeta",
        color_discrete_sequence=COLOR_PALETTE,
        text="label",
        title="<b>Distribución por estado</b>",
    )

    fig.add_scatter(
        x=conteo["estado_carpeta"],
        y=[total_meta] * len(conteo),
        mode="lines",
        name="Meta acumulada",
        line=dict(color="#007BFF", width=2, dash="dash"),
    )

    fig.add_annotation(
        text=f"<b>Meta: {total_meta:,.0f}</b>".replace(",", "X").replace(".", ",").replace("X", "."),
        xref="paper", yref="paper",
        x=0.98, y=1.05,
        showarrow=False,
        font=dict(size=13, color="#007BFF", family="Arial"),
        align="right",
    )

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

def grafico_categorias_barh(df_mod: pd.DataFrame, modulo: str, per_subject_meta: int):
    col = sujetos_col(modulo)
    dev = desarrolladas_por_sujeto(df_mod, modulo)
    if dev.empty:
        return px.bar(title="<b>Sin datos para mostrar</b>")

    dev["meta"] = per_subject_meta
    dev["atraso"] = dev["meta"] - dev["desarrolladas"]
    dev["categoria"] = dev["atraso"].apply(lambda x: clasifica_categoria(int(x), modulo))

    cat_count = dev.groupby("categoria").size().reset_index(name="cantidad")
    orden = ["Al día", "Atraso normal", "Atraso medio", "Atraso alto"]
    cat_count["categoria"] = pd.Categorical(cat_count["categoria"], categories=orden, ordered=True)
    cat_count = cat_count.sort_values("categoria")

    fig = px.bar(
        cat_count,
        x="cantidad",
        y="categoria",
        orientation="h",
        color="categoria",
        color_discrete_sequence=COLOR_PALETTE,
        title="<b>Cantidad por seguimiento individual</b>",
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

def grafico_avance_total(total: int, avance: int, meta_ref: int | None = None):
    porcentaje = (avance / total * 100) if total > 0 else 0

    fig = go.Figure(go.Indicator(
        mode="gauge",
        value=avance,
        title={
            "text": "<b>Avance total de carpetas</b>",
            "font": {"size": 18, "color": "#1F9924"}
        },
        gauge={
            "axis": {"range": [0, total], "tickwidth": 1, "tickcolor": "#ccc", "tickfont": {"size": 10}},
            "bar": {"color": "#2e7d32", "thickness": 0.5},
            "bgcolor": "white",
            "steps": [
                {"range": [0, total * 0.5], "color": "#e0f2f1"},
                {"range": [total * 0.5, total], "color": "#e0f2f1"}
            ],
            "borderwidth": 2,
            "bordercolor": "#cccccc"
        },
        domain={'x': [0, 1], 'y': [0, 1]}
    ))

    valor_formateado = f"{avance:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    fig.add_annotation(
        text=f"<b style='font-size:36px; color:#000;'>{valor_formateado}</b>",
        x=0.5, y=0, showarrow=False, xanchor="center"
    )

    fig.add_annotation(
        text=f"<b style='font-size:16px; color:#1F9924;'>{porcentaje:,.1f}%</b>".replace(",", "X").replace(".", ",").replace("X", "."),
        x=0.5, y=0.3, showarrow=False, xanchor="center"
    )

    total_formateado = f"{total:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    fig.add_annotation(
        text=f"Total: {total_formateado}",
        x=0.5, y=-0.1, showarrow=False,
        font=dict(size=13, color="#444", family="Arial"),
        xanchor="center"
    )

    if meta_ref and 0 < meta_ref < total:
        theta = 180 * (meta_ref / total)
        x0 = 0.5 - 0.35 * math.cos(math.radians(theta))
        y0 = 0.5 + 0.35 * math.sin(math.radians(theta))
        x1 = 0.5 - 0.42 * math.cos(math.radians(theta))
        y1 = 0.5 + 0.42 * math.sin(math.radians(theta))

        fig.add_shape(type="line", x0=x0, y0=y0, x1=x1, y1=y1, line=dict(color="red", width=3))
        fig.add_annotation(text="Meta", x=x1, y=y1 + 0.05, showarrow=False,
                           font=dict(size=11, color="red"), xanchor="center")

    fig.update_layout(margin=dict(l=20, r=20, t=70, b=60), height=320,
                      paper_bgcolor="#ffffff", font={"family": "Arial", "color": "#1a1a1a"})
    return fig

def tabla_resumen(df_mod: pd.DataFrame, modulo: str, per_subject_meta: int) -> pd.DataFrame:
    col = sujetos_col(modulo)

    if df_mod.empty or col not in df_mod.columns:
        return pd.DataFrame(columns=["Categoria", col.capitalize(), "Analizadas", "Meta", "Faltantes"])

    if modulo.lower() == "analistas":
        estados_efectivos = {"auditada", "aprobada", "calificada"}
    elif modulo.lower() == "supervisores":
        estados_efectivos = {"auditada", "aprobada"}
    else:
        estados_efectivos = set()

    df_mod = df_mod.dropna(subset=["estado_carpeta", col])
    df_mod["estado_carpeta"] = df_mod["estado_carpeta"].str.strip().str.lower()

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
    pivot["Meta"] = per_subject_meta
    pivot["Faltantes"] = pivot["Meta"] - pivot["Analizadas"]
    pivot["Categoria"] = pivot["Faltantes"].apply(lambda x: clasifica_categoria(int(x), modulo))

    columnas_estado = ESTADOS_ORDEN
    out = pivot[[col] + columnas_estado + ["Analizadas", "Meta", "Faltantes", "Categoria"]]

    categorias = ["Al día", "Atraso normal", "Atraso medio", "Atraso alto"]
    out["Categoria"] = pd.Categorical(out["Categoria"], categories=categorias, ordered=True)
    out = out.sort_values(["Categoria", col], ascending=[True, True])

    out = out.rename(columns={col: col.capitalize(), **{e: ESTADOS_RENOM.get(e, e) for e in columnas_estado}})
    return out

def grafico_estado_supervisor(df: pd.DataFrame):
    # Mapear supervisor por equipo
    sup_info = (
        df[["EQUIPO_NUM", "supervisor"]]
        .drop_duplicates()
        .groupby("EQUIPO_NUM")["supervisor"]
        .agg(lambda x: ', '.join(sorted(x.dropna().unique())))
        .to_dict()
    )

    # Preparar datos
    df["supervisor"] = df["EQUIPO_NUM"].map(sup_info)
    df["estado_label"] = df["estado_carpeta"].map(ESTADOS_RENOM)
    df["estado_label"] = pd.Categorical(
        df["estado_label"],
        categories=[ESTADOS_RENOM[e] for e in ESTADOS_ORDEN],
        ordered=True
    )

    # Agrupar
    grp = (
        df.groupby(["EQUIPO_NUM", "estado_label", "supervisor"])
        .size()
        .reset_index(name="cantidad")
    )

    # Crear figura
    fig = go.Figure()

    # Crear una traza por cada estado (esto asegura tooltips correctos)
    for estado in [ESTADOS_RENOM[e] for e in ESTADOS_ORDEN]:
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

    # Layout
    fig.update_layout(
        barmode="stack",
        title="<b>Estados por EQUIPO — Vista: Supervisor</b>",
        xaxis_title="Equipo",
        yaxis=dict(title="Cantidad", range=[0, 1000],),
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
    # Asignar roles por equipo: A1, A2...
    analistas_unicos = (
        df[["EQUIPO_NUM", "analista"]]
        .drop_duplicates()
        .sort_values(["EQUIPO_NUM", "analista"])
    )
    analistas_unicos["rol"] = analistas_unicos.groupby("EQUIPO_NUM").cumcount() + 1
    analistas_unicos["rol"] = "A" + analistas_unicos["rol"].astype(str)

    df = df.merge(analistas_unicos, on=["EQUIPO_NUM", "analista"], how="left")
    df["equipo_rol"] = df["EQUIPO_NUM"].astype(str) + " " + df["rol"]

    # Homologar estado
    df["estado_homol"] = df["estado_carpeta"].str.lower().map(ESTADOS_RENOM).fillna("Otro")

    # Agrupar
    grouped = (
        df.groupby(["EQUIPO_NUM", "analista", "equipo_rol", "estado_homol"])
        .size()
        .reset_index(name="cantidad")
    )

    # Pivot para tener estados como columnas
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
                hovertemplate="<b>A:</b> %{customdata[0]}<br><b>E:</b> %{customdata[1]}<br><b>C:</b> %{customdata[2]}<extra></extra>",
            )
        )

    # Layout
    fig.update_layout(
        barmode="stack",
        title="<b>Estados por EQUIPO — Vista: Analistas</b>",
        xaxis_title="Equipo",
        yaxis=dict(title="Cantidad", range=[0, 500],),
        font=dict(family="Arial", size=12),
        title_font=dict(size=18, color="#1F9924", family="Arial"),
        plot_bgcolor="white",
        legend_title_text="Estado",
        height=500,
        margin=dict(l=30, r=30, t=60, b=70),
        bargap=0.4,  # barras más delgadas
        colorway=COLOR_PALETTE,
        xaxis=dict(
            tickmode="array",
            tickvals=pivot["equipo_rol"],
            ticktext=pivot["EQUIPO_NUM"].astype(str)
        )
    )

    return fig

# ---------- utilidades de categorías globales (para filtro transversal) ----------
def categorias_por_sujeto(df_base: pd.DataFrame, modulo: str, dias_habiles: int) -> pd.DataFrame:
    """Devuelve DataFrame con columnas: sujeto (analista/supervisor/auditor), Categoria y además EQUIPO para posible cruce."""
    dfm = prepara_df_modulo(df_base, modulo)
    per_subject = 34 if modulo == "Supervisores" else 17
    per_subject_meta = per_subject * dias_habiles
    tab = tabla_resumen(dfm, modulo, per_subject_meta)
    sujeto_col_cap = sujetos_col(modulo).capitalize()

    # Mapear equipo desde df_base
    equipo_map = (df_base[[sujetos_col(modulo), "EQUIPO"]]
                  .drop_duplicates()
                  .rename(columns={sujetos_col(modulo): sujeto_col_cap}))
    tab = tab.merge(equipo_map, on=sujeto_col_cap, how="left")
    tab["Modulo"] = modulo
    return tab[[sujeto_col_cap, "Categoria", "EQUIPO", "Modulo"]].rename(columns={sujeto_col_cap: "Sujeto"})

def aplicar_filtro_categoria_transversal(df_in: pd.DataFrame, categoria_sel: str,
                                         cat_analistas: pd.DataFrame,
                                         cat_supervisores: pd.DataFrame,
                                         cat_equipos: pd.DataFrame) -> pd.DataFrame:
    """Filtra filas cuyo analista/supervisor/auditor caiga en la categoría seleccionada."""
    if categoria_sel in (None, "", "Todos"):
        return df_in

    # Join de categorías a nivel de fila
    out = df_in.copy()
    if "analista" in out.columns and not cat_analistas.empty:
        out = out.merge(cat_analistas[["Sujeto", "Categoria"]].rename(columns={"Sujeto": "analista", "Categoria": "cat_analista"}),
                        on="analista", how="left")
    if "supervisor" in out.columns and not cat_supervisores.empty:
        out = out.merge(cat_supervisores[["Sujeto", "Categoria"]].rename(columns={"Sujeto": "supervisor", "Categoria": "cat_supervisor"}),
                        on="supervisor", how="left")
    if "auditor" in out.columns and not cat_equipos.empty:
        out = out.merge(cat_equipos[["Sujeto", "Categoria"]].rename(columns={"Sujeto": "auditor", "Categoria": "cat_auditor"}),
                        on="auditor", how="left")

    # categoría global fila = primero no-nulo
    out["categoria_global"] = out["cat_analista"].fillna(out["cat_supervisor"]).fillna(out["cat_auditor"])
    out = out[out["categoria_global"] == categoria_sel].copy()
    return out

# ============ NAVEGACION ============
if "pagina" not in st.session_state:
    st.session_state.pagina = st.query_params.get("pagina", "Inicio")

secciones = ["Inicio", "Resumen", "Analistas", "Supervisores", "Equipos"]
pagina_actual = st.session_state.pagina
seleccion = st.sidebar.radio("Ir a la sección:", secciones, index=secciones.index(pagina_actual), key="nav_radio")
if seleccion != pagina_actual:
    st.session_state.pagina = seleccion
    st.query_params["pagina"] = seleccion
    st.rerun()

# ============ SIDEBAR FILTROS (persistentes) ============
with st.sidebar:
    st.header("🔎 Filtros")

    # Botón para recargar datos desde Google Sheets (limpia la caché)
    if st.button("🔄 Recargar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    # Inicializar estados si no existen
    for k in ["sel_prof", "sel_sup", "sel_ana", "sel_estado", "sel_nivel", "sel_categoria"]:
        if k not in st.session_state:
            st.session_state[k] = "Todos"

    # Botón para limpiar filtros sin cambiar de página
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

    # Generar opciones válidas con base en filtro actual
    opciones_prof = ["Todos"] + sorted(df_temp["auditor"].dropna().unique())
    opciones_sup = ["Todos"] + sorted(df_temp["supervisor"].dropna().unique())
    opciones_ana = ["Todos"] + sorted(df_temp["analista"].dropna().unique())
    opciones_estado = ["Todos"] + sorted(set(df["estado_carpeta"].str.lower().dropna().unique()) | {""})
    opciones_nivel = ["Todos"] + sorted(df_temp["nivel"].dropna().unique()) if "nivel" in df_temp.columns else ["Todos"]

    # Mostrar selectboxes
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

    # 🔄 Filtro de Categoría dependiente del resto
    df_filtro_prev = df.copy()
    if st.session_state.sel_prof != "Todos":
        df_filtro_prev = df_filtro_prev[df_filtro_prev["auditor"] == st.session_state.sel_prof]
    if st.session_state.sel_sup != "Todos":
        df_filtro_prev = df_filtro_prev[df_filtro_prev["supervisor"] == st.session_state.sel_sup]
    if st.session_state.sel_ana != "Todos":
        df_filtro_prev = df_filtro_prev[df_filtro_prev["analista"] == st.session_state.sel_ana]

    dias_habiles_categoria = business_days_since_start(date.today() - timedelta(days=1))
    cat_ana_sub = categorias_por_sujeto(df_filtro_prev, "Analistas", dias_habiles_categoria)
    cat_sup_sub = categorias_por_sujeto(df_filtro_prev, "Supervisores", dias_habiles_categoria)
    cat_equ_sub = categorias_por_sujeto(df_filtro_prev, "Equipos", dias_habiles_categoria)

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

# ========= Preparar categorías por sujeto (para filtro transversal) =========
dias_habiles_ref = business_days_since_start(date.today() - timedelta(days=1))
cat_analistas_df = categorias_por_sujeto(df, "Analistas", dias_habiles_ref)
cat_supervisores_df = categorias_por_sujeto(df, "Supervisores", dias_habiles_ref)
cat_equipos_df = categorias_por_sujeto(df, "Equipos", dias_habiles_ref)

# ========= Aplicar filtros al DataFrame =========
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

# Aplicar filtro por Categoría (transversal)
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

    st.markdown("<h1 style='text-align:center; font-weight:700; color:#1F9924'>Seguimiento de Metas VA DIAN 2667</h1>", unsafe_allow_html=True)

    col_left, col_center, col_right = st.columns([1, 1, 1])
    with col_left:
        st.write("")
        if st.button("Resumen", key="btn_home_resumen"):
            st.session_state.pagina = "Resumen"
            st.query_params["pagina"] = "Resumen"
            st.rerun()
        if st.button("Analistas", key="btn_home_analistas"):
            st.session_state.pagina = "Analistas"
            st.query_params["pagina"] = "Analistas"
            st.rerun()
        if st.button("Supervisores", key="btn_home_supervisores"):
            st.session_state.pagina = "Supervisores"
            st.query_params["pagina"] = "Supervisores"
            st.rerun()
        if st.button("Equipos", key="btn_home_equipos"):
            st.session_state.pagina = "Equipos"
            st.query_params["pagina"] = "Equipos"
            st.rerun()
    with col_center:
        st.image("assets/Logo Tablero.jpg", use_container_width=True)

# ============ RESUMEN ============
if st.session_state.pagina == "Resumen":
    st.markdown(f"<h1 style='color:#1F9924;'>Resumen general</h1>", unsafe_allow_html=True)
    dias_habiles = business_days_since_start(date.today() - timedelta(days=1))
    st.info(f"Días hábiles considerados: **{dias_habiles}** - Fecha de corte: **{date.today() - timedelta(days=1)}**")

    por_asignar = df_filtrado["estado_carpeta"].fillna("").eq("").sum()
    equipo_va = df_filtrado["analista"].nunique() + df_filtrado["supervisor"].nunique()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📂 Total carpetas", f"{len(df_filtrado):,}".replace(",", "."))
    col2.metric("✔️ Auditadas", f"{(df_filtrado['estado_carpeta'].str.lower() == 'auditada').sum():,}".replace(",", "."))
    col3.metric("👨‍👧‍👧 Equipo VA", f"{equipo_va:,}".replace(",", "."))
    col4.metric("📌 Por asignar", f"{por_asignar:,}".replace(",", "."))

    avance = df_filtrado["estado_carpeta"].str.lower().isin(["auditada"]).sum()
    total = len(df_filtrado)
    dfm = prepara_df_modulo(df_filtrado, "Supervisores")
    meta_total, n_sujetos = meta_acumulada("Supervisores", dfm)
    fig_gauge = grafico_avance_total(total, avance, meta_total)
    st.plotly_chart(fig_gauge, use_container_width=True)

    fig_estado = grafico_estado_con_meta(df_filtrado, "Resumen", meta_total)
    st.plotly_chart(fig_estado, use_container_width=True)

# ============ VISTA MÓDULOS ============
def modulo_vista(nombre_modulo: str):
    st.markdown(f"<h1 style='color:#1F9924;'>{nombre_modulo}</h1>", unsafe_allow_html=True)
    dfm = prepara_df_modulo(df_filtrado, nombre_modulo)

    dias_habiles = business_days_since_start(date.today() - timedelta(days=1))
    meta_total, n_sujetos = meta_acumulada(nombre_modulo, dfm)
    st.info(f"Equipo: **{n_sujetos:,}** - Días hábiles considerados: **{dias_habiles}** - Fecha de corte: **{date.today() - timedelta(days=1)}**".replace(",", "."))

    validos = estados_validos(nombre_modulo)
    desarrolladas_total = (
        dfm["estado_carpeta"].str.lower().isin(validos)
    ).sum() if "estado_carpeta" in dfm.columns else 0
    diferencia_total = desarrolladas_total - meta_total

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📂 Total carpetas", f"{len(dfm):,}".replace(",", "."))
    c2.metric("✔️ Desarrolladas", f"{desarrolladas_total:,}".replace(",", "."))
    c3.metric("🎯 Meta a la fecha", f"{meta_total:,}".replace(",", "."))
    c4.metric("⚠️ Diferencia", f"{diferencia_total:,}".replace(",", "."))

    dias_habiles_loc = dias_habiles
    per_subject = 34 if nombre_modulo == "Supervisores" else 17
    meta_individual = per_subject * dias_habiles_loc
   
    # ---------- Cabecera de métricas de contexto ----------
    analistas_filtrados = sorted(df_filtrado["analista"].dropna().unique()) if "analista" in df_filtrado.columns else []
    supervisores_filtrados = sorted(df_filtrado["supervisor"].dropna().unique()) if "supervisor" in df_filtrado.columns else []
    auditores_filtrados = sorted(df_filtrado["auditor"].dropna().unique()) if "auditor" in df_filtrado.columns else []
    equipos_filtrados = sorted(df_filtrado["EQUIPO"].dropna().unique()) if "EQUIPO" in df_filtrado.columns else []

    if len(analistas_filtrados) == 0:
        analista_label_1 = "No disponible"; analista_label_2 = "No disponible"
    elif len(analistas_filtrados) == 1:
        analista_label_1 = analistas_filtrados[0]; analista_label_2 = ""
    elif len(analistas_filtrados) == 2:
        analista_label_1 = analistas_filtrados[0]; analista_label_2 = analistas_filtrados[1]
    else:
        analista_label_1 = "Varios"; analista_label_2 = "Varios"
    
    if len(supervisores_filtrados) == 1: supervisor_label = supervisores_filtrados[0]
    elif len(supervisores_filtrados) > 1: supervisor_label = "Varios"
    else: supervisor_label = "No disponible"

    if len(auditores_filtrados) == 1: auditor_label = auditores_filtrados[0]
    elif len(auditores_filtrados) > 1: auditor_label = "Varios"
    else: auditor_label = "No disponible"

    if len(equipos_filtrados) == 1: equipo_label = equipos_filtrados[0]
    elif len(equipos_filtrados) > 1: equipo_label = "Varios"
    else: equipo_label = "No disponible"
    
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
    
    # ---------- Contenido por módulo ----------
    if nombre_modulo != "Equipos":
        col_fig1, col_fig2 = st.columns(2)
        with col_fig1:
            fig1 = grafico_estado_con_meta(dfm, nombre_modulo, meta_total)
            st.plotly_chart(fig1, use_container_width=True)
        with col_fig2:
            fig2 = grafico_categorias_barh(dfm, nombre_modulo, meta_individual)
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
            else:
                cx1, cx2, cx3, cx4 = st.columns(4)
                with cx1: custom_metric("💯 Equipo", equipo_label) 
                with cx2: custom_metric("👨‍💻 Analista1", analista_label_1)
                with cx3: custom_metric("👨‍💻 Analista2", analista_label_2)
                with cx4: custom_metric("🕵️‍♀️ Supervisor", supervisor_label)
        
        tabla = tabla_resumen(dfm, nombre_modulo, meta_individual)
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
    tabla = tabla_resumen(dfm, "Equipos", 34 * dias_habiles_loc)  # meta individual auditores ~ supervisores
    st.markdown(f"<h3 style='color:#1F9924; font-weight:600; margin-top: 1em;'>Resumen {nombre_modulo}</h3>", unsafe_allow_html=True)
    st.dataframe(tabla, use_container_width=True)

# ============ ENRUTAMIENTO ============
if st.session_state.pagina == "Analistas":
    modulo_vista("Analistas")
elif st.session_state.pagina == "Supervisores":
    modulo_vista("Supervisores")
elif st.session_state.pagina == "Equipos":
    modulo_vista("Equipos")
