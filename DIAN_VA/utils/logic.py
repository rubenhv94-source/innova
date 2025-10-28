from datetime import date, timedelta
import pandas as pd

START_DATE = date(2025, 9, 16)

def business_days_since_start(end_date: date) -> int:
    if end_date < START_DATE:
        return 0
    rng = pd.bdate_range(START_DATE, end_date)
    return len(rng)

def clasifica_categoria(atraso: int, modulo: str) -> str:
    if modulo == "Supervisores":
        if atraso < 0: return "Al día"
        if atraso <= 68: return "Atraso normal"
        if atraso <= 101: return "Atraso medio"
        return "Atraso alto"
    else:
        if atraso < 0: return "Al día"
        if atraso <= 10: return "Atraso normal"
        if atraso <= 34: return "Atraso medio"
        return "Atraso alto"

def sujetos_col(modulo: str) -> str:
    return {"Analistas": "analista", "Supervisores": "supervisor", "Equipos": "auditor"}[modulo]

def estados_validos(modulo: str) -> list[str]:
    if modulo == "Analistas":
        return ["auditada", "aprobada", "calificada"]
    if modulo == "Supervisores":
        return ["auditada", "aprobada"]
    return ["auditada"]

def get_meta_por_sujeto(modulo: str) -> int:
    return {"Analistas": 17, "Supervisores": 34, "Equipos": 34}.get(modulo, 0)
