from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
 
from app.config import settings
 
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
 
 
def verificar_api_key(api_key: str = Security(_api_key_header)) -> None:
    """Protege endpoints que exponen datos de varios participantes a la vez.
 
    No es un sistema de autenticacion de usuarios (no hay login ni roles):
    es una clave compartida que solo el investigador conoce, pensada para
    evitar que cualquier persona que encuentre la URL publica pueda
    descargar los datos de salud recolectados."""
    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clave de acceso invalida o ausente (encabezado X-API-Key).",
        )
 