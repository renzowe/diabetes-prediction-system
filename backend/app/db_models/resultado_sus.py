from datetime import datetime, timezone

from sqlalchemy import Column, Integer, Float, String, DateTime, JSON

from app.database import Base


class ResultadoSUS(Base):
    """Resultado de la evaluacion de usabilidad (System Usability Scale)."""

    __tablename__ = "resultados_sus"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    participante_codigo = Column(String, nullable=False)
    respuestas = Column(JSON, nullable=False)  
    puntaje_sus = Column(Float, nullable=False)  

