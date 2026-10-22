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
    title="Sistema web predictivo de HbA1c elevada",
    description=(
        "API REST que estima, con factores no invasivos, la probabilidad de HbA1c >= 5.7 % (compatible con "
        "prediabetes o diabetes) en adultos de 20 a 69 años sin diagnóstico previo de diabetes ni prediabetes, "
        "con un modelo de regresión logística desarrollado con NHANES 2007-2020. Devuelve un intervalo bootstrap, "
        "las principales contribuciones SHAP y recomendaciones de un catálogo con fuentes. Ámbito de aplicación: "
        "Lima Metropolitana. Prototipo de investigación: no constituye un diagnóstico médico."
    ),
    version="3.0.0",
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
