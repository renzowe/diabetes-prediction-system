from typing import Literal, Optional

from pydantic import BaseModel, Field


class DiabetesInput(BaseModel):
    """Datos ingresados por el participante en el formulario de evaluacion."""

    edad: int = Field(..., ge=30, le=64, description="Edad en anios (30-64)")
    genero: Literal["Female", "Male", "Other"]
    hipertension: Literal[0, 1]
    enfermedad_cardiaca: Literal[0, 1]
    historial_tabaquismo: Literal["never", "No Info", "former", "not current", "ever", "current"]
    imc: float = Field(..., gt=10, lt=70, description="Indice de masa corporal")
    hba1c: float = Field(..., gt=3, lt=15, description="Nivel de HbA1c (%)")
    glucosa: float = Field(..., gt=50, lt=400, description="Glucosa en sangre (mg/dL)")

    # Opcionales, solo se usan si esta evaluacion es parte del pretest/postest
    momento: Optional[Literal["manual", "sistema"]] = None
    tiempo_segundos: Optional[float] = None
    participante_codigo: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "edad": 45,
                "genero": "Female",
                "hipertension": 0,
                "enfermedad_cardiaca": 0,
                "historial_tabaquismo": "never",
                "imc": 27.5,
                "hba1c": 6.0,
                "glucosa": 140,
                "momento": "sistema",
                "tiempo_segundos": 42.3,
                "participante_codigo": "P01"
            }
        }
    }


class DiabetesOutput(BaseModel):
    """Resultado de la prediccion devuelto al frontend."""

    id: int
    prediccion: int
    probabilidad: float
    nivel_riesgo: Literal["bajo", "moderado", "alto"]

