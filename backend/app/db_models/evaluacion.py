from datetime import datetime, timezone

from sqlalchemy import Column, Integer, Float, String, DateTime

from app.database import Base


class Evaluacion(Base):
    """Registro de cada evaluacion de riesgo realizada (manual o mediante el sistema)."""

    __tablename__ = "evaluaciones"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Datos de entrada
    edad = Column(Integer, nullable=False)
    genero = Column(String, nullable=False)
    hipertension = Column(Integer, nullable=False)
    enfermedad_cardiaca = Column(Integer, nullable=False)
    historial_tabaquismo = Column(String, nullable=False)
    imc = Column(Float, nullable=False)
    hba1c = Column(Float, nullable=False)
    glucosa = Column(Float, nullable=False)

    # Resultado del modelo
    prediccion = Column(Integer, nullable=False)          # 0 = sin riesgo, 1 = con riesgo
    probabilidad = Column(Float, nullable=False)          # probabilidad estimada (0-1)

    # Metadatos para el diseno pretest-postest
    momento = Column(String, nullable=True)               # 'manual' | 'sistema'
    tiempo_segundos = Column(Float, nullable=True)
    participante_codigo = Column(String, nullable=True)
