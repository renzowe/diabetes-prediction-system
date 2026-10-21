"""Codificación de predictores según docs/protocolo_analisis.md (sección 3).

La importan los notebooks 02 en adelante para que la codificación sea idéntica en exploración,
entrenamiento y evaluación final.
"""

from pathlib import Path

import pandas as pd

RUTA_DESARROLLO = Path(__file__).resolve().parent.parent / "data/processed/endes_lima_desarrollo_2021_2024.csv"

DESENLACE = "dm_autorreportada"

PREDICTORES_WEB = [
    "edad", "hombre", "imc", "cintura", "hta", "tabaco", "alcohol", "frutas_dias", "verduras_dias",
]
PREDICTORES_COMPLETO = PREDICTORES_WEB + ["pas", "pad", "educacion", "seguro", "riqueza"]

CODIGO_NO_VALIDO = 999


def _si_no(s: pd.Series) -> pd.Series:
    """ENDES codifica 1 = sí, 2 = no, 8 = no sabe."""
    return s.map({1: 1.0, 2: 0.0})


def _dias_por_semana(unidad: pd.Series, cantidad: pd.Series) -> pd.Series:
    """Unidad 1 = número de días (cantidad 1-7), 3 = no comió, 8 = no sabe."""
    dias = cantidad.where(unidad == 1)
    return dias.mask(unidad == 3, 0.0)


def _promedio_valido(a: pd.Series, b: pd.Series) -> pd.Series:
    return pd.concat([a, b], axis=1).where(lambda x: x < CODIGO_NO_VALIDO).mean(axis=1)


def codificar(df: pd.DataFrame) -> pd.DataFrame:
    """Recibe un conjunto generado por ml/integrar_endes.py y devuelve los predictores codificados,
    el desenlace y las columnas auxiliares (año, peso muestral y glucosa medida)."""
    alcohol = _si_no(df["QS208"]).mask(df["QS206"] == 2, 0.0)  # nunca bebió: el cuestionario salta QS208

    return pd.DataFrame({
        "anio": df["ANIO"],
        DESENLACE: df["DM_AUTORREPORTADA"],
        "edad": df["QS23"],
        "hombre": (df["QSSEXO"] == 1).astype(float),
        "imc": df["IMC"],
        "cintura": df["QS907"],
        "hta": _si_no(df["QS102"]),
        "tabaco": _si_no(df["QS200"]),
        "alcohol": alcohol,
        "frutas_dias": _dias_por_semana(df["QS213U"], df["QS213C"]),
        "verduras_dias": _dias_por_semana(df["QS219U"], df["QS219C"]),
        "pas": _promedio_valido(df["QS903S"], df["QS905S"]),
        "pad": _promedio_valido(df["QS903D"], df["QS905D"]),
        "educacion": df["QS25N"],
        "seguro": _si_no(df["QS26"]),
        "riqueza": df["HV270"],
        "peso_muestral": df["PESO15_AMAS"],
        "glucosa_12m": (df["QS107"] == 1).astype(int),
    }, index=df.index)


def cargar_desarrollo(ruta: Path = RUTA_DESARROLLO) -> pd.DataFrame:
    """Carga y codifica el conjunto de desarrollo (2021-2024). El conjunto de evaluación 2025
    no tiene función de carga aquí a propósito: solo lo lee el notebook de evaluación final."""
    datos = codificar(pd.read_csv(ruta))
    if datos["anio"].max() >= 2025:
        raise ValueError("El conjunto de desarrollo no debe contener registros de 2025")
    return datos
