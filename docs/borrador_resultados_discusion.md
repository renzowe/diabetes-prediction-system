# Borrador: resultados y discusión (fase NHANES)

Texto base para los capítulos de resultados y discusión del informe final. Las cifras provienen de `resultados/nhanes/` (notebooks 02 a 05). Los análisis de los notebooks 02 a 04 usaron solo el conjunto de desarrollo; el notebook 05 es la evaluación única con el conjunto de prueba reservado.

---

## Resultados: contraste de hipótesis

### HE1. Factores asociados (conjunto de desarrollo, n = 17,324 con datos completos)

Criterio: un factor se considera asociado si su OR ajustado tiene p < 0.05.

| Factor | OR ajustado (IC 95 %) | p | Decisión |
|---|---|---|---|
| Edad (por 10 años) | 1.78 (1.73–1.84) | < 0.001 | Asociado, directa |
| IMC (por 5 kg/m²) | 1.49 (1.38–1.60) | < 0.001 | Asociado, directa |
| Antecedente familiar de diabetes | 1.26 (1.17–1.36) | < 0.001 | Asociado, directa |
| Perímetro abdominal (por 10 cm) | 0.98 (0.92–1.05) | 0.55 | No asociado |
| Hipertensión diagnosticada | 1.05 (0.96–1.14) | 0.28 | No asociado |

**HE1 se acepta parcialmente:** tres de los cinco factores cumplen el criterio.

### HE2. Comparación de algoritmos (conjunto de prueba)

Criterio: diferencia significativa en la AUC-ROC frente a la regresión logística (DeLong bilateral, p < 0.05).

| Algoritmo | Diferencia de AUC frente a RL (IC 95 % bootstrap por conglomerado) | p (DeLong) |
|---|---|---|
| Random Forest | −0.002 (−0.006 a 0.003) | 0.46 |
| XGBoost | +0.001 (−0.002 a 0.005) | 0.38 |
| LightGBM | +0.002 (−0.002 a 0.005) | 0.37 |

**HE2 se rechaza:** ningún algoritmo difiere significativamente de la regresión logística.

### HE3. Desempeño del modelo seleccionado (regresión logística, conjunto de prueba, n = 4,627)

| Criterio prefijado | Resultado | ¿Cumple? |
|---|---|---|
| AUC-ROC ≥ 0.75 | 0.744 (IC 95 % 0.730–0.757) | No |
| Pendiente de calibración entre 0.8 y 1.2 | 0.98 (0.91–1.05) | Sí |
| Razón O/E entre 0.9 y 1.1 | 1.015 (0.95–1.08) | Sí |
| Brier menor que el del modelo nulo | 0.169 frente a 0.196 | Sí |

**HE3 se acepta parcialmente:** se cumplen los tres criterios de calibración, pero no la meta de discriminación.

Otros resultados del conjunto de prueba (umbral congelado de 0.277):

- AUC-PR: 0.483 (0.448–0.515), con una prevalencia del 26.7 %.
- Sensibilidad 0.675, especificidad 0.692, VPP 0.444 y VPN 0.854.
- La AUC de validación cruzada menos la de prueba fue 0.011.

### Hipótesis general

**La hipótesis general se rechaza en su componente de discriminación** (AUC-ROC de 0.744 frente a una meta de ≥ 0.75). Se cumple en su componente de calibración.

### Resultados secundarios

- HbA1c ≥ 6.5 %: AUC-ROC de 0.790 (0.757–0.822), con 104 casos.
- AUC-ROC por subgrupo:
  - Mujeres 0.765 y hombres 0.722.
  - De 20 a 39 años, 0.705; de 40 a 59, 0.678; de 60 a 69, 0.573 (n = 736).

---

## Discusión

### Discriminación del modelo

El modelo obtuvo una AUC-ROC de 0.744 en el conjunto de prueba reservado, ligeramente por debajo de la meta de 0.75 fijada en el protocolo, por lo que ese componente de la hipótesis no se confirma. Aun así, el intervalo de confianza (0.730–0.757) incluye la meta y la diferencia es de 0.006.

Según la clasificación convencional de la AUC (Hosmer et al., 2013; Mandrekar, 2010), este valor corresponde a una discriminación *aceptable*. Es una referencia descriptiva, no el criterio con que se contrastó la hipótesis.

El resultado es coherente con el techo de información de los predictores no invasivos. La escala FINDRISC, la más utilizada para tamizaje sin pruebas de laboratorio, obtuvo una AUC de 0.67 para detectar prediabetes en NHANES 1999–2010 (Zhang et al., 2014) y de 0.69 en población peruana (Bernabé-Ortiz et al., 2018), aunque sus desenlaces y poblaciones no son idénticos a los de este estudio.

Los antecedentes que motivaron la meta reportaron valores más altos: Sun et al. (2026) obtuvieron 0.82, Cichosz et al. (2024) entre 0.78 y 0.81, y Choi et al. (2023) entre 0.79 y 0.82. Entre las posibles explicaciones están las diferencias en los predictores, en la definición del desenlace y en la forma de validar. Este estudio evaluó el modelo una sola vez en un conjunto reservado por conglomerados, sin usarlo para ninguna decisión, un diseño menos expuesto al optimismo.
*(Completar con el detalle de cada antecedente: predictores, desenlace y tipo de validación.)*

### Calibración

La calibración cumplió los tres criterios prefijados: pendiente 0.98, razón O/E 1.015 y Brier menor que el del modelo nulo. Las probabilidades que muestra el sistema web corresponden, en promedio, a las proporciones observadas. Esto es especialmente relevante porque el sistema muestra una probabilidad y no una categoría de riesgo.

### Comparación de algoritmos

Random Forest, XGBoost y LightGBM no superaron a la regresión logística: las diferencias fueron menores a 0.002 y no significativas. Con ocho predictores no invasivos y relaciones mayormente monótonas, los métodos de ensamble no encuentran estructura adicional. Este resultado respalda el uso de un modelo lineal, más interpretable, cuyas contribuciones SHAP son exactas.

### Factores asociados

La edad, el IMC y el antecedente familiar se asociaron con la HbA1c elevada. El perímetro abdominal no mostró asociación independiente del IMC, por su alta colinealidad (r = 0.91; VIF ≈ 8); sin el IMC en el modelo, sí se asocia (OR 1.35 por 10 cm). La hipertensión mostró una asociación cruda (OR 2.29) que desaparece al ajustar por edad y adiposidad. Estas asociaciones provienen de datos transversales y no implican causalidad.

### Limitaciones

- La validación es interna, con un conjunto reservado de NHANES. No es temporal ni externa, y el desempeño en población de Lima Metropolitana no se ha evaluado.
- Entre las personas de 60 a 69 años la discriminación es baja (AUC 0.573). El sistema muestra un aviso para ese grupo, añadido después de la evaluación final.
- El desenlace se basa en una única medición de HbA1c.
- La prueba de DeLong supone independencia entre observaciones; por eso se complementó con intervalos bootstrap por conglomerado.
