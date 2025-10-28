from enum import Enum

class Modulo(str, Enum):
    ANALISTAS = "Analistas"
    SUPERVISORES = "Supervisores"
    EQUIPOS = "Equipos"

class Estado(str, Enum):
    ASIGNADA = "asignada"
    DEVUELTA = "devuelta"
    CALIFICADA = "calificada"
    APROBADA = "aprobada"
    AUDITADA = "auditada"
