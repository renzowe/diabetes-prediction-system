import os

# Se define ANTES de importar la app: usa una base de datos SQLite exclusiva
# para pruebas, separada de la base de datos real (PostgreSQL) del proyecto.
os.environ["DATABASE_URL"] = "sqlite:///./test_db.sqlite3"
os.environ["API_KEY"] = "test-key-123"

import pytest
from fastapi.testclient import TestClient

from app.main import app  # noqa: E402  (import tardio intencional, ver arriba)


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c

    # Limpieza: elimina el archivo de base de datos de prueba al terminar
    if os.path.exists("test_db.sqlite3"):
        os.remove("test_db.sqlite3")


@pytest.fixture
def auth_headers():
    return {"X-API-Key": "test-key-123"}


@pytest.fixture
def payload_bajo_riesgo():
    return {
        "edad": 32,
        "genero": "Female",
        "hipertension": 0,
        "enfermedad_cardiaca": 0,
        "historial_tabaquismo": "never",
        "imc": 22.0,
        "hba1c": 5.0,
        "glucosa": 90,
    }


@pytest.fixture
def payload_alto_riesgo():
    return {
        "edad": 62,
        "genero": "Male",
        "hipertension": 1,
        "enfermedad_cardiaca": 1,
        "historial_tabaquismo": "current",
        "imc": 36.0,
        "hba1c": 9.5,
        "glucosa": 270,
    }