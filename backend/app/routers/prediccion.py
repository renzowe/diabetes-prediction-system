import time

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models.evaluacion import Evaluacion
from app.schemas.diabetes import EvaluacionEntrada, EvaluacionSalida, FactorSalida, ModeloSalida
from app.services.predictor import MENSAJE_ALCANCE, NOTA_FACTORES, PREVALENCIA_REFERENCIA, ModeloRiesgo

router = APIRouter(prefix="/predict", tags=["Prediccion"])


def get_modelo(request: Request) -> ModeloRiesgo:
    """El modelo se carga una sola vez al iniciar la aplicacion (ver app.main)."""
    return request.app.state.modelo


@router.post("", response_model=EvaluacionSalida)
def evaluar(datos: EvaluacionEntrada, db: Session = Depends(get_db), modelo: ModeloRiesgo = Depends(get_modelo)):
    """Estima la probabilidad de diagnostico autorreportado de DM, devuelve las contribuciones de
    los factores que se muestran al usuario y guarda la evaluacion."""

    inicio = time.perf_counter()
    resultado = modelo.predecir(datos)
    tiempo_ms = (time.perf_counter() - inicio) * 1000

    registro = Evaluacion(
        **datos.model_dump(),  # incluye el IMC calculado
        probabilidad=resultado.probabilidad,
        modelo_archivo=modelo.archivo,
        tiempo_prediccion_ms=tiempo_ms,
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)

    return EvaluacionSalida(
        id=registro.id,
        probabilidad=round(resultado.probabilidad, 4),
        prevalencia_referencia=round(PREVALENCIA_REFERENCIA, 4),
        imc=datos.imc,
        factores=[FactorSalida(**vars(f)) for f in resultado.factores_mostrados],
        nota_factores=NOTA_FACTORES,
        mensaje=MENSAJE_ALCANCE,
        modelo=ModeloSalida(**modelo.metadatos),
    )
