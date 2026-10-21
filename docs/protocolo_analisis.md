# Protocolo de análisis del modelo predictivo

Fija las decisiones de preparación, modelado y evaluación **antes** de entrenar cualquier modelo,
conforme al plan de tesis (v4, secciones 4.4, 4.6.1 y 4.9). Cualquier cambio posterior se registra
en la sección 9 con fecha y motivo, y siempre antes de la evaluación final.

## 1. Desenlace

`DM_AUTORREPORTADA` = 1 si `QS109 = 1` («¿Alguna vez en su vida un médico le ha diagnosticado
diabetes o “azúcar alta” en la sangre?»), 0 si `QS109 = 2`. Se excluyen «no sabe» (8) y los no
respondidos. La redacción es idéntica en los cuestionarios 2021–2025 y excluye la diabetes
gestacional.

Todas las métricas se interpretan como concordancia con el diagnóstico autorreportado, no como
detección de diabetes. La ENDES no incluye glucosa ni HbA1c.

## 2. Datos y separación desarrollo / evaluación

Generados por `notebooks/01_integracion_endes.ipynb` a partir de los módulos 1629, 1630 y 1640 de la ENDES:

| Archivo | Años | Registros | Uso |
|---|---|---|---|
| `data/processed/endes_lima_desarrollo_2021_2024.csv` | 2021–2024 | 8,909 (562 casos) | Todo el desarrollo |
| `data/processed/endes_lima_evaluacion_2025.csv` | 2025 | 1,990 | Solo la evaluación final |

**Regla:** ningún notebook, salvo el de evaluación final (`notebooks/04_evaluacion_final.ipynb`), lee el archivo de evaluación.
Ese script se ejecuta una sola vez, con el modelo congelado y su versión registrada en Git.

Criterios de selección: Lima Metropolitana (`SHREGION = 1`), 30 a 69 años (`QS23`), `QS109` válido y
peso, talla y perímetro abdominal medidos con valores válidos (< 999).

## 3. Predictores y codificación

| Predictor | Variable ENDES | Codificación | Modelo web |
|---|---|---|---|
| Edad | `QS23` | Años, numérica | Sí |
| Sexo | `QSSEXO` | 1 = hombre, 0 = mujer | Sí |
| IMC | `QS900`, `QS901` | kg / m² | Sí |
| Perímetro abdominal | `QS907` | cm | Sí |
| Hipertensión diagnosticada | `QS102` | 1 = sí, 0 = no; 8 → faltante | Sí |
| Tabaco (12 meses) | `QS200` | 1 = sí, 0 = no; 8 → faltante | Sí |
| Alcohol (12 meses) | `QS206`, `QS208` | 1 si `QS208 = 1`; 0 si `QS208 = 2` o `QS206 = 2` (nunca bebió); 8 → faltante | Sí |
| Días con frutas (7 días) | `QS213U`, `QS213C` | `QS213C` si `QS213U = 1`; 0 si `QS213U = 3`; 8 → faltante | Sí |
| Días con ensalada de verduras (7 días) | `QS219U`, `QS219C` | Igual que frutas | Sí |
| Presión sistólica y diastólica | `QS903S/D`, `QS905S/D` | Promedio de las dos mediciones; ≥ 999 → faltante | No |
| Nivel educativo | `QS25N` | Ordinal 0–5 | No |
| Seguro de salud | `QS26` | 1 = sí, 0 = no | No |
| Índice de riqueza | `HV270` | Quintil 1–5 | No |

Se entrenan dos versiones con el mismo procedimiento: **modelo completo** (todos los predictores) y
**modelo web** (solo los marcados «Sí»). El sistema web usa el modelo web.

`QS107` (glucosa medida en 12 meses) no es predictor; solo define el subgrupo del análisis de
robustez. `PESO15_AMAS` solo se usa en estadísticas descriptivas.

## 3.1 Factores asociados (OE1 / HE1)

Con los datos 2021–2024 (`notebooks/02_exploracion_factores.ipynb`):

- Descriptivos ponderados con `PESO15_AMAS`; pruebas bivariadas sin ponderar (chi-cuadrado para
  variables categóricas, Mann-Whitney para continuas).
- OR crudos y OR ajustados por regresión logística multivariable con todos los predictores del
  modelo completo, en casos completos. Las variables continuas se expresan por unidades
  interpretables: edad por 10 años, IMC por 5 kg/m², perímetro abdominal por 10 cm, presión por
  10 mmHg.
