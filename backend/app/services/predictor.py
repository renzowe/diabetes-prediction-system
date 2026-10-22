"""Carga el modelo NHANES congelado en notebooks/nhanes/03 y los remuestreos bootstrap de
notebooks/nhanes/04, y calcula para cada persona la probabilidad estimada, su intervalo, las
contribuciones SHAP de cada factor y las recomendaciones del catalogo."""

import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.schemas.diabetes import EvaluacionEntrada
from app.services.recomendaciones import Perfil, Recomendacion, seleccionar

# Predictor del modelo -> factor que se explica. IMC y perimetro abdominal estan muy correlacionados
# (r = 0.91) y el modelo estima el efecto de cada uno a igual valor del otro; por eso se suman en un
# solo factor. En un modelo lineal los valores SHAP son aditivos, asi que la suma es exacta.
FACTOR_DE_PREDICTOR = {
    "edad": "edad",
    "hombre": "sexo",
    "imc": "composicion_corporal",
    "cintura": "composicion_corporal",
    "hta": "hipertension",
    "familiar_dm": "antecedente_familiar",
    "actividad": "actividad",
    "fuma": "tabaquismo",
}


def _si_no(valor: bool | None, si: str, no: str) -> str:
    return "No sabe" if valor is None else (si if valor else no)


# Factor -> (etiqueta, dato de la persona en lenguaje sencillo)
ETIQUETAS = {
    "edad": ("Edad", lambda d: f"{d.edad} años"),
    "sexo": ("Sexo", lambda d: "Mujer" if d.sexo == "femenino" else "Hombre"),
    "composicion_corporal": (
        "Composición corporal",
        lambda d: f"IMC {d.imc:.1f}" + (f" · perímetro abdominal {d.cintura_cm:.0f} cm" if d.cintura_cm else ""),
    ),
    "hipertension": ("Hipertensión arterial", lambda d: _si_no(d.hipertension, "Con diagnóstico médico", "Sin diagnóstico médico")),
    "antecedente_familiar": ("Familiar directo con diabetes", lambda d: _si_no(d.familiar_diabetes, "Sí", "No")),
    "actividad": ("Actividad física recreativa", lambda d: _si_no(d.actividad_fisica, "Sí realiza", "No realiza")),
    "tabaquismo": ("Tabaco", lambda d: _si_no(d.fuma, "Fuma actualmente", "No fuma")),
}

MAXIMO_FACTORES = 3
CONTRIBUCION_MINIMA = 0.05  # log-odds; contribuciones menores no se muestran

# Proporcion ponderada de HbA1c >= 5.7 % en el desarrollo (notebooks/nhanes/02, prevalencia.csv)
PREVALENCIA_REFERENCIA = 0.2062

MENSAJE_ALCANCE = (
    "Esta cifra estima qué proporción de las personas con un perfil como el suyo tenía, sin saberlo, una "
    "hemoglobina glicosilada (HbA1c) de 5.7 % o más, valor compatible con prediabetes o diabetes, en la encuesta "
    "NHANES de Estados Unidos. No es un diagnóstico ni indica si usted tiene diabetes: solo un análisis de "
    "laboratorio puede confirmarlo. El modelo se desarrolló con población de Estados Unidos y su aplicación en "
    "Lima Metropolitana está en evaluación."
)

NOTA_INTERVALO = (
    "El intervalo indica la precisión con que el modelo estima esta proporción para su perfil. No indica un "
    "rango de su HbA1c ni la certeza sobre su caso individual."
)

NOTA_FACTORES = (
    "Estas contribuciones (valores SHAP) describen cómo el modelo combinó sus datos para obtener la estimación, "
    "en comparación con una persona promedio de la población de referencia (adultos de 20 a 69 años de EE. UU. "
    "sin diagnóstico previo, NHANES 2007-2020). No son consejos de salud ni efectos causales: no indican que "
    "cambiar un dato vaya a modificar su probabilidad real."
)

# Aviso añadido DESPUES de la evaluacion final (protocolo, seccion 15): en el conjunto de prueba la
# AUC-ROC fue 0.573 en el grupo de 60 a 69 años (n = 736). No cambia el modelo ni la probabilidad.
EDAD_AVISO = 60
AVISO_EDAD = (
    "En personas de 60 a 69 años, la evaluación del modelo mostró que distingue poco entre personas de la misma "
    "edad: en ese grupo, la estimación ayuda menos a saber quién tiene la HbA1c elevada. Tome este resultado con "
    "especial cautela. A su edad, las guías indican realizarse una prueba de laboratorio, que es la única forma de "
    "conocer su HbA1c."
)

NOTA_RECOMENDACIONES = (
    "Recomendaciones generales tomadas de guías de salud, elegidas según los datos que ingresó. No sustituyen la "
    "consulta con un profesional de salud ni garantizan una reducción del riesgo. Están pendientes de revisión "
    "por un panel de expertos."
)


@dataclass(frozen=True)
class Factor:
    clave: str
    factor: str
    valor: str
    efecto: str          # "aumenta" | "disminuye" (respecto de la persona promedio)
    contribucion: float  # valor SHAP en log-odds


@dataclass(frozen=True)
class Resultado:
    probabilidad: float
    intervalo: tuple[float, float]
    contribuciones: dict[str, float]  # todos los factores
    factores_mostrados: list[Factor]
    recomendaciones: list[Recomendacion]


