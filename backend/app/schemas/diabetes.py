from typing import Literal, Optional

from pydantic import BaseModel, Field, computed_field, model_validator


class EvaluacionEntrada(BaseModel):
    """Datos que ingresa la persona en el formulario. Corresponden a los predictores del modelo
    web (docs/protocolo_analisis.md, seccion 3); el IMC se calcula a partir del peso y la talla."""

    edad: int = Field(..., ge=30, le=69, description="Edad en años (el modelo se desarrolló con adultos de 30 a 69 años)")
    sexo: Literal["femenino", "masculino"]
    peso_kg: float = Field(..., ge=30, le=250, description="Peso en kilogramos")
    talla_cm: float = Field(..., ge=120, le=220, description="Talla en centímetros")
    cintura_cm: float = Field(..., ge=50, le=170, description="Perímetro abdominal en centímetros")
    hipertension: bool = Field(..., description="¿Algún médico le ha diagnosticado hipertensión arterial?")
    fuma: bool = Field(..., description="¿Ha fumado cigarrillos en los últimos 12 meses?")
    alcohol: bool = Field(..., description="¿Ha consumido bebidas alcohólicas en los últimos 12 meses?")
    dias_frutas: int = Field(..., ge=0, le=7, description="Días de la última semana en que comió frutas")
    dias_verduras: int = Field(..., ge=0, le=7, description="Días de la última semana en que comió ensalada de verduras")

    # Opcional: solo para vincular la evaluación con la encuesta SUS de un mismo participante
    participante_codigo: Optional[str] = Field(None, max_length=20)

    @computed_field
    @property
    def imc(self) -> float:
        return round(self.peso_kg / (self.talla_cm / 100) ** 2, 2)

    @model_validator(mode="after")
    def validar_imc(self):
        if not 12 <= self.imc <= 70:
            raise ValueError(f"El IMC calculado ({self.imc}) está fuera del rango plausible (12-70); revise el peso y la talla")
        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "edad": 52,
                "sexo": "femenino",
                "peso_kg": 72.5,
                "talla_cm": 156,
                "cintura_cm": 98,
                "hipertension": False,
                "fuma": False,
                "alcohol": True,
                "dias_frutas": 4,
                "dias_verduras": 2,
            }
        }
    }


class FactorSalida(BaseModel):
    factor: str
    valor: str = Field(..., description="Dato ingresado por la persona, en lenguaje sencillo")
    efecto: Literal["aumenta", "disminuye"] = Field(..., description="Dirección respecto de la persona promedio de la población de referencia")
    contribucion: float = Field(..., description="Contribución al log-odds respecto de la persona promedio de la población de referencia")


class ModeloSalida(BaseModel):
    algoritmo: str
    desenlace: str
    datos_entrenamiento: str
    fecha: str


class EvaluacionSalida(BaseModel):
    """Resultado devuelto al frontend. No incluye categorías de riesgo: no existen umbrales
    clínicos validados para una probabilidad de diagnóstico autorreportado (plan de tesis, 4.6.1)."""

    id: int
    probabilidad: float = Field(..., description="Probabilidad estimada de diagnóstico autorreportado de DM (0-1)")
    prevalencia_referencia: float = Field(..., description="Proporción de diagnóstico autorreportado en la población de referencia (ENDES 2021-2024)")
    imc: float
    factores: list[FactorSalida] = Field(..., description="Solo los factores que se muestran al usuario (edad, sexo, composición corporal e hipertensión)")
    nota_factores: str
    mensaje: str
    modelo: ModeloSalida
