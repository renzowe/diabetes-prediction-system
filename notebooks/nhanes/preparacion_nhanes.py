"""Descarga, integración, partición y codificación de NHANES según docs/protocolo_nhanes.md.

La importan los notebooks de la fase NHANES para que la codificación sea idéntica en exploración,
entrenamiento y evaluación final.
"""

import hashlib
import math
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
RUTA_CRUDOS = RAIZ / "data/nhanes/raw"
RUTA_PARTICION = RAIZ / "particion/particion_nhanes.csv"
RUTA_FUENTES = RAIZ / "particion/fuentes_nhanes.csv"
RUTA_DESARROLLO = RAIZ / "data/processed/nhanes_desarrollo.csv"
RUTA_PRUEBA = RAIZ / "data/processed/nhanes_prueba.csv"  # solo lo lee el notebook de evaluación final

URL_BASE = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{anio}/DataFiles/{archivo}.xpt"

# Sección 2: ciclo -> (año de inicio en la URL, años que cubre, etiqueta)
CICLOS = {
    "E": (2007, 2.0, "2007-2008"),
    "F": (2009, 2.0, "2009-2010"),
    "G": (2011, 2.0, "2011-2012"),
    "H": (2013, 2.0, "2013-2014"),
    "I": (2015, 2.0, "2015-2016"),
    "P": (2017, 3.2, "2017-marzo 2020"),
}
CICLOS_PARTICIONABLES = ["E", "F", "G", "H", "I"]  # orden fijo de uso del generador
ANIOS_TOTALES = sum(c[1] for c in CICLOS.values())  # 13.2

VARIABLES = {
    "DEMO": ["RIDAGEYR", "RIAGENDR", "RIDRETH1", "RIDEXPRG", "SDMVSTRA", "SDMVPSU"],
    "BMX": ["BMXWT", "BMXHT", "BMXWAIST"],
    "GHB": ["LBXGH"],
    "DIQ": ["DIQ010", "DIQ160", "DIQ050", "DIQ070"],
    "BPQ": ["BPQ020"],
    "MCQ": ["MCQ300C"],
    "PAQ": ["PAQ650", "PAQ665"],
    "SMQ": ["SMQ020", "SMQ040"],
}

# Misma pregunta y codificación con otro nombre (protocolo, sección 15)
NOMBRES_EQUIVALENTES = {("E", "DIQ"): {"DID070": "DIQ070"}}

SEMILLA_PARTICION = 20261022
FRACCION_PRUEBA = 0.25

DESENLACE = "hba1c_elevada"
DESENLACE_SECUNDARIO = "hba1c_diabetes"
PREDICTORES = ["edad", "hombre", "imc", "cintura", "hta", "familiar_dm", "actividad", "fuma"]


def nombre_archivo(ciclo: str, modulo: str) -> str:
    return f"P_{modulo}" if ciclo == "P" else f"{modulo}_{ciclo}"


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def descargar(ciclo: str, modulo: str) -> dict:
    """Descarga un archivo XPT del CDC (si no está ya en disco) y comprueba que sea XPT."""
    archivo = nombre_archivo(ciclo, modulo)
    url = URL_BASE.format(anio=CICLOS[ciclo][0], archivo=archivo)
    ruta = RUTA_CRUDOS / f"{archivo}.xpt"
    if not ruta.exists():
        RUTA_CRUDOS.mkdir(parents=True, exist_ok=True)
        temporal = ruta.with_suffix(".parcial")
        urllib.request.urlretrieve(url, temporal)
        temporal.replace(ruta)
    with open(ruta, "rb") as f:
        if f.read(6) != b"HEADER":
            raise ValueError(f"{ruta.name} no es un archivo XPT; se descargó desde {url}")
    return {"ciclo": ciclo, "archivo": f"{archivo}.xpt", "url": url,
            "bytes": ruta.stat().st_size, "sha256": sha256(ruta)}


def leer_ciclo(ciclo: str) -> pd.DataFrame:
    """Une los módulos de un ciclo por SEQN, partiendo de DEMO (todos los participantes)."""
    peso = "WTMECPRP" if ciclo == "P" else "WTMEC2YR"
    df = None
    for modulo, columnas in VARIABLES.items():
        columnas = columnas + [peso] if modulo == "DEMO" else columnas
        tabla = pd.read_sas(RUTA_CRUDOS / f"{nombre_archivo(ciclo, modulo)}.xpt", format="xport")
        tabla = tabla.rename(columns=NOMBRES_EQUIVALENTES.get((ciclo, modulo), {}))
        faltan = [c for c in ["SEQN", *columnas] if c not in tabla.columns]
        if faltan:
            raise KeyError(f"{nombre_archivo(ciclo, modulo)} no tiene {faltan}")
        if tabla["SEQN"].duplicated().any():
            raise ValueError(f"SEQN duplicado dentro de {nombre_archivo(ciclo, modulo)}")
        tabla = tabla[["SEQN", *columnas]]
        df = tabla if df is None else df.merge(tabla, on="SEQN", how="left", validate="one_to_one")
    df = df.rename(columns={peso: "peso_mec"})
    # read_sas devuelve ceros como 5.4e-79: los códigos categóricos se redondean
    categoricas = [c for c in df.columns if c not in {"BMXWT", "BMXHT", "BMXWAIST", "LBXGH", "peso_mec"}]
    df[categoricas] = df[categoricas].round()
    df["SEQN"] = df["SEQN"].astype("int64")
    df.insert(1, "ciclo", ciclo)
    return df


