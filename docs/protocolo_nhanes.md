# Protocolo de análisis — Fase NHANES

Fija las decisiones de datos, partición, modelado y evaluación **antes** de descargar los datos de
desarrollo y prueba, conforme al plan de tesis v6. Cualquier cambio posterior se registra en la
sección 15 con fecha y motivo. El protocolo de la fase anterior (ENDES) está en
`docs/protocolo_analisis.md`.

## 0. Exploraciones previas (declaradas)

| Exploración | Datos usados | Qué se hizo | Consecuencia |
|---|---|---|---|
| Desarrollo completo con ENDES 2021–2025 | ENDES | Modelo de diagnóstico autorreportado (notebooks 01–06) | Se cambió de fuente: la ENDES no mide la glucemia |
| Exploración de NHANES 2017–marzo 2020 (`P_*`) | `P_DEMO`, `P_BMX`, `P_GHB`, `P_GLU`, `P_DIQ`, `P_BPQ`, `P_MCQ`, `P_SMQ`, `P_PAQ` | Proporciones de diabetes y de HbA1c elevada por perfil; un modelo logístico preliminar sin calcular su AUC | Orientó el desenlace y la población. **Ese ciclo va íntegro al desarrollo** |
| Revisión de documentación, 2005–2006 a 2021–2023 | Solo páginas de documentación (no datos) | Disponibilidad de `MCQ300C`, `PAQ650/665`, `DIQ160` y HbA1c | Se usan los ciclos 2007–2008 a 2017–marzo 2020 |

Ninguna exploración usó datos de los ciclos 2007–2008 a 2015–2016, de los que proviene el conjunto
de prueba. La meta de AUC y los criterios de calibración (sección 14) se fijaron el 2026-10-21,
antes de descargar esos ciclos.

## 1. Desenlace

`hba1c_elevada` = 1 si `LBXGH` ≥ 5.7 %; 0 si `LBXGH` < 5.7 %. Registros sin `LBXGH` se excluyen.
Análisis secundario: `hba1c_diabetes` = 1 si `LBXGH` ≥ 6.5 %.

## 2. Fuente y archivos

Ciclos (sufijo de archivo): 2007–2008 (`_E`), 2009–2010 (`_F`), 2011–2012 (`_G`), 2013–2014 (`_H`),
2015–2016 (`_I`) y 2017–marzo 2020 (prefijo `P_`). Módulos por ciclo: `DEMO`, `BMX`, `GHB`, `DIQ`,
`BPQ`, `MCQ`, `PAQ`, `SMQ`.

- **No** se descarga el ciclo 2017–2018 (`_J`): sus participantes están incluidos en `P_`.
- **No** se usan 2005–2006 (otro cuestionario de actividad física) ni 2021–2023 (sin `MCQ300C`).
- Los módulos se unen por `SEQN`. Se verifica que cada `SEQN` aparezca una sola vez en el conjunto
  integrado; si hubiera duplicados, el proceso se detiene.

## 3. Criterios de selección

Inclusión: `RIDAGEYR` de 20 a 69; `DIQ010` = 2 (No); `LBXGH` disponible.

Exclusión: `RIDEXPRG` = 1 (embarazo); `DIQ010` ∈ {1, 3, 7, 9} (diabetes, borderline, rehusó, no
sabe); `DIQ160` = 1 (le informaron prediabetes); `DIQ050` = 1 (insulina) o `DIQ070` = 1 (pastillas).
`DIQ160`, `DIQ050` y `DIQ070` faltantes (por salto del cuestionario) no excluyen.

## 4. Predictores y codificación

| Predictor | Variables | Codificación |
|---|---|---|
| Edad | `RIDAGEYR` | Años |
| Sexo | `RIAGENDR` | 1 = hombre, 0 = mujer |
| IMC | `BMXWT`, `BMXHT` | kg / (m)²; si falta alguno, faltante |
| Perímetro abdominal | `BMXWAIST` | cm |
| Hipertensión diagnosticada | `BPQ020` | 1 = sí, 0 = no; 7/9 → faltante |
| Antecedente familiar de diabetes | `MCQ300C` | 1 = sí, 0 = no; 7/9 → faltante |
| Actividad física recreativa | `PAQ650`, `PAQ665` | 1 si alguna = 1; 0 si ambas = 2; resto → faltante |
| Tabaquismo actual | `SMQ020`, `SMQ040` | 1 si `SMQ040` ∈ {1, 2}; 0 si `SMQ040` = 3 o `SMQ020` = 2; resto → faltante |

`RIDRETH1` (raza/etnia) solo para descriptivos: no es predictor. Pesos y diseño: `WTMEC2YR`
(`WTMECPRP` en `P_`), `SDMVSTRA`, `SDMVPSU`.

## 5. Partición en desarrollo y prueba

