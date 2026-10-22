import csv
import io
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models.evaluacion import Evaluacion
from app.db_models.resultado_sus import ResultadoSUS
from app.security import verificar_api_key

router = APIRouter(
    prefix="/resultados",
    tags=["Resultados"],
    dependencies=[Depends(verificar_api_key)],
)

LIMITE_RESPUESTA_MS = 2000  # meta del indicador de rendimiento (plan de tesis, 3.4.1)


def _evaluacion_a_dict(e: Evaluacion) -> dict:
    return {
        "id": e.id,
        "fecha": e.fecha.isoformat() if e.fecha else None,
        "participante_codigo": e.participante_codigo,
        "edad": e.edad,
        "sexo": e.sexo,
        "peso_kg": e.peso_kg,
        "talla_cm": e.talla_cm,
        "imc": e.imc,
        "cintura_cm": e.cintura_cm,
        "hipertension": e.hipertension,
        "familiar_diabetes": e.familiar_diabetes,
        "actividad_fisica": e.actividad_fisica,
        "fuma": e.fuma,
        "probabilidad": e.probabilidad,
        "intervalo_inferior": e.intervalo_inferior,
        "intervalo_superior": e.intervalo_superior,
        "factores_mostrados": e.factores_mostrados,
        "recomendaciones": e.recomendaciones,
        "modelo_archivo": e.modelo_archivo,
        "tiempo_prediccion_ms": e.tiempo_prediccion_ms,
    }


def _sus_a_dict(s: ResultadoSUS) -> dict:
    return {
        "id": s.id,
        "fecha": s.fecha.isoformat() if s.fecha else None,
        "participante_codigo": s.participante_codigo,
        "respuestas": s.respuestas,
        "puntaje_sus": s.puntaje_sus,
    }


def _csv_response(filas: list[dict], nombre_archivo: str) -> StreamingResponse:
    buffer = io.StringIO()
    if filas:
        writer = csv.DictWriter(buffer, fieldnames=list(filas[0].keys()))
        writer.writeheader()
        writer.writerows(filas)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


@router.get("/evaluaciones")
def listar_evaluaciones(participante_codigo: Optional[str] = None, db: Session = Depends(get_db)):
    """Lista las evaluaciones guardadas, opcionalmente filtradas por codigo de participante."""
    query = db.query(Evaluacion)
    if participante_codigo:
        query = query.filter(Evaluacion.participante_codigo == participante_codigo)
    return [_evaluacion_a_dict(e) for e in query.order_by(Evaluacion.id).all()]


@router.get("/evaluaciones/export")
def exportar_evaluaciones(db: Session = Depends(get_db)):
    """Descarga todas las evaluaciones en un archivo CSV, listo para Excel/SPSS."""
    filas = [_evaluacion_a_dict(e) for e in db.query(Evaluacion).order_by(Evaluacion.id).all()]
    return _csv_response(filas, "evaluaciones.csv")


@router.get("/sus")
def listar_sus(db: Session = Depends(get_db)):
    """Lista los resultados de la escala de usabilidad SUS."""
    return [_sus_a_dict(s) for s in db.query(ResultadoSUS).order_by(ResultadoSUS.id).all()]


@router.get("/sus/export")
def exportar_sus(db: Session = Depends(get_db)):
    """Descarga los resultados SUS en un archivo CSV."""
    filas = [_sus_a_dict(s) for s in db.query(ResultadoSUS).order_by(ResultadoSUS.id).all()]
    return _csv_response(filas, "resultados_sus.csv")


@router.get("/resumen")
def resumen(db: Session = Depends(get_db)):
    """Indicadores de calidad del sistema para el objetivo especifico 4: rendimiento
    (tiempo de prediccion) y usabilidad (puntaje SUS)."""
    tiempos = np.array([t for (t,) in db.query(Evaluacion.tiempo_prediccion_ms).all()])
    puntajes = np.array([p for (p,) in db.query(ResultadoSUS.puntaje_sus).all()])
    return {
        "evaluaciones": int(tiempos.size),
        "tiempo_prediccion_ms": None if tiempos.size == 0 else {
            "media": round(float(tiempos.mean()), 2),
            "p95": round(float(np.percentile(tiempos, 95)), 2),
            "maximo": round(float(tiempos.max()), 2),
            f"porcentaje_menor_a_{LIMITE_RESPUESTA_MS}_ms": round(100 * float((tiempos < LIMITE_RESPUESTA_MS).mean()), 1),
        },
        "encuestas_sus": int(puntajes.size),
        "puntaje_sus": None if puntajes.size == 0 else {
            "media": round(float(puntajes.mean()), 2),
            "desviacion_estandar": round(float(puntajes.std(ddof=1)), 2) if puntajes.size > 1 else None,
            "minimo": float(puntajes.min()),
            "maximo": float(puntajes.max()),
        },
    }
