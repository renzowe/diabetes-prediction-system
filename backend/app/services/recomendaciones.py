"""Catalogo de recomendaciones preventivas y regla para elegir las que se muestran.

Cada mensaje se activa por un criterio de una guia de salud aplicado a los datos de la persona, no
por el signo de una contribucion del modelo: una contribucion negativa (por ejemplo, realizar
actividad fisica) se explica, pero nunca se convierte en un consejo. Ningun mensaje promete una
reduccion del riesgo. El catalogo y sus fuentes estan en docs/catalogo_recomendaciones.md y se
someten al juicio de expertos (version del catalogo en VERSION_CATALOGO).
"""

from dataclasses import dataclass
from typing import Callable

VERSION_CATALOGO = "1.0 (2026-10-21, pendiente de juicio de expertos)"

FUENTES = {
    "ADA-2": (
        "American Diabetes Association Professional Practice Committee. 2. Diagnosis and Classification of "
        "Diabetes: Standards of Care in Diabetes—2026. Diabetes Care. 2026;49(Suppl 1):S27–S49. "
        "doi:10.2337/dc26-S002"
    ),
    "ADA-3": (
        "American Diabetes Association Professional Practice Committee. 3. Prevention or Delay of Diabetes and "
        "Associated Comorbidities: Standards of Care in Diabetes—2026. Diabetes Care. 2026;49(Suppl 1):S50–S60. "
        "doi:10.2337/dc26-S003"
    ),
    "USPSTF": (
        "US Preventive Services Task Force. Screening for Prediabetes and Type 2 Diabetes: US Preventive Services "
        "Task Force Recommendation Statement. JAMA. 2021;326(8):736–743. doi:10.1001/jama.2021.12531"
    ),
    "OMS-AF": (
        "Bull FC, Al-Ansari SS, Biddle S, et al. World Health Organization 2020 guidelines on physical activity "
        "and sedentary behaviour. Br J Sports Med. 2020;54(24):1451–1462. doi:10.1136/bjsports-2020-102955"
    ),
    "CDC-TAB": (
        "Centers for Disease Control and Prevention. Smoking and Diabetes. Tips From Former Smokers. "
        "https://www.cdc.gov/tobacco/campaign/tips/diseases/diabetes.html (revisado el 13 de octubre de 2023)"
    ),
}


@dataclass(frozen=True)
class Perfil:
    """Datos de la persona que usan los criterios del catalogo."""

    edad: int
    imc: float
    hipertension: bool
    familiar_diabetes: bool | None  # None = no sabe
    actividad_fisica: bool
    fuma: bool


@dataclass(frozen=True)
class Recomendacion:
    id: str
    titulo: str
    texto: str
    fuentes: tuple[str, ...]
    criterio: str                     # descripcion legible del criterio de activacion
    aplica: Callable[[Perfil], bool]
    modificable: bool
    factor: str | None = None         # factor del modelo relacionado (para ordenar por su contribucion)


def _criterio_tamizaje_ada(p: Perfil) -> bool:
    """ADA 2026, recomendaciones 2.12a-b y tabla 2.5, con los datos que pide el sistema: desde los 35
    años, o a cualquier edad con IMC >= 25 y al menos un factor de riesgo (familiar de primer grado
    con diabetes, hipertension o inactividad fisica)."""
    factor_riesgo = bool(p.familiar_diabetes) or p.hipertension or not p.actividad_fisica
    return p.edad >= 35 or (p.imc >= 25 and factor_riesgo)


