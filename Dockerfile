FROM python:3.14-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
# Solo el modelo NHANES congelado (notebooks/nhanes/03) y su bootstrap (notebooks/nhanes/04);
# el modelo se elige con seleccion.json
COPY models/nhanes ./models/nhanes

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
