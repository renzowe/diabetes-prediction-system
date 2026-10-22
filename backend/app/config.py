from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracion de la aplicacion, leida desde variables de entorno o del archivo .env.

    Las variables del .env que no pertenecen al backend (por ejemplo DB_USER, usada solo por
    docker-compose) se ignoran en lugar de provocar un error al iniciar."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite:///./local_dev.db"
    API_KEY: str = "change-me-too"
    # Carpeta con los modelos congelados en notebooks/03; el modelo web se toma de seleccion.json
    MODELS_DIR: str = "models/v2"
    # Origenes permitidos por CORS, en formato JSON: ["https://mi-frontend.com"]
    CORS_ORIGINS: list[str] = ["*"]


settings = Settings()
