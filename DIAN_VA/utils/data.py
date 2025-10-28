import pandas as pd
import streamlit as st

@st.cache_data(ttl=600)
def cargar_datos(url: str) -> pd.DataFrame:
    df = pd.read_csv(url, dtype=str)
    for c in ["analista", "supervisor", "auditor", "estado_carpeta", "profesional", "nivel", "EQUIPO"]:
        if c in df.columns:
            df[c] = df[c].fillna("").str.strip()
    return df
