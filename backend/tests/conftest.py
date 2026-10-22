import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

# Se define ANTES de importar la app: base de datos SQLite exclusiva para pruebas y rutas absolutas
# para que las pruebas funcionen desde cualquier carpeta.
os.environ["DATABASE_URL"] = "sqlite:///./test_db.sqlite3"
os.environ["API_KEY"] = "test-key-123"
os.environ["MODELS_DIR"] = str(RAIZ / "models" / "v2")

import pytest
from fastapi.testclient import TestClient

from app.database import engine  # noqa: E402
from app.main import app  # noqa: E402  (import tardio intencional, ver arriba)


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c

    # Limpieza: cierra las conexiones (en Windows el archivo queda bloqueado) y elimina la BD de prueba
    engine.dispose()
    if os.path.exists("test_db.sqlite3"):
        os.remove("test_db.sqlite3")


@pytest.fixture
def auth_headers():
    return {"X-API-Key": "test-key-123"}


@pytest.fixture
def payload_perfil_bajo():
    return {
        "edad": 32,
        "sexo": "femenino",
        "peso_kg": 55,
        "talla_cm": 160,
        "cintura_cm": 76,
        "hipertension": False,
        "fuma": False,
        "alcohol": True,
        "dias_frutas": 5,
        "dias_verduras": 3,
    }


@pytest.fixture
def payload_perfil_alto():
    return {
        "edad": 66,
        "sexo": "masculino",
        "peso_kg": 92,
        "talla_cm": 165,
        "cintura_cm": 115,
        "hipertension": True,
        "fuma": True,
        "alcohol": False,
        "dias_frutas": 2,
        "dias_verduras": 1,
    }