def conglomerado(df: pd.DataFrame) -> pd.Series:
    return (df["ciclo"] + "-" + df["SDMVSTRA"].astype(int).astype(str)
            + "-" + df["SDMVPSU"].astype(int).astype(str))


def particionar(df: pd.DataFrame) -> pd.DataFrame:
    """Sección 5. Usa solo ciclo, estrato y unidad primaria; no consulta desenlace ni predictores."""
    base = df[["SEQN", "ciclo", "SDMVSTRA", "SDMVPSU"]].copy()
    base["conglomerado"] = conglomerado(base)
    rng = np.random.default_rng(SEMILLA_PARTICION)
    prueba = set()
    for ciclo in CICLOS_PARTICIONABLES:
        lista = (base.loc[base["ciclo"] == ciclo, ["SDMVSTRA", "SDMVPSU", "conglomerado"]]
                 .drop_duplicates().sort_values(["SDMVSTRA", "SDMVPSU"])["conglomerado"].to_numpy())
        orden = rng.permutation(len(lista))
        prueba.update(lista[orden[:math.ceil(FRACCION_PRUEBA * len(lista))]])
    base["conjunto"] = np.where(base["conglomerado"].isin(prueba), "prueba", "desarrollo")
    return base[["SEQN", "ciclo", "conglomerado", "conjunto"]].sort_values(["ciclo", "SEQN"])


def flujo_seleccion(df: pd.DataFrame) -> tuple[pd.DataFrame, list[tuple[str, int]]]:
    """Sección 3. Devuelve los seleccionados y el número que queda tras cada criterio."""
    pasos = [
        ("Participantes en DEMO", pd.Series(True, index=df.index)),
        ("Edad 20 a 69 años", df["RIDAGEYR"].between(20, 69)),
        ("Sin embarazo (RIDEXPRG distinto de 1)", df["RIDEXPRG"] != 1),
        ("DIQ010 = 2 (sin diagnóstico de diabetes ni borderline)", df["DIQ010"] == 2),
        ("Sin aviso de prediabetes (DIQ160 distinto de 1)", df["DIQ160"] != 1),
        ("Sin insulina ni pastillas (DIQ050 y DIQ070 distintos de 1)", (df["DIQ050"] != 1) & (df["DIQ070"] != 1)),
        ("HbA1c disponible", df["LBXGH"].notna()),
    ]
    mascara = pd.Series(True, index=df.index)
    conteo = []
    for nombre, condicion in pasos:
        mascara &= condicion
        conteo.append((nombre, int(mascara.sum())))
    return df[mascara].copy(), conteo


def _si_no(s: pd.Series) -> pd.Series:
    """NHANES codifica 1 = sí, 2 = no, 7 = rehusó, 9 = no sabe."""
    return s.map({1: 1.0, 2: 0.0})


def codificar(df: pd.DataFrame) -> pd.DataFrame:
    """Sección 4. Recibe los seleccionados y devuelve predictores, desenlaces, diseño y peso."""
    actividad = pd.Series(np.nan, index=df.index)
    actividad[(df["PAQ650"] == 2) & (df["PAQ665"] == 2)] = 0.0
    actividad[(df["PAQ650"] == 1) | (df["PAQ665"] == 1)] = 1.0

    fuma = pd.Series(np.nan, index=df.index)
    fuma[(df["SMQ040"] == 3) | (df["SMQ020"] == 2)] = 0.0
    fuma[df["SMQ040"].isin([1, 2])] = 1.0

    anios = df["ciclo"].map({c: v[1] for c, v in CICLOS.items()})
    return pd.DataFrame({
        "SEQN": df["SEQN"],
        "ciclo": df["ciclo"],
        "conglomerado": conglomerado(df),
        "estrato": df["ciclo"] + "-" + df["SDMVSTRA"].astype(int).astype(str),
        "peso": df["peso_mec"] * anios / ANIOS_TOTALES,  # sección 12, solo para descriptivos
        "raza_etnia": df["RIDRETH1"],  # solo descriptivos
        "hba1c": df["LBXGH"],
        DESENLACE: (df["LBXGH"] >= 5.7).astype(int),
        DESENLACE_SECUNDARIO: (df["LBXGH"] >= 6.5).astype(int),
        "edad": df["RIDAGEYR"],
        "hombre": (df["RIAGENDR"] == 1).astype(float),
        "imc": df["BMXWT"] / (df["BMXHT"] / 100) ** 2,
        "cintura": df["BMXWAIST"],
        "hta": _si_no(df["BPQ020"]),
        "familiar_dm": _si_no(df["MCQ300C"]),
        "actividad": actividad,
        "fuma": fuma,
    }).reset_index(drop=True)


def cargar_desarrollo() -> pd.DataFrame:
    return pd.read_csv(RUTA_DESARROLLO)
