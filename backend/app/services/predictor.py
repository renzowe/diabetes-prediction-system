"""Carga el modelo web congelado en notebooks/03 y calcula la probabilidad estimada y las
contribuciones de los factores a cada resultado."""

import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.schemas.diabetes import EvaluacionEntrada

# Predictor del modelo -> factor que se explica. IMC y perimetro abdominal estan muy correlacionados
# (r = 0.90) y el modelo estima el efecto de cada uno a igual valor del otro; por eso se suman en un
# solo factor.
FACTOR_DE_PREDICTOR = {
    "edad": "edad",
    "hombre": "sexo",
    "imc": "composicion_corporal",
    "cintura": "composicion_corporal",
    "hta": "hipertension",
    "tabaco": "tabaco",
    "alcohol": "alcohol",
    "frutas_dias": "frutas",
    "verduras_dias": "verduras",
}

# Factores cuya contribucion se muestra al usuario, con su etiqueta y el valor que ingreso la persona.
# Tabaco, alcohol, frutas y verduras se usan en el modelo pero no se muestran: sus asociaciones con el
# diagnostico reportado son pequeñas o de causa incierta (docs/analisis_alcohol.md).
FACTORES_MOSTRADOS = {
    "edad": ("Edad", lambda d: f"{d.edad} años"),
    "sexo": ("Sexo", lambda d: "Mujer" if d.sexo == "femenino" else "Hombre"),
    "composicion_corporal": (
        "Composición corporal",
        lambda d: f"IMC {d.imc:.1f} · perímetro abdominal {d.cintura_cm:.0f} cm",
    ),
    "hipertension": (
        "Hipertensión arterial",
        lambda d: "Con diagnóstico médico" if d.hipertension else "Sin diagnóstico médico",
    ),
}

# Proporcion de diagnostico autorreportado en los datos de desarrollo (562 / 8,909; notebooks/01)
PREVALENCIA_REFERENCIA = 562 / 8909

MENSAJE_ALCANCE = (
    "Este resultado indica qué tanto se parece su perfil al de las personas que, en la encuesta "
    "ENDES, reportaron haber recibido un diagnóstico de diabetes. No es un diagnóstico ni indica "
    "si usted tiene diabetes. Si desea conocer su estado, solicite una prueba de glucosa en un "
    "establecimiento de salud."
)

NOTA_FACTORES = (
    "Estas contribuciones describen cómo el modelo combinó sus datos para obtener la estimación, en "
    "comparación con una persona promedio de la población de referencia (adultos de 30 a 69 años de "
    "Lima Metropolitana, ENDES 2021-2024). No son consejos de salud ni efectos causales: no indican "
    "que cambiar un dato vaya a modificar su probabilidad real de tener diabetes. El modelo también "
    "usa sus respuestas sobre tabaco, alcohol, frutas y verduras, pero su contribución no se muestra "
    "porque su asociación con el diagnóstico reportado es pequeña o de causa incierta."
)


@dataclass(frozen=True)
class Factor:
    factor: str
    valor: str           # dato de la persona, en lenguaje sencillo
    efecto: str          # "aumenta" | "disminuye" (respecto de la persona promedio)
    contribucion: float  # en log-odds


@dataclass(frozen=True)
class Resultado:
    probabilidad: float
    contribuciones: dict[str, float]  # todos los factores, incluidos los que no se muestran
    factores_mostrados: list[Factor]


class ModeloRiesgo:
    """Envuelve el artefacto guardado por notebooks/03 (diccionario con el pipeline y sus metadatos)."""

    def __init__(self, directorio: str | Path):
        directorio = Path(directorio)
        seleccion = json.loads((directorio / "seleccion.json").read_text(encoding="utf-8"))
        self.archivo = seleccion["web"]
        artefacto = joblib.load(directorio / self.archivo)

        pipeline = artefacto["modelo"]
        if not (isinstance(pipeline, Pipeline) and isinstance(pipeline.named_steps["modelo"], LogisticRegression)):
            raise TypeError("La explicacion de factores requiere un pipeline de regresion logistica")

        self.predictores: list[str] = artefacto["predictores"]
        self.metadatos = {k: artefacto[k] for k in ("algoritmo", "desenlace", "datos_entrenamiento", "fecha")}
        self._pipeline = pipeline
        self._prep = pipeline.named_steps["prep"]
        self._coef = pipeline.named_steps["modelo"].coef_[0]
        self.intercepto = float(pipeline.named_steps["modelo"].intercept_[0])
        # get_feature_names_out devuelve "continuas__edad"; se recupera el nombre del predictor
        self._columnas = [n.split("__", 1)[1] for n in self._prep.get_feature_names_out()]

    def _fila(self, datos: EvaluacionEntrada) -> pd.DataFrame:
        valores = {
            "edad": datos.edad,
            "hombre": 1.0 if datos.sexo == "masculino" else 0.0,
            "imc": datos.imc,
            "cintura": datos.cintura_cm,
            "hta": float(datos.hipertension),
            "tabaco": float(datos.fuma),
            "alcohol": float(datos.alcohol),
            "frutas_dias": datos.dias_frutas,
            "verduras_dias": datos.dias_verduras,
        }
        return pd.DataFrame([valores])[self.predictores]

    def predecir(self, datos: EvaluacionEntrada) -> Resultado:
        fila = self._fila(datos)
        probabilidad = float(self._pipeline.predict_proba(fila)[0, 1])

        # Con variables estandarizadas, coeficiente x valor estandarizado es la contribucion de cada
        # variable al log-odds respecto de la persona promedio (equivale a SHAP en un modelo lineal).
        contribuciones: dict[str, float] = {}
        for columna, valor in zip(self._columnas, self._coef * self._prep.transform(fila)[0]):
            factor = FACTOR_DE_PREDICTOR[columna]
            contribuciones[factor] = contribuciones.get(factor, 0.0) + float(valor)

        mostrados = [
            Factor(
                factor=FACTORES_MOSTRADOS[clave][0],
                valor=FACTORES_MOSTRADOS[clave][1](datos),
                efecto="aumenta" if contribuciones[clave] > 0 else "disminuye",
                contribucion=round(contribuciones[clave], 4),
            )
            for clave in sorted(FACTORES_MOSTRADOS, key=lambda k: abs(contribuciones[k]), reverse=True)
        ]
        return Resultado(probabilidad=probabilidad, contribuciones=contribuciones, factores_mostrados=mostrados)
