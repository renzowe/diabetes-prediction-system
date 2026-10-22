# Sistema web predictivo de HbA1c elevada

Sistema web que estima, solo con factores no invasivos, la probabilidad de HbA1c ≥ 5.7 %
(compatible con prediabetes o diabetes) en adultos de 20 a 69 años sin diagnóstico previo de
diabetes ni prediabetes. El modelo se desarrolló con datos de NHANES 2007–marzo 2020 y el
sistema se aplica en Lima Metropolitana. Es parte de una tesis de Ingeniería de Sistemas (UNFV).

El resultado muestra la probabilidad con su intervalo bootstrap, las principales contribuciones
de los datos de la persona (valores SHAP) y dos o tres recomendaciones preventivas de un
catálogo con fuentes (`docs/catalogo_recomendaciones.md`). No es un diagnóstico.

## Arquitectura

El sistema está compuesto por tres capas desacopladas, ejecutadas en contenedores
independientes orquestados con Docker Compose:

| Capa | Tecnología | Función |
|---|---|---|
| Presentación | HTML, CSS, JavaScript (Nginx) | Formulario de evaluación y encuesta de usabilidad |
| Lógica de negocio | FastAPI (API REST) | Validación de datos, ejecución del modelo predictivo |
| Persistencia | PostgreSQL | Almacenamiento de evaluaciones y resultados de usabilidad |

El modelo predictivo (regresión logística, elegida frente a Random Forest, XGBoost y LightGBM
según el protocolo) se entrena en los notebooks y se congela en `models/nhanes/` junto con sus
remuestreos bootstrap; el backend los carga al iniciar.

## Estructura del proyecto

```
diabetes-prediction-system/
├── docs/               Protocolos de análisis, catálogo de recomendaciones y borradores
├── notebooks/nhanes/   Integración, partición, factores, entrenamiento, bootstrap y evaluación final
├── notebooks/          (01–06) Fase exploratoria previa con ENDES
├── particion/          Partición desarrollo/prueba y huellas de los archivos fuente
├── models/nhanes/      Modelos congelados (.joblib), bootstrap y selección
├── resultados/nhanes/  Tablas y figuras de cada notebook
├── backend/
│   ├── app/            Código de la API (routers, schemas, servicios, modelos ORM)
│   └── tests/          Pruebas automatizadas (pytest)
├── frontend/           Interfaz web (formulario de evaluación y encuesta SUS)
├── Dockerfile          Imagen del backend
└── docker-compose.yml  Orquestación de los tres servicios
```

## Requisitos

- Docker y Docker Compose
- (Opcional, para los notebooks) Python 3.14 con Jupyter y las dependencias de
  `notebooks/requirements.txt`. Los datos de NHANES se descargan automáticamente del CDC al
  ejecutar `notebooks/nhanes/01_integracion_particion.ipynb`

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
| POST | `/predict` | Público | Estima la probabilidad con su intervalo, contribuciones y recomendaciones, y registra la evaluación |
| POST | `/sus` | Público | Registra las respuestas de la escala de usabilidad SUS |
| GET | `/resultados/evaluaciones` | Requiere clave | Lista las evaluaciones registradas |
| GET | `/resultados/evaluaciones/export` | Requiere clave | Descarga las evaluaciones en formato CSV |
| GET | `/resultados/sus` | Requiere clave | Lista los resultados de usabilidad |
| GET | `/resultados/sus/export` | Requiere clave | Descarga los resultados SUS en formato CSV |
| GET | `/resultados/resumen` | Requiere clave | Indicadores de rendimiento (tiempo de respuesta) y usabilidad (SUS) |

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

Fase NHANES (`notebooks/nhanes/`), según `docs/protocolo_nhanes.md`:

1. `01_integracion_particion`: descarga, integración y partición por conglomerados.
2. `02_factores_asociados`: OE1 / HE1 (solo desarrollo).
3. `03_entrenamiento_modelo`: comparación de algoritmos, selección, calibración y congelamiento (OE2).
4. `04_intervalos_bootstrap`: intervalos individuales por bootstrap por conglomerado.
5. `05_evaluacion_final`: evaluación única con el conjunto de prueba reservado (OE2, OE3).

Los notebooks 01–06 de la carpeta `notebooks/` corresponden a la fase exploratoria previa con
la ENDES (`docs/protocolo_analisis.md`), que motivó el cambio a NHANES.

## Nota sobre los datos

El sistema registra datos de salud seudonimizados mediante un código de participante. No
almacena nombres, documentos de identidad ni datos de contacto. Su uso se realiza en el marco
de una investigación académica, con consentimiento informado de los participantes.
