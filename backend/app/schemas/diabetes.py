from typing import Literal, Optional

from pydantic import BaseModel, Field, computed_field, model_validator

MENSAJE_FUERA_DE_ALCANCE = (
    "Este sistema está pensado para personas sin diagnóstico previo de diabetes ni prediabetes y que no estén "
    "embarazadas. Si ya recibió un diagnóstico o está embarazada, siga las indicaciones de su profesional de salud."
)


class EvaluacionEntrada(BaseModel):
    """Datos que ingresa la persona en el formulario. Corresponden a los predictores del modelo
    (docs/protocolo_nhanes.md, seccion 4), con la redaccion de las preguntas de NHANES traducida; el
    IMC se calcula a partir del peso y la talla."""

    # Pregunta de filtro (criterios de seleccion del protocolo, seccion 3)
    diagnostico_previo: bool = Field(
        ..., description="¿Algún médico le ha dicho que tiene diabetes, prediabetes o azúcar alta en la sangre, o usa insulina o pastillas para la diabetes?"
    )
    embarazo: bool = Field(False, description="¿Está embarazada actualmente? (solo mujeres)")

    edad: int = Field(..., ge=20, le=69, description="Edad en años (el modelo se desarrolló con adultos de 20 a 69 años)")
    sexo: Literal["femenino", "masculino"]
    peso_kg: float = Field(..., ge=30, le=250, description="Peso en kilogramos")
    talla_cm: float = Field(..., ge=120, le=220, description="Talla en centímetros")
    cintura_cm: Optional[float] = Field(None, ge=50, le=180, description="Perímetro abdominal en centímetros (opcional)")
    hipertension: bool = Field(..., description="¿Algún médico le ha dicho que tiene presión alta (hipertensión)?")
    familiar_diabetes: Optional[bool] = Field(
        ..., description="¿Su padre, madre, algún hermano o hermana ha sido diagnosticado con diabetes? (null = no sabe)"
    )
    actividad_fisica: bool = Field(
        ..., description="En una semana típica, ¿realiza deportes, ejercicios o actividades recreativas moderadas o vigorosas durante al menos 10 minutos seguidos?"
    )
    fuma: bool = Field(..., description="¿Fuma cigarrillos actualmente, todos los días o algunos días?")

    # Opcional: solo para vincular la evaluación con la encuesta SUS de un mismo participante
    participante_codigo: Optional[str] = Field(None, max_length=20)

    @computed_field
    @property
    def imc(self) -> float:
        return round(self.peso_kg / (self.talla_cm / 100) ** 2, 2)

    @model_validator(mode="after")
    def validar(self):
        if self.diagnostico_previo or (self.embarazo and self.sexo == "femenino"):
            raise ValueError(MENSAJE_FUERA_DE_ALCANCE)
        if not 12 <= self.imc <= 70:
            raise ValueError(f"El IMC calculado ({self.imc}) está fuera del rango plausible (12-70); revise el peso y la talla")
        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "diagnostico_previo": False,
                "embarazo": False,
                "edad": 52,
                "sexo": "femenino",
                "peso_kg": 72.5,
                "talla_cm": 156,
                "cintura_cm": 98,
                "hipertension": False,
                "familiar_diabetes": True,
                "actividad_fisica": False,
                "fuma": False,
            }
        }
    }


class FactorSalida(BaseModel):
    factor: str
    valor: str = Field(..., description="Dato ingresado por la persona, en lenguaje sencillo")
    efecto: Literal["aumenta", "disminuye"] = Field(..., description="Dirección respecto de la persona promedio de la población de referencia")
    contribucion: float = Field(..., description="Valor SHAP en log-odds respecto de la persona promedio de la población de referencia")


class RecomendacionSalida(BaseModel):
    id: str
    titulo: str
    texto: str
    fuentes: list[str] = Field(..., description="Referencias completas de las guías que sustentan el mensaje")


class ModeloSalida(BaseModel):
    algoritmo: str
    desenlace: str
    datos_entrenamiento: str
    fecha: str


class EvaluacionSalida(BaseModel):
    """Resultado devuelto al frontend. No incluye categorías de riesgo (plan de tesis, 4.6.1)."""

    id: int
    probabilidad: float = Field(..., description="Probabilidad estimada de HbA1c >= 5.7 % (0-1)")
    intervalo: tuple[float, float] = Field(..., description="Intervalo bootstrap del 95 % de la probabilidad estimada")
    nota_intervalo: str
    aviso_edad: Optional[str] = Field(None, description="Aviso de menor capacidad de discriminación en personas de 60 a 69 años (añadido tras la evaluación final)")
    prevalencia_referencia: float = Field(..., description="Proporción ponderada de HbA1c >= 5.7 % en la población de referencia (NHANES, desarrollo)")
    imc: float
    factores: list[FactorSalida] = Field(..., description="Principales contribuciones SHAP (hasta 3, con |SHAP| >= 0.05)")
    nota_factores: str
    recomendaciones: list[RecomendacionSalida] = Field(..., description="Dos o tres mensajes del catálogo de recomendaciones")
    nota_recomendaciones: str
    version_catalogo: str
    mensaje: str
    modelo: ModeloSalida
