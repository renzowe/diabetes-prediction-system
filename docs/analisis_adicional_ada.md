# Análisis adicional posterior a la evaluación final: comparación con el ADA Risk Test

**Estado:** reglas redactadas el 2026-11-22 (hora de Lima), **antes de calcular cualquier resultado**. Este documento se sube a Git antes de ejecutar el análisis, igual que el protocolo y la partición.

**Naturaleza del análisis.** Es un **análisis adicional posterior a la evaluación final** (ejecutada el 2026-10-21, commit `aa31a1f`). No forma parte de las hipótesis (HE1–HE4 y general), no cambia ninguna decisión sobre ellas y **no modifica el modelo congelado** (`models/nhanes/regresion_logistica.joblib`, SHA-256 `fa1be5d6a0ab00640f41549cd27725aa975f555fd55e02ffb2e434a57d41dd1b`). El conjunto de prueba no se usa para ajustar nada: solo se calcula una puntuación fija y se compara.

**Motivo.** Una comparación con otra escala del propio conjunto de prueba permite saber cuánto aportan los ocho predictores frente a un cuestionario simple, en lugar de comparar con cifras de otros estudios con desenlaces y poblaciones distintos.

## 1. Hallazgo sobre diabetes gestacional en NHANES (verificado)

La pregunta **RHQ162** («Durante el embarazo, ¿le dijo un médico que tenía diabetes, diabetes del azúcar o diabetes gestacional?»; solo mujeres de 20 años o más) **está disponible en los seis ciclos** (RHQ_E a RHQ_I y P_RHQ). Codificación: 1 = Sí; 2 = No; 3 = Dudoso (borderline); 7 = Rechazó; 9 = No sabe; vacío = no preguntada (principalmente mujeres que nunca estuvieron embarazadas, RHQ131 = 2, y otras sin dato). En las mujeres de 20 a 69 años de cada ciclo, la proporción con dato vacío fue de 23 a 34 % según el ciclo.

Los archivos se descargaron de la misma ruta de los CDC que el resto de los módulos (`https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{año}/DataFiles/{archivo}.xpt`) y quedan en `data/nhanes/raw/` (carpeta ignorada por Git).

## 2. Escala y versiones

**Fuente publicada verificada:** Bang H, et al. (2009). *Annals of Internal Medicine*, 151(11), 775–783, tabla 2 (texto completo consultado en PubMed Central, PMC3633111). Puntos publicados:

| Ítem | Categoría | Puntos |
|---|---|---|
| Edad | < 40 / 40–49 / 50–59 / ≥ 60 años | 0 / 1 / 2 / 3 |
| Sexo | Mujer / hombre | 0 / 1 |
| Antecedente familiar de diabetes | No / sí | 0 / 1 |
| Antecedente de hipertensión | No / sí | 0 / 1 |
| Peso (obesidad) | Sin sobrepeso / sobrepeso / obesidad / obesidad extrema | 0 / 1 / 2 / 3 |
| Actividad física | No / sí | 0 / −1 |

Categoría de peso (nota de la tabla 2 de Bang et al.): obesidad extrema si IMC ≥ 40 kg/m² o perímetro abdominal ≥ 50 pulgadas (127 cm) en hombres o ≥ 49 pulgadas (124.5 cm) en mujeres; obesidad si 30 ≤ IMC < 40 o perímetro de 40 a < 50 pulgadas (101.6 a < 127 cm) en hombres o de 35 a < 49 pulgadas (88.9 a < 124.5 cm) en mujeres; sobrepeso si 25 ≤ IMC < 30 o perímetro de 37 a < 40 pulgadas (94 a < 101.6 cm) en hombres o de 31.5 a < 35 pulgadas (80 a < 88.9 cm) en mujeres; en otro caso, sin sobrepeso. Se asigna la categoría **más alta** que cumpla cualquiera de las dos medidas (IMC o perímetro). El punto de corte publicado es ≥ 5 para diabetes y 4 para prediabetes.

**Limitación que debe confirmar el investigador antes del commit.** La versión de Bang et al. no incluye diabetes gestacional (los autores señalan que no había datos de embarazo). El cuestionario público de la ADA incluye un punto para mujeres con diabetes gestacional previa, pero **su tabla de puntos oficial no pudo consultarse en esta sesión** (la página de la ADA es interactiva y los PDF oficiales no estuvieron accesibles). Por eso se registran dos versiones, sin ajustar ningún punto:

- **Versión A (principal): puntos de Bang et al. (2009) tal como se publicaron**, sin ítem de diabetes gestacional.
- **Versión B (sensibilidad): versión A + 1 punto para mujeres con diabetes gestacional previa**, valor tomado del cuestionario público de la ADA y **pendiente de confirmar contra la tarjeta oficial**. Si el investigador no puede confirmarlo, la versión B no se calcula.

Se declara que la versión A es la escala usada en el análisis principal; la B nunca sustituye a la A.

## 3. Adaptación a las variables de NHANES (diferencias declaradas)

