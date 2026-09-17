from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models.evaluacion import Evaluacion
from app.schemas.diabetes import DiabetesInput, DiabetesOutput
from app.services import predictor
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter(prefix="/predict", tags=["Prediccion"])


@router.post("", response_model=DiabetesOutput)
def predecir_riesgo(data: DiabetesInput, db: Session = Depends(get_db)):
    """Recibe los datos del participante, ejecuta el modelo y guarda el registro."""

    prediccion, probabilidad = predictor.predict(data)
    riesgo = predictor.nivel_riesgo(probabilidad)

    registro = Evaluacion(
        edad=data.edad,
        genero=data.genero,
        hipertension=data.hipertension,
        enfermedad_cardiaca=data.enfermedad_cardiaca,
        historial_tabaquismo=data.historial_tabaquismo,
        imc=data.imc,
        hba1c=data.hba1c,
        glucosa=data.glucosa,
        prediccion=prediccion,
        probabilidad=probabilidad,
        momento=data.momento,
        tiempo_segundos=data.tiempo_segundos,
        participante_codigo=data.participante_codigo,
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)

    return DiabetesOutput(
        id=registro.id,
        prediccion=prediccion,
        probabilidad=round(probabilidad, 4),
        nivel_riesgo=riesgo,
    )