- **Unidad:** conglomerado = (ciclo, `SDMVSTRA`, `SDMVPSU`). Un conglomerado nunca se divide.
- **Ciclo `P_`:** todos sus conglomerados → desarrollo (sección 0).
- **Ciclos `_E` a `_I`:** en cada ciclo, en orden E, F, G, H, I, se ordenan los conglomerados por
  (`SDMVSTRA`, `SDMVPSU`), se permutan con `numpy.random.default_rng(20261022)` (un solo generador,
  usado en ese orden) y el primer `ceil(0.25 × n_conglomerados)` va a prueba; el resto a desarrollo.
- La partición se hace con los conglomerados de **todos** los participantes de `DEMO`, antes de
  aplicar los criterios de selección, y usa solo ciclo, estrato y unidad primaria. **No se consultan
  el desenlace ni los predictores.**
- Se guarda `particion/particion_nhanes.csv` (`SEQN`, `ciclo`, `conglomerado`, `conjunto`), su
  SHA-256 se registra en la sección 15 y el archivo se sube a Git **antes** de cualquier modelado.
- Los datos procesados de prueba se escriben en un archivo separado. Ningún notebook lo lee salvo el
  de evaluación final, que se ejecuta una sola vez.

## 6. Preprocesamiento

Dentro de un `Pipeline` ajustado solo con datos de entrenamiento de cada partición: imputación con
mediana (continuas) o moda (binarias); escalado estándar para la regresión logística. Sin corrección
del desbalance.

## 7. Algoritmos y selección

| Algoritmo | Hiperparámetros |
|---|---|
| Regresión logística (comparador principal) | `C` ∈ {0.01, 0.1, 1, 10} |
| Random Forest | 500 árboles; `max_depth` ∈ {4, 6, 8, None}; `min_samples_leaf` ∈ {10, 30, 50} |
| XGBoost | `n_estimators` ∈ {200, 500}; `max_depth` ∈ {2, 3, 4}; `learning_rate` ∈ {0.03, 0.1}; `subsample` = 0.8 |
| LightGBM | `n_estimators` ∈ {200, 500}; `num_leaves` ∈ {7, 15, 31}; `learning_rate` ∈ {0.03, 0.1}; `min_child_samples` = 30 |

- Validación cruzada: `StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)`, grupos =
  conglomerado, estratificada por `hba1c_elevada`, solo en el desarrollo.
- Métrica de selección: AUC-ROC media.
- **Regla de elección:** el algoritmo de mayor AUC-ROC media; si su ventaja sobre la regresión
  logística es menor a 0.01, se elige la regresión logística.

## 8. Calibración y umbral (desarrollo)

- Con predicciones fuera de partición: si la pendiente queda fuera de [0.9, 1.1], se recalibra con
  `CalibratedClassifierCV` (sigmoide) usando las mismas particiones agrupadas.
- Umbral: máxima especificidad con sensibilidad ≥ 0.70 (solo para reportar sensibilidad y
  especificidad; la web no muestra categorías).

## 9. Factores asociados (OE1 / HE1), desarrollo

Regresión logística multivariable con todos los predictores (casos completos); OR por 10 años,
5 kg/m² y 10 cm. HE1: cada factor (edad, IMC, perímetro abdominal, hipertensión, antecedente
familiar) se considera asociado si su OR ajustado tiene p < 0.05; se reporta la dirección. Por la
colinealidad IMC–perímetro abdominal se reportan VIF y modelos con cada uno por separado.

## 10. Intervalos individuales (bootstrap)

1,000 remuestreos **por conglomerado** del desarrollo; en cada uno se reajusta el modelo seleccionado
con los hiperparámetros congelados. Intervalo = percentiles 2.5 y 97.5 de las probabilidades. Para la
regresión logística se guardan los coeficientes de cada remuestreo; si el modelo elegido no fuera
lineal, se usan 200 remuestreos y se guardan los modelos.

## 11. Evaluación final (conjunto de prueba, una sola vez)

- AUC-ROC y AUC-PR con IC 95% por bootstrap por conglomerado (2,000 remuestreos).
- Sensibilidad, especificidad, VPP y VPN en el umbral congelado.
- Calibración: pendiente, razón O/E, intercepto, ICI y curva de calibración; Brier frente al nulo
  (prevalencia del desarrollo).
- DeLong bilateral: cada algoritmo frente a la regresión logística (se declara que la prueba supone
  independencia entre observaciones).
- Consistencia: AUC de validación cruzada menos AUC de prueba.
- Secundarios: desempeño para `hba1c_diabetes`; por sexo y por edad (20–39, 40–59, 60–69).
- El notebook registra commit, SHA-256 de modelos y datos, y se niega a ejecutarse dos veces.

## 12. Ponderación

Modelado sin ponderar (estimación individual). Descriptivos ponderados con el peso combinado:
`WTMEC2YR × 2 / 13.2` para `_E` a `_I` y `WTMECPRP × 3.2 / 13.2` para `P_` (13.2 años en total).

## 13. Sistema web

Pregunta de filtro (diagnóstico de diabetes o aviso de prediabetes → no estima). Entradas: edad,
sexo, peso, talla, perímetro abdominal, hipertensión, antecedente familiar, actividad física,
tabaquismo, con la redacción de NHANES traducida. Salida: probabilidad, intervalo bootstrap, factores
mostrados y mensaje de alcance. Los factores que se muestran se deciden con el desarrollo (HE1 y
SHAP), antes de la evaluación final.