def _parametros(pipeline: Pipeline) -> dict:
    """Valores de imputacion, media, desviacion y coeficiente de cada predictor (mismo formato que
    los remuestreos de notebooks/nhanes/04)."""
    prep, modelo = pipeline.named_steps["prep"], pipeline.named_steps["modelo"]
    filas, j = {}, 0
    for nombre, sub, columnas in prep.transformers_:
        if nombre == "remainder":
            continue
        imputar, escalar = sub.named_steps["imputar"], sub.named_steps["escalar"]
        for k, col in enumerate(columnas):
            filas[col] = (imputar.statistics_[k], escalar.mean_[k], escalar.scale_[k], modelo.coef_[0, j])
            j += 1
    return filas


class ModeloRiesgo:
    """Envuelve el artefacto de notebooks/nhanes/03 y los remuestreos de notebooks/nhanes/04."""

    def __init__(self, directorio: str | Path):
        directorio = Path(directorio)
        seleccion = json.loads((directorio / "seleccion.json").read_text(encoding="utf-8"))
        self.archivo = seleccion["seleccionado"]
        artefacto = joblib.load(directorio / self.archivo)

        pipeline = artefacto["modelo"]
        if not (isinstance(pipeline, Pipeline) and isinstance(pipeline.named_steps["modelo"], LogisticRegression)):
            raise TypeError("Las contribuciones SHAP exactas y el bootstrap requieren un pipeline de regresion logistica")

        self.predictores: list[str] = artefacto["predictores"]
        self.metadatos = {k: artefacto[k] for k in ("algoritmo", "desenlace", "datos_entrenamiento", "fecha")}
        self._pipeline = pipeline

        p = _parametros(pipeline)
        self._imputacion, self._media, self._escala, self._coef = (
            np.array([p[c][i] for c in self.predictores]) for i in range(4)
        )
        self.intercepto = float(pipeline.named_steps["modelo"].intercept_[0])

        boot = joblib.load(directorio / "bootstrap_regresion_logistica.joblib")
        if boot["predictores"] != self.predictores:
            raise ValueError("Los remuestreos bootstrap no corresponden a los predictores del modelo")
        self._boot = {k: boot[k] for k in ("imputacion", "media", "escala", "coef", "intercepto")}
        self.percentiles = boot["percentiles"]

    def _vector(self, datos: EvaluacionEntrada) -> np.ndarray:
        """Predictores en el orden del modelo; los datos que la persona no sabe quedan como NaN y se
        imputan igual que en el entrenamiento."""
        def num(v):
            return np.nan if v is None else float(v)

        valores = {
            "edad": datos.edad,
            "hombre": 1.0 if datos.sexo == "masculino" else 0.0,
            "imc": datos.imc,
            "cintura": num(datos.cintura_cm),
            "hta": num(datos.hipertension),
            "familiar_dm": num(datos.familiar_diabetes),
            "actividad": num(datos.actividad_fisica),
            "fuma": num(datos.fuma),
        }
        return np.array([valores[c] for c in self.predictores], dtype=float)

    def fila(self, datos: EvaluacionEntrada) -> pd.DataFrame:
        return pd.DataFrame([self._vector(datos)], columns=self.predictores)

    def predecir(self, datos: EvaluacionEntrada) -> Resultado:
        x = self._vector(datos)

        # Valores SHAP exactos de un modelo lineal (en log-odds, respecto de la media del entrenamiento):
        # coeficiente x valor estandarizado.
        z = (np.where(np.isnan(x), self._imputacion, x) - self._media) / self._escala
        shap = self._coef * z
        log_odds = self.intercepto + shap.sum()
        probabilidad = float(1 / (1 + np.exp(-log_odds)))

        b = self._boot
        xb = np.where(np.isnan(x), b["imputacion"], x)
        p_boot = 1 / (1 + np.exp(-(((xb - b["media"]) / b["escala"] * b["coef"]).sum(axis=1) + b["intercepto"])))
        intervalo = tuple(float(v) for v in np.percentile(p_boot, self.percentiles))

        contribuciones: dict[str, float] = {}
        for columna, valor in zip(self.predictores, shap):
            factor = FACTOR_DE_PREDICTOR[columna]
            contribuciones[factor] = contribuciones.get(factor, 0.0) + float(valor)

        principales = sorted(
            (k for k, v in contribuciones.items() if abs(v) >= CONTRIBUCION_MINIMA),
            key=lambda k: abs(contribuciones[k]), reverse=True,
        )[:MAXIMO_FACTORES]
        mostrados = [
            Factor(
                clave=k,
                factor=ETIQUETAS[k][0],
                valor=ETIQUETAS[k][1](datos),
                efecto="aumenta" if contribuciones[k] > 0 else "disminuye",
                contribucion=round(contribuciones[k], 4),
            )
            for k in principales
        ]

        perfil = Perfil(
            edad=datos.edad, imc=datos.imc, hipertension=datos.hipertension,
            familiar_diabetes=datos.familiar_diabetes, actividad_fisica=datos.actividad_fisica, fuma=datos.fuma,
        )
        return Resultado(
            probabilidad=probabilidad,
            intervalo=intervalo,
            contribuciones=contribuciones,
            factores_mostrados=mostrados,
            recomendaciones=seleccionar(perfil, contribuciones),
        )
