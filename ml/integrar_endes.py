"""Integra los microdatos de la ENDES 2021-2025 y genera los conjuntos de Lima Metropolitana.

Une, por año, el Cuestionario de Salud (módulo 1640, CSALUD01), las Características de la
Vivienda (módulo 1630, RECH23) y las Características del Hogar (módulo 1629, RECH0) mediante
HHID. Aplica los criterios de selección del plan de tesis (sección 4.11) y escribe dos archivos
separados:

    data/processed/endes_lima_desarrollo_2021_2024.csv   -> todo el desarrollo del modelo
    data/processed/endes_lima_evaluacion_2025.csv        -> SOLO para la evaluación final

Ningún notebook ni script de modelado debe leer el archivo de evaluación (ver
docs/protocolo_analisis.md).

Uso:
    python ml/integrar_endes.py --endes ENDES --salida data/processed
"""

import argparse
import glob
from pathlib import Path

import numpy as np
import pandas as pd

ANIOS = range(2021, 2026)
ANIO_EVALUACION = 2025

COLS_SALUD = [
    "HHID", "QSNUMERO", "QSSEXO", "QS23", "QS25N", "QS26", "QS102", "QS107", "QS109",
    "QS200", "QS206", "QS208", "QS213U", "QS213C", "QS219U", "QS219C",
    "QS900", "QS901", "QS903S", "QS903D", "QS905S", "QS905D", "QS907", "PESO15_AMAS",
]
COLS_VIVIENDA = ["HHID", "SHREGION", "HV270"]
COLS_HOGAR = ["HHID", "HV024", "HV025"]

LIMA_METROPOLITANA = 1
EDAD_MIN, EDAD_MAX = 30, 69
CODIGO_NO_VALIDO = 999  # las mediciones antropométricas no realizadas se registran como 999.9


def leer_modulo(patron: str, columnas: list[str]) -> pd.DataFrame:
    """Lee un CSV de la ENDES detectando separador y codificación, que varían entre años
    (por ejemplo, 2022 usa ';' y coma decimal)."""
    rutas = glob.glob(patron)
    if len(rutas) != 1:
        raise FileNotFoundError(f"Se esperaba un archivo para {patron}, se encontraron {len(rutas)}")
    with open(rutas[0], "rb") as f:
        cabecera = f.readline()
    sep = ";" if cabecera.count(b";") > cabecera.count(b",") else ","
    enc = "utf-8-sig" if cabecera.startswith(b"\xef\xbb\xbf") else "latin1"
    df = pd.read_csv(rutas[0], sep=sep, encoding=enc, dtype=str, low_memory=False)
    df.columns = [c.strip().upper() for c in df.columns]
    faltantes = set(columnas) - set(df.columns)
    if faltantes:
        raise KeyError(f"{rutas[0]}: faltan columnas {sorted(faltantes)}")
    return df[columnas].apply(lambda s: s.str.strip())


def a_numerico(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.str.replace(",", ".", regex=False).replace("", np.nan), errors="coerce")


def integrar_anio(endes: Path, anio: int) -> pd.DataFrame:
    salud = leer_modulo(f"{endes}/{anio}/1640/CSALUD01*.csv", COLS_SALUD)
    vivienda = leer_modulo(f"{endes}/{anio}/1630/RECH23*.csv", COLS_VIVIENDA)
    hogar = leer_modulo(f"{endes}/{anio}/1629/RECH0*.csv", COLS_HOGAR)

    df = salud.merge(vivienda, on="HHID", how="left").merge(hogar, on="HHID", how="left")
    if df["SHREGION"].isna().any():
        raise ValueError(f"{anio}: {df['SHREGION'].isna().sum()} registros sin región tras el cruce")

    for col in df.columns.drop("HHID"):
        df[col] = a_numerico(df[col])
    df.insert(0, "ANIO", anio)
    return df


def seleccionar(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Criterios de inclusión y exclusión del plan de tesis (4.10 y 4.11).
    Devuelve (población, muestra con antropometría válida)."""
    lima = df[(df["SHREGION"] == LIMA_METROPOLITANA) & df["QS23"].between(EDAD_MIN, EDAD_MAX)]
    poblacion = lima[lima["QS109"].isin([1, 2])]  # excluye "no sabe" (8) y no respondidos
    antropometria_valida = (
        (poblacion["QS900"] < CODIGO_NO_VALIDO)
        & (poblacion["QS901"] < CODIGO_NO_VALIDO)
        & (poblacion["QS907"] < CODIGO_NO_VALIDO)
    )
    muestra = poblacion[antropometria_valida].copy()
    muestra["DM_AUTORREPORTADA"] = (muestra["QS109"] == 1).astype(int)
    muestra["IMC"] = muestra["QS900"] / (muestra["QS901"] / 100) ** 2
    return poblacion, muestra


def resumen(df: pd.DataFrame, nombre: str) -> None:
    por_anio = df.groupby("ANIO").agg(registros=("ANIO", "size"), casos=("DM_AUTORREPORTADA", "sum"))
    print(f"\n{nombre}\n{por_anio.to_string()}\nTotal: {len(df)} registros, {df['DM_AUTORREPORTADA'].sum()} casos")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--endes", type=Path, default=Path("ENDES"))
    parser.add_argument("--salida", type=Path, default=Path("data/processed"))
    args = parser.parse_args()

    datos = pd.concat([integrar_anio(args.endes, a) for a in ANIOS], ignore_index=True)
    poblacion, muestra = seleccionar(datos)
    print(f"Población (Lima, {EDAD_MIN}-{EDAD_MAX} años, QS109 válido): "
          f"{len(poblacion)} personas, {(poblacion['QS109'] == 1).sum()} con diagnóstico")

    desarrollo = muestra[muestra["ANIO"] < ANIO_EVALUACION]
    evaluacion = muestra[muestra["ANIO"] == ANIO_EVALUACION]
    resumen(desarrollo, "Conjunto de desarrollo (2021-2024)")
    print(f"\nConjunto de evaluación ({ANIO_EVALUACION}): {len(evaluacion)} registros "
          "(los casos no se muestran a propósito; ver docs/protocolo_analisis.md)")

    args.salida.mkdir(parents=True, exist_ok=True)
    desarrollo.to_csv(args.salida / "endes_lima_desarrollo_2021_2024.csv", index=False)
    evaluacion.to_csv(args.salida / f"endes_lima_evaluacion_{ANIO_EVALUACION}.csv", index=False)
    print(f"\nArchivos escritos en {args.salida}/")


if __name__ == "__main__":
    main()
