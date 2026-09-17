from pydantic_settings import BaseSettings
 
 
class Settings(BaseSettings):
    """Configuracion de la aplicacion, leida desde variables de entorno (.env)."""
 
    DATABASE_URL: str = "sqlite:///./local_dev.db"
    SECRET_KEY: str = "change-me"
    MODEL_PATH: str = "models/diabetes_model_v1.joblib"
    API_KEY: str = "change-me-too"
 
    class Config:
        env_file = ".env"
 
 
settings = Settings()