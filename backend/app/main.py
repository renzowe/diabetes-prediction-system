
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import prediccion, usabilidad, resultados

# Crea las tablas si no existen (en un proyecto mayor se usaria Alembic)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema de Prediccion de Riesgo de Diabetes",
    description="API REST para la identificacion temprana del riesgo de Diabetes Mellitus Tipo 2 mediante Machine Learning.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en produccion, restringir al dominio del frontend
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prediccion.router)
app.include_router(usabilidad.router)
app.include_router(resultados.router)


@app.get("/", tags=["Estado"])
def estado():
    return {"status": "ok", "mensaje": "API de prediccion de diabetes activa"}