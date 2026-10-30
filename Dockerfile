FROM python:3.14-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
# Solo el modelo NHANES congelado (notebooks/nhanes/03) y su bootstrap (notebooks/nhanes/04);
# el modelo se elige con seleccion.json
COPY models/nhanes ./models/nhanes

EXPOSE 8000

# Render indica el puerto en la variable PORT; en local se usa 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
