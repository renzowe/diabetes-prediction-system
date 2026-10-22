import time

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models.evaluacion import Evaluacion
from app.schemas.diabetes import EvaluacionEntrada, EvaluacionSalida, FactorSalida, ModeloSalida, RecomendacionSalida
from app.services.predictor import (
    AVISO_EDAD, EDAD_AVISO, MENSAJE_ALCANCE, NOTA_FACTORES, NOTA_INTERVALO, NOTA_RECOMENDACIONES,
    PREVALENCIA_REFERENCIA, ModeloRiesgo,
)
from app.services.recomendaciones import FUENTES, VERSION_CATALOGO

router = APIRouter(prefix="/predict", tags=["Prediccion"])


def get_modelo(request: Request) -> ModeloRiesgo:
    """El modelo se carga una sola vez al iniciar la aplicacion (ver app.main)."""
    return request.app.state.modelo


@router.post("", response_model=EvaluacionSalida)
def evaluar(datos: EvaluacionEntrada, db: Session = Depends(get_db), modelo: ModeloRiesgo = Depends(get_modelo)):
    """Estima la probabilidad de HbA1c >= 5.7 % con su intervalo bootstrap, devuelve las principales
    contribuciones SHAP y las recomendaciones del catalogo, y guarda la evaluacion."""

    inicio = time.perf_counter()
    resultado = modelo.predecir(datos)
    tiempo_ms = (time.perf_counter() - inicio) * 1000

    registro = Evaluacion(
        **datos.model_dump(exclude={"diagnostico_previo", "embarazo"}),  # incluye el IMC calculado
        probabilidad=resultado.probabilidad,
        intervalo_inferior=resultado.intervalo[0],
        intervalo_superior=resultado.intervalo[1],
        factores_mostrados=",".join(f.clave for f in resultado.factores_mostrados),
        recomendaciones=",".join(r.id for r in resultado.recomendaciones),
        modelo_archivo=modelo.archivo,
        tiempo_prediccion_ms=tiempo_ms,
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)

    return EvaluacionSalida(
        id=registro.id,
        probabilidad=round(resultado.probabilidad, 4),
        intervalo=(round(resultado.intervalo[0], 4), round(resultado.intervalo[1], 4)),
        nota_intervalo=NOTA_INTERVALO,
        aviso_edad=AVISO_EDAD if datos.edad >= EDAD_AVISO else None,
        prevalencia_referencia=PREVALENCIA_REFERENCIA,
        imc=datos.imc,
        factores=[FactorSalida(factor=f.factor, valor=f.valor, efecto=f.efecto, contribucion=f.contribucion)
                  for f in resultado.factores_mostrados],
        nota_factores=NOTA_FACTORES,
        recomendaciones=[RecomendacionSalida(id=r.id, titulo=r.titulo, texto=r.texto, fuentes=[FUENTES[f] for f in r.fuentes])
                         for r in resultado.recomendaciones],
        nota_recomendaciones=NOTA_RECOMENDACIONES,
        version_catalogo=VERSION_CATALOGO,
        mensaje=MENSAJE_ALCANCE,
        modelo=ModeloSalida(**modelo.metadatos),
    )
