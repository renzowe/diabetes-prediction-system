# Sistema de predicción de riesgo de Diabetes Mellitus Tipo 2

Sistema web que aplica un modelo de Machine Learning para estimar el riesgo de Diabetes
Mellitus Tipo 2 en adultos de 30 a 64 años, desarrollado como parte de un trabajo de tesis
de Ingeniería de Sistemas.

## Arquitectura

El sistema está compuesto por tres capas desacopladas, ejecutadas en contenedores
independientes orquestados con Docker Compose:

| Capa | Tecnología | Función |
|---|---|---|
| Presentación | HTML, CSS, JavaScript (Nginx) | Formulario de evaluación y encuesta de usabilidad |
| Lógica de negocio | FastAPI (API REST) | Validación de datos, ejecución del modelo predictivo |
| Persistencia | PostgreSQL | Almacenamiento de evaluaciones y resultados de usabilidad |

El modelo predictivo (Random Forest) se entrena por separado en los notebooks y se exporta
como artefacto serializado (`.joblib`), que el backend carga al iniciar.

## Estructura del proyecto

```
diabetes-prediction-system/
├── notebooks/          Exploración de datos y entrenamiento del modelo (Jupyter)
├── models/             Modelo entrenado exportado (.joblib)
├── backend/
│   ├── app/            Código de la API (routers, schemas, servicios, modelos ORM)
│   └── tests/          Pruebas automatizadas (pytest)
├── frontend/           Interfaz web (formulario de evaluación y encuesta SUS)
├── Dockerfile          Imagen del backend
└── docker-compose.yml  Orquestación de los tres servicios
```

## Requisitos

- Docker y Docker Compose
- (Opcional, para los notebooks) Python 3.11+ con Jupyter

## Instalación y ejecución

1. Clonar el repositorio y ubicarse en la carpeta del proyecto.

2. Crear el archivo de variables de entorno a partir del ejemplo:

   ```bash
   cp .env.example .env
   ```

   Editar `.env` y definir valores propios para `DB_PASSWORD`, `SECRET_KEY` y `API_KEY`.

3. Levantar los servicios:

   ```bash
   docker-compose up -d --build
   ```

4. Acceder a:

   - Interfaz web: http://localhost
   - Documentación interactiva de la API (Swagger): http://localhost:8000/docs
   - Base de datos (pgAdmin u otro cliente): `localhost:5433`

## Endpoints principales

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| POST | `/predict` | Público | Genera la predicción de riesgo y registra la evaluación |
| POST | `/sus` | Público | Registra las respuestas de la escala de usabilidad SUS |
| GET | `/resultados/evaluaciones` | Requiere clave | Lista las evaluaciones registradas |
| GET | `/resultados/evaluaciones/export` | Requiere clave | Descarga las evaluaciones en formato CSV |
| GET | `/resultados/sus` | Requiere clave | Lista los resultados de usabilidad |
| GET | `/resultados/sus/export` | Requiere clave | Descarga los resultados SUS en formato CSV |

Los endpoints marcados como "requiere clave" están protegidos mediante una clave compartida
que se envía en el encabezado `X-API-Key`, con el fin de evitar que los datos de salud
recolectados queden expuestos públicamente.

## Pruebas automatizadas

```bash
docker-compose exec backend pytest tests/ -v
```

Las pruebas utilizan una base de datos SQLite independiente, por lo que no afectan los datos
almacenados en PostgreSQL.

## Notebooks

- `notebooks/01_data_exploration.ipynb`: comprensión y análisis exploratorio de los datos.
- `notebooks/02_model_training.ipynb`: preparación de datos, balanceo de clases, entrenamiento,
  comparación de modelos y exportación del modelo final.

## Nota sobre los datos

El sistema registra datos de salud seudonimizados mediante un código de participante. No
almacena nombres, documentos de identidad ni datos de contacto. Su uso se realiza en el marco
de una investigación académica, con consentimiento informado de los participantes.
