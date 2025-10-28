import pandas as pd
from .logic import prepara_df_modulo, tabla_resumen, sujetos_col, get_meta_por_sujeto

def categorias_por_sujeto(df_base: pd.DataFrame, modulo: str, dias_habiles: int) -> pd.DataFrame:
    dfm = prepara_df_modulo(df_base, modulo)
    per_subject = get_meta_por_sujeto(modulo)
    per_subject_meta = per_subject * dias_habiles
    tab = tabla_resumen(dfm, modulo, per_subject_meta)

    sujeto_col_cap = sujetos_col(modulo).capitalize()
    equipo_map = (
        df_base[[sujetos_col(modulo), "EQUIPO"]]
        .drop_duplicates()
        .rename(columns={sujetos_col(modulo): sujeto_col_cap})
    )

    tab = tab.merge(equipo_map, on=sujeto_col_cap, how="left")
    tab["Modulo"] = modulo

    return tab[[sujeto_col_cap, "Categoria", "EQUIPO", "Modulo"]].rename(columns={sujeto_col_cap: "Sujeto"})

def aplicar_filtro_categoria_transversal(df_in: pd.DataFrame, categoria_sel: str,
                                         cat_analistas: pd.DataFrame,
                                         cat_supervisores: pd.DataFrame,
                                         cat_equipos: pd.DataFrame) -> pd.DataFrame:
    if categoria_sel in (None, "", "Todos"):
        return df_in

    out = df_in.copy()
    if "analista" in out.columns and not cat_analistas.empty:
        out = out.merge(cat_analistas.rename(columns={"Sujeto": "analista", "Categoria": "cat_analista"}), on="analista", how="left")
    if "supervisor" in out.columns and not cat_supervisores.empty:
        out = out.merge(cat_supervisores.rename(columns={"Sujeto": "supervisor", "Categoria": "cat_supervisor"}), on="supervisor", how="left")
    if "auditor" in out.columns and not cat_equipos.empty:
        out = out.merge(cat_equipos.rename(columns={"Sujeto": "auditor", "Categoria": "cat_auditor"}), on="auditor", how="left")

    out["categoria_global"] = out["cat_analista"].fillna(out["cat_supervisor"]).fillna(out["cat_auditor"])
    out = out[out["categoria_global"] == categoria_sel].copy()
    return out
