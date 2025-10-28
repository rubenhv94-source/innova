import math
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Colores y estilo
COLOR_PALETTE = px.colors.sequential.Greens
ESTADOS_RENOM = {
    "": "Por asignar",
    "asignada": "0. asignada",
    "devuelta": "1. devuelta",
    "calificada": "2. calificada",
    "aprobada": "3. aprobada",
    "auditada": "4. auditada"
}

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
    from utils.logic import sujetos_col, desarrolladas_por_sujeto, clasifica_categoria

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
        title={"text": "<b>Avance total de carpetas</b>", "font": {"size": 18, "color": "#1F9924"}},
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
    fig.add_annotation(text=f"<b style='font-size:36px; color:#000;'>{valor_formateado}</b>", x=0.5, y=0, showarrow=False, xanchor="center")

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