CATALOGO = [
    Recomendacion(
        id="actividad_fisica",
        titulo="Actividad física",
        texto=(
            "La Organización Mundial de la Salud recomienda que los adultos realicen cada semana entre 150 y 300 "
            "minutos de actividad física aeróbica moderada (por ejemplo, caminar a paso rápido) o entre 75 y 150 "
            "minutos de actividad vigorosa, además de ejercicios de fortalecimiento muscular dos o más días por "
            "semana. Si tiene alguna enfermedad o limitación, consulte con un profesional de salud antes de empezar."
        ),
        fuentes=("OMS-AF", "ADA-3"),
        criterio="No realiza actividades físicas recreativas moderadas o vigorosas en una semana típica",
        aplica=lambda p: not p.actividad_fisica,
        modificable=True,
        factor="actividad",
    ),
    Recomendacion(
        id="peso",
        titulo="Peso corporal",
        texto=(
            "Su índice de masa corporal está en el rango de sobrepeso u obesidad (25 o más). Para adultos con "
            "sobrepeso u obesidad y mayor riesgo de diabetes, la Asociación Americana de Diabetes recomienda "
            "programas de cambio de estilo de vida, con alimentación saludable y actividad física, que buscan una "
            "pérdida de al menos 5 a 7 % del peso inicial. Un profesional de salud o de nutrición puede orientarle "
            "sobre un plan adecuado para usted."
        ),
        fuentes=("ADA-3",),
        criterio="IMC ≥ 25 kg/m²",
        aplica=lambda p: p.imc >= 25,
        modificable=True,
        factor="composicion_corporal",
    ),
    Recomendacion(
        id="tabaco",
        titulo="Tabaco",
        texto=(
            "Fumar es una de las causas de la diabetes tipo 2: según los CDC, las personas que fuman tienen entre "
            "30 y 40 % más probabilidad de desarrollarla que quienes no fuman. La Asociación Americana de Diabetes "
            "indica que las personas con riesgo de diabetes deben recibir orientación para dejar de fumar. Puede "
            "pedir apoyo para dejar de fumar en su establecimiento de salud."
        ),
        fuentes=("CDC-TAB", "ADA-3"),
        criterio="Fuma actualmente (todos los días o algunos días)",
        aplica=lambda p: p.fuma,
        modificable=True,
        factor="tabaquismo",
    ),
    Recomendacion(
        id="prueba_tamizaje",
        titulo="Prueba de laboratorio",
        texto=(
            "Según los criterios de la Asociación Americana de Diabetes, a su perfil le corresponde una prueba de "
            "tamizaje de diabetes y prediabetes, como la hemoglobina glicosilada (HbA1c) o la glucosa en ayunas. "
            "Solo un análisis de laboratorio puede indicar si sus valores son normales. Si el resultado es normal, "
            "la guía recomienda repetir la prueba al menos cada 3 años."
        ),
        fuentes=("ADA-2", "USPSTF"),
        criterio="Edad ≥ 35 años, o IMC ≥ 25 con familiar de primer grado con diabetes, hipertensión o inactividad física",
        aplica=_criterio_tamizaje_ada,
        modificable=False,
    ),
    Recomendacion(
        id="tamizaje_futuro",
        titulo="Cuándo realizarse una prueba",
        texto=(
            "Con los datos ingresados, las guías de la Asociación Americana de Diabetes todavía no indican una "
            "prueba de tamizaje. Recomiendan empezar a los 35 años, o antes si se presenta sobrepeso junto con otro "
            "factor de riesgo, como tener un familiar directo con diabetes, hipertensión o inactividad física."
        ),
        fuentes=("ADA-2",),
        criterio="No cumple el criterio de la prueba de tamizaje",
        aplica=lambda p: not _criterio_tamizaje_ada(p),
        modificable=False,
    ),
    Recomendacion(
        id="sintomas",
        titulo="Síntomas que requieren consulta",
        texto=(
            "Si presenta sed excesiva, necesidad de orinar con mucha frecuencia o pérdida de peso sin causa "
            "aparente, acuda a un establecimiento de salud, aunque la estimación de este sistema sea baja."
        ),
        fuentes=("ADA-2",),
        criterio="Se muestra solo si los criterios anteriores dan menos de dos recomendaciones",
        aplica=lambda p: True,
        modificable=False,
    ),
]

POR_ID = {r.id: r for r in CATALOGO}
MAXIMO, MINIMO = 3, 2


def seleccionar(perfil: Perfil, contribuciones: dict[str, float]) -> list[Recomendacion]:
    """Regla prefijada (protocolo, seccion 13):

    1. Mensajes de factores modificables cuyo criterio se cumple, ordenados por la contribucion del
       factor relacionado (de mayor a menor).
    2. Si corresponde la prueba de tamizaje, se incluye siempre y los modificables se limitan a dos.
    3. Si no corresponde, hasta tres modificables; si quedan menos de dos mensajes se agrega cuándo
       realizarse una prueba y, si aun faltan, los síntomas que requieren consulta.
    """
    modificables = sorted(
        (r for r in CATALOGO if r.modificable and r.aplica(perfil)),
        key=lambda r: contribuciones.get(r.factor, 0.0),
        reverse=True,
    )
    if POR_ID["prueba_tamizaje"].aplica(perfil):
        elegidas = modificables[: MAXIMO - 1] + [POR_ID["prueba_tamizaje"]]
    else:
        elegidas = modificables[:MAXIMO]
        if len(elegidas) < MINIMO:
            elegidas.append(POR_ID["tamizaje_futuro"])
    if len(elegidas) < MINIMO:
        elegidas.append(POR_ID["sintomas"])
    return elegidas
