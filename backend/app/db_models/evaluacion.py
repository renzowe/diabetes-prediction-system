from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String

from app.database import Base


class Evaluacion(Base):
    """Registro de cada evaluacion realizada con el sistema web (modelo NHANES).

    Usa una tabla nueva (evaluaciones_nhanes): las tablas anteriores (evaluaciones y
    evaluaciones_riesgo), con los campos de los modelos de fases previas, se conservan sin cambios."""

    __tablename__ = "evaluaciones_nhanes"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Datos de entrada (sin nombres ni documentos de identidad, Ley N.° 29733). Las respuestas de
    # filtro no se guardan: si la persona tiene diagnostico previo o esta embarazada no se estima.
    edad = Column(Integer, nullable=False)
    sexo = Column(String, nullable=False)
    peso_kg = Column(Float, nullable=False)
    talla_cm = Column(Float, nullable=False)
    imc = Column(Float, nullable=False)
    cintura_cm = Column(Float, nullable=True)
    hipertension = Column(Boolean, nullable=False)
    familiar_diabetes = Column(Boolean, nullable=True)
    actividad_fisica = Column(Boolean, nullable=False)
    fuma = Column(Boolean, nullable=False)

    # Resultado: probabilidad, intervalo bootstrap y lo que se mostro (claves separadas por comas)
    probabilidad = Column(Float, nullable=False)
    intervalo_inferior = Column(Float, nullable=False)
    intervalo_superior = Column(Float, nullable=False)
    factores_mostrados = Column(String, nullable=False)
    recomendaciones = Column(String, nullable=False)

    # Rendimiento (indicador D3 de la variable independiente: tiempo de respuesta)
    modelo_archivo = Column(String, nullable=False)
    tiempo_prediccion_ms = Column(Float, nullable=False)

    participante_codigo = Column(String, nullable=True)
