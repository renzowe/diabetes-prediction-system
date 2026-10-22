from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import prediccion, resultados, usabilidad
from app.services.predictor import ModeloRiesgo


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crea las tablas que no existan (no modifica las existentes) y carga el modelo una sola vez
    Base.metadata.create_all(bind=engine)
    app.state.modelo = ModeloRiesgo(settings.MODELS_DIR)
    yield


app = FastAPI(
    title="Sistema web predictivo de diagnóstico autorreportado de Diabetes Mellitus",
    description=(
        "API REST que estima la probabilidad de diagnóstico autorreportado de Diabetes Mellitus en adultos "
        "de 30 a 69 años de Lima Metropolitana, con un modelo de regresión logística desarrollado con datos "
        "de la ENDES 2021-2024. Prototipo de investigación: no constituye un diagnóstico médico."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prediccion.router)
app.include_router(usabilidad.router)
app.include_router(resultados.router)


@app.get("/", tags=["Estado"])
def estado():
    return {
        "status": "ok",
        "mensaje": "API de predicción de diabetes activa",
        "modelo": {"archivo": app.state.modelo.archivo, **app.state.modelo.metadatos},
    }
