FROM python:3.14-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
# Solo los modelos congelados en notebooks/03 (models/v2); el modelo web se elige con seleccion.json
COPY models/v2 ./models/v2

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