| Ítem | Variable usada | Diferencia respecto de la escala publicada |
|---|---|---|
| Edad | `edad` (RIDAGEYR) | Ninguna |
| Sexo | `hombre` | Ninguna |
| Antecedente familiar | `familiar_dm` (MCQ300C) | La pregunta incluye «familiares biológicos cercanos» (padre, madre, hermanos y hermanas). Es la misma variable del modelo |
| Hipertensión | `hta` (BPQ020, diagnóstico médico) | Ninguna sustantiva |
| Peso | `imc` y `cintura` (medidos por personal capacitado) | En el modelo propio el IMC y la cintura también se miden; en la escala de Bang se informan |
| Actividad física | `actividad` (recreativa vigorosa o moderada, PAQ650/PAQ665) | Bang et al. la definieron en NHANES 1999–2004 con otra pregunta («compare su actividad con la de otros de su edad»); aquí es actividad recreativa, la misma variable del modelo |
| Diabetes gestacional (solo versión B) | RHQ162 | Ver sección 4 |

La escala se aplica **sobre los mismos participantes y las mismas variables** que usa el modelo, de modo que la comparación es sobre la misma información de entrada. El desenlace es el del estudio (hemoglobina glicosilada ≥ 5.7 %), no el de Bang et al. (diabetes no diagnosticada por glucosa en ayunas).

## 4. Reglas de codificación y valores faltantes (fijadas antes del cálculo)

1. **Diabetes gestacional (versión B):** mujeres con RHQ162 = 1 reciben +1; RHQ162 = 2, 3 (dudoso), 7, 9 o vacío = 0 punto; hombres = 0. Se reporta cuántas mujeres tuvieron dato vacío, 3, 7 o 9.
2. **Valores faltantes en los ítems (análisis principal):** casos completos. Entran las personas del conjunto de prueba con todos los ítems de la escala disponibles (edad, sexo, antecedente familiar, hipertensión, actividad física y al menos una medida de peso: IMC o perímetro abdominal). El modelo se evalúa **en los mismos participantes**, de modo que la comparación pareada es válida. Se reporta cuántos participantes se excluyen y su proporción.
3. **Análisis de sensibilidad:** todo el conjunto de prueba (n = 4,627), con los ítems faltantes puntuados como 0. El modelo se evalúa con la imputación que ya usa.
4. No se modifican puntos, categorías ni puntos de corte; no se ajusta ningún parámetro con el conjunto de prueba.

## 5. Métricas

1. **AUC-ROC de la escala** (puntuación entera, con empates tratados como en `roc_auc_score`) en el conjunto de prueba, con **IC del 95 % por bootstrap por conglomerado** (2,000 remuestreos, `default_rng(42)`, los mismos remuestreos que la evaluación final).
2. **Comparación pareada con el modelo congelado:** diferencia de AUC-ROC (modelo menos escala) con **prueba de DeLong pareada** (bilateral) e **IC del 95 % de la diferencia por bootstrap por conglomerado**.
3. Descriptivo: sensibilidad, especificidad y valores predictivos con los puntos de corte publicados ≥ 5 y ≥ 4. No se declara «mejor» ni «peor» a partir de estas cifras.
4. Se reporta la AUC-ROC de la escala por grupo de edad (20–39, 40–59, 60–69) **solo como descriptivo**.

## 6. Cómo se reportará cada escenario (decidido antes de ver el resultado)

El escenario se define con la diferencia de AUC-ROC (modelo menos escala) en los casos completos, versión A:

- **Escenario 1: el modelo es mejor.** IC del 95 % de la diferencia por encima de 0 y DeLong con p < 0.05. Se redacta: «El modelo discrimina mejor que la escala ADA en el conjunto de prueba», sin afirmar que sea clínicamente superior.
- **Escenario 2: comparable.** IC de la diferencia incluye 0 o DeLong con p ≥ 0.05. Se redacta: «El desempeño discriminativo del modelo es comparable al de la escala ADA de seis ítems». El valor agregado del sistema se describe en términos de probabilidad individual calibrada, intervalo de confianza e interpretabilidad (SHAP), no de discriminación.
- **Escenario 3: la escala es mejor.** IC de la diferencia por debajo de 0 y DeLong con p < 0.05. Se redacta tal cual: «La escala ADA de seis ítems discrimina mejor que el modelo en el conjunto de prueba». No se cambia el modelo ni se reabren las hipótesis. Se mantienen las conclusiones del estudio y se añade esta limitación; el sistema aporta probabilidades calibradas e interpretables, pero no mayor discriminación que una escala simple.

Independientemente del escenario: se reporta el resultado de la versión A en el plan y en el artículo, en una sección rotulada **«Análisis adicional posterior a la evaluación final»**; no se modifica ningún resultado, tabla ni decisión sobre las hipótesis existentes; y la versión B y la sensibilidad se reportan como secundarias.

## 7. Qué no se hará

- No se reajustará, recalibrará ni se reemplazará el modelo.
- No se cambiarán los puntos de la escala, la codificación ni la regla de casos completos después de ver el resultado.
- No se agregarán otras escalas ni variantes después de ver el resultado; si se quisiera otra comparación, se registra antes y por separado.
- No se calculará nada hasta que el investigador confirme que este archivo está en Git.

## 8. Registro

| Fecha (Lima) | Evento |
|---|---|
| 2026-11-22 | Reglas redactadas. Verificado que RHQ162 existe en los seis ciclos. Sin cálculo del ADA Risk Test |
