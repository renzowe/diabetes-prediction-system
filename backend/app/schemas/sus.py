from typing import List

from pydantic import BaseModel, Field, field_validator


class SUSInput(BaseModel):
    """Respuestas del participante a las 10 preguntas de la escala SUS (1 a 5)."""

    participante_codigo: str
    respuestas: List[int] = Field(..., min_length=10, max_length=10)

    @field_validator("respuestas")
    @classmethod
    def validar_rango(cls, v):
        if any(r < 1 or r > 5 for r in v):
            raise ValueError("Cada respuesta debe estar entre 1 y 5")
        return v


class SUSOutput(BaseModel):
    id: int
    puntaje_sus: float
    interpretacion: str