- **Criterio de HE1:** cada uno de los cuatro factores (edad, IMC, perímetro abdominal e
  hipertensión diagnosticada) se considera asociado si su OR ajustado tiene p < 0.05 en el modelo
  multivariable. Se reporta el resultado de cada factor por separado.
- Por la colinealidad esperada entre IMC y perímetro abdominal, se reportan los factores de inflación
  de la varianza (VIF) y, como análisis de sensibilidad, el modelo ajustado con cada una de esas dos
  variables por separado. Este análisis no cambia el criterio de HE1.

## 4. Preprocesamiento

Dentro de un `Pipeline` de scikit-learn, ajustado únicamente con datos de entrenamiento en cada
partición:

- Imputación de faltantes: mediana (numéricas) y moda (binarias y ordinales).
- Escalado estándar para la regresión logística.
- **Sin corrección de desbalance** (ni SMOTE ni pesos de clase) en el análisis principal, porque
  estas correcciones deterioran la calibración (van den Goorbergh et al., 2022). El desbalance se
  maneja con el umbral de clasificación (sección 6).

## 5. Algoritmos y selección

| Algoritmo | Papel | Hiperparámetros explorados |
|---|---|---|
| Regresión logística | Comparador principal | `C` ∈ {0.01, 0.1, 1, 10} (L2) |
| Random Forest | Alternativo | `n_estimators` = 500; `max_depth` ∈ {4, 6, 8, None}; `min_samples_leaf` ∈ {10, 30, 50} |
| XGBoost | Alternativo | `n_estimators` ∈ {200, 500}; `max_depth` ∈ {2, 3, 4}; `learning_rate` ∈ {0.03, 0.1}; `subsample` = 0.8 |
| LightGBM | Alternativo | `n_estimators` ∈ {200, 500}; `num_leaves` ∈ {7, 15, 31}; `learning_rate` ∈ {0.03, 0.1}; `min_child_samples` = 30 |

- Validación cruzada estratificada de 5 particiones sobre 2021–2024, semilla 42.
- Métrica de selección de hiperparámetros: AUC-ROC media.
- **Regla de elección del algoritmo final (prefijada):** se elige el de mayor AUC-ROC media en la
  validación cruzada. Si su ventaja sobre la regresión logística es menor a 0.01, se elige la
  regresión logística por parsimonia e interpretabilidad.

## 6. Calibración y umbral

- Con las predicciones fuera de partición (out-of-fold) de 2021–2024 se evalúan la pendiente y el
  intercepto de calibración. Si la pendiente queda fuera de [0.9, 1.1], se recalibra con
  `CalibratedClassifierCV` (método sigmoide, validación cruzada de 5 particiones sobre 2021–2024).
- **Umbral de clasificación (prefijado):** con las predicciones fuera de partición, el umbral que
  maximiza la especificidad sujeta a una sensibilidad ≥ 0.70. Se fija antes de la evaluación final.
- El sistema web no muestra categorías de riesgo; el umbral solo se usa para reportar sensibilidad
  y especificidad.

## 7. Evaluación final (2025, una sola vez)

Con el modelo y el umbral congelados:

- AUC-ROC y AUC-PR con IC 95% por bootstrap (2,000 remuestreos).
- Sensibilidad, especificidad y valores predictivos en el umbral prefijado.
- Brier score frente al modelo nulo (prevalencia de 2021–2024); pendiente e intercepto de
  calibración; curva de calibración.
- Prueba de DeLong bilateral: cada algoritmo frente a la regresión logística (HE2).
- Estabilidad temporal: diferencia entre el AUC de validación cruzada y el AUC de 2025.
- Análisis de robustez: las mismas métricas en el subgrupo con `QS107 = 1`, interpretado según
  4.9 del plan (no corrige el error de clasificación del desenlace).

## 8. Análisis preliminar de factibilidad

Antes de este protocolo se ejecutó una exploración con modelos sin ajustar que llegó a mirar los
datos de 2025 e imputó con medianas calculadas sobre todos los años. Sus resultados **no** se usan
para elegir el algoritmo, los hiperparámetros, el umbral ni las metas, y no se reportan como
resultados. La meta de AUC ≥ 0.75 se sustenta en Xie et al. (2019).

## 9. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-10-21 | Versión inicial | — |
| 2026-10-21 | Se agrega la sección 3.1 (análisis de factores asociados y criterio de HE1) | No estaba especificado; se fija antes de ejecutar el análisis |
| 2026-10-21 | Los scripts de `ml/` pasan a notebooks en `notebooks/` (la codificación queda en `notebooks/preparacion.py`) | Mantener el método de trabajo del proyecto; no cambia ninguna decisión del análisis |