## 14. Metas (fijadas el 2026-10-21)

- AUC-ROC ≥ 0.75 en el conjunto de prueba.
- Calibración adecuada: pendiente entre 0.8 y 1.2, razón O/E entre 0.9 y 1.1 y Brier menor que el
  nulo. IC, intercepto, curva e ICI se reportan sin criterio de aprobación.

## 15. Registro de cambios

Todas las fechas están en hora de Lima (UTC−5).

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-10-21 | Versión inicial | — |
| 2026-10-21 | En 2007–2008 la pregunta de pastillas para la diabetes se llama `DID070` (misma pregunta y códigos que `DIQ070`); se renombra a `DIQ070` al leer `DIQ_E` | El nombre no existe en ese ciclo; se detectó al integrar, antes de la partición. No cambia ningún criterio |
| 2026-10-21 | Partición generada (`notebooks/nhanes/01_integracion_particion.ipynb`): 203 conglomerados, 40 en prueba (19.7 %); 66,148 participantes en `DEMO`, 0 `SEQN` duplicados. SHA-256 de `particion/particion_nhanes.csv`: `2f05d104399e7e063d9f142d0532ccced9b500ba7cf5f93611f56980fd087fcd`. URL y SHA-256 de cada archivo fuente en `particion/fuentes_nhanes.csv` | Sección 5 |
| 2026-10-21 | Tras los criterios de selección: desarrollo 18,264 participantes (163 conglomerados); prueba 4,627 (40 conglomerados, reservado). SHA-256 de `data/processed/nhanes_prueba.csv`: `c48492938873def3d096e59c8d465e32843fdd574d3dd2b349e90754d58ee62c` | Permite comprobar en la evaluación final que el archivo de prueba no cambió |
| 2026-10-21 | Corrección de fechas: la versión inicial, la meta de AUC y los criterios de calibración figuraban con fecha 2026-10-22, que era la fecha en UTC; en hora de Lima corresponde a 2026-10-21. El commit del protocolo (`4e2fb70`, etiqueta `protocolo-nhanes-v1`) se registró el 2026-10-21 a las 21:47:15 (UTC−5), es decir, el 2026-10-22 a las 02:47:15 UTC | Solo se corrige la fecha. **No cambió el contenido del protocolo**: criterios, partición, algoritmos, metas y calibración son los mismos de `protocolo-nhanes-v1` |
| 2026-10-21 | Se añade a la sección 9 un análisis de sensibilidad: el mismo modelo multivariable con errores estándar robustos por conglomerado (`cov_type='cluster'`). El criterio de HE1 no cambia (modelo principal, p < 0.05) | Los participantes de un conglomerado no son independientes. Se registró antes de ejecutar el notebook 02 y solo con el desarrollo |
| 2026-10-21 | Sección 10: el bootstrap por conglomerado remuestrea con reemplazo los 163 conglomerados del desarrollo, con `numpy.random.default_rng(42)`; los coeficientes de cada remuestreo se guardan en `models/nhanes/bootstrap_regresion_logistica.joblib` | El protocolo no fijaba la semilla ni el formato. Se registró antes de ejecutar el bootstrap, con la regresión logística ya seleccionada en el notebook 03 |
| 2026-10-21 | Sección 13, salida de la web: (1) probabilidad con su intervalo bootstrap; (2) principales contribuciones individuales, calculadas como valores SHAP exactos del modelo lineal en log-odds (coeficiente × valor estandarizado, con IMC y perímetro abdominal sumados como "composición corporal"), hasta 3 factores con \|SHAP\| ≥ 0.05, ordenados por magnitud; (3) dos o tres recomendaciones tomadas de un catálogo con fuentes (`docs/catalogo_recomendaciones.md`), activadas por criterios de las guías y no por el signo de una contribución. Las contribuciones negativas solo se explican y nunca generan un consejo. Ningún mensaje promete reducir el riesgo | Decisión del investigador con el desarrollo, antes de la evaluación final. Los mensajes se someterán al juicio de expertos |
| 2026-10-21 | Evaluación final ejecutada una sola vez (`notebooks/nhanes/05_evaluacion_final.ipynb`, commit `aa31a1f`, 23:23–23:26). Huella del archivo de prueba verificada. Antes se ensayó el código con el desarrollo, sin leer la prueba. Regresión logística: AUC-ROC 0.744 (IC 95 % 0.730–0.757), pendiente 0.98, O/E 1.015, Brier 0.169 frente a 0.196 del nulo. HE3: meta de AUC no alcanzada; criterios de calibración cumplidos. HE2: sin diferencias frente a la regresión logística (p de DeLong ≥ 0.37). Para la ejecución se fijaron dos detalles que la sección 11 no precisaba: la semilla del bootstrap por conglomerado (`default_rng(42)`, mismos remuestreos para todos los modelos) y que el ICI se reporta sin IC | Sección 11. El modelo no se modifica |
