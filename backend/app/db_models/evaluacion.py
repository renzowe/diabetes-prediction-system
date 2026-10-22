from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String

from app.database import Base


class Evaluacion(Base):
    """Registro de cada evaluacion realizada con el sistema web.

    Usa una tabla nueva (evaluaciones_riesgo): la tabla anterior (evaluaciones), con los campos
    del modelo antiguo, se conserva sin cambios en la base de datos."""

    __tablename__ = "evaluaciones_riesgo"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Datos de entrada (sin nombres ni documentos de identidad, Ley N.° 29733)
    edad = Column(Integer, nullable=False)
    sexo = Column(String, nullable=False)
    peso_kg = Column(Float, nullable=False)
    talla_cm = Column(Float, nullable=False)
    imc = Column(Float, nullable=False)
    cintura_cm = Column(Float, nullable=False)
    hipertension = Column(Boolean, nullable=False)
    fuma = Column(Boolean, nullable=False)
    alcohol = Column(Boolean, nullable=False)
    dias_frutas = Column(Integer, nullable=False)
    dias_verduras = Column(Integer, nullable=False)

    # Resultado y rendimiento (indicador D3 de la variable independiente: tiempo de respuesta)
    probabilidad = Column(Float, nullable=False)
    modelo_archivo = Column(String, nullable=False)
    tiempo_prediccion_ms = Column(Float, nullable=False)

    participante_codigo = Column(String, nullable=True)
