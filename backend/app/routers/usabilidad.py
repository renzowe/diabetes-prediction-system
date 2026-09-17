from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models.resultado_sus import ResultadoSUS
from app.schemas.sus import SUSInput, SUSOutput

router = APIRouter(prefix="/sus", tags=["Usabilidad"])


def _calcular_puntaje_sus(respuestas: list[int]) -> float:
    """Formula estandar de la System Usability Scale (Brooke, 1996).
    Preguntas impares (1,3,5,7,9): puntaje = respuesta - 1
    Preguntas pares  (2,4,6,8,10): puntaje = 5 - respuesta
    Suma total x 2.5 -> puntaje final de 0 a 100."""
    total = 0
    for i, r in enumerate(respuestas):
        posicion = i + 1
        total += (r - 1) if posicion % 2 != 0 else (5 - r)
    return total * 2.5


def _interpretar(puntaje: float) -> str:
    if puntaje >= 80.3:
        return "Excelente"
    elif puntaje >= 68:
        return "Buena"
    elif puntaje >= 51:
        return "Aceptable"
    return "Deficiente"


@router.post("", response_model=SUSOutput)
def registrar_sus(data: SUSInput, db: Session = Depends(get_db)):
    puntaje = _calcular_puntaje_sus(data.respuestas)

    registro = ResultadoSUS(
        participante_codigo=data.participante_codigo,
        respuestas=data.respuestas,
        puntaje_sus=puntaje,
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)

    return SUSOutput(
        id=registro.id,
        puntaje_sus=puntaje,
        interpretacion=_interpretar(puntaje),
    )

