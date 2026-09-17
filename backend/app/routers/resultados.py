import csv
import io
from typing import Optional
 
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
 
 
def _evaluacion_a_dict(e: Evaluacion) -> dict:
    return {
        "id": e.id,
        "fecha": e.fecha.isoformat() if e.fecha else None,
        "participante_codigo": e.participante_codigo,
        "momento": e.momento,
        "edad": e.edad,
        "genero": e.genero,
        "hipertension": e.hipertension,
        "enfermedad_cardiaca": e.enfermedad_cardiaca,
        "historial_tabaquismo": e.historial_tabaquismo,
        "imc": e.imc,
        "hba1c": e.hba1c,
        "glucosa": e.glucosa,
        "prediccion": e.prediccion,
        "probabilidad": e.probabilidad,
        "tiempo_segundos": e.tiempo_segundos,
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
def listar_evaluaciones(
    momento: Optional[str] = None,
    participante_codigo: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Lista las evaluaciones guardadas. Permite filtrar por momento (manual/sistema)
    y/o por codigo de participante."""
    query = db.query(Evaluacion)
    if momento:
        query = query.filter(Evaluacion.momento == momento)
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