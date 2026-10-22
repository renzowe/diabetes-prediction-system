# Análisis complementario: la variable alcohol

Resumen del análisis posterior a la evaluación final (`docs/protocolo_analisis.md`, sección 8.1).
El detalle, el código y las tablas están en `notebooks/05_analisis_alcohol.ipynb` y
`resultados/05_alcohol/`. **Solo usa datos 2021–2024 y no modifica el modelo congelado.**

## Motivo

En la API, para una persona que bebió alcohol en los últimos 12 meses, esta variable contribuye a
disminuir la probabilidad estimada. Se investigó si se debía a un error o a una característica de los
datos, sin asumir de antemano una explicación.

## Resultados

| Verificación | Resultado |
|---|---|
| Pregunta `QS208` en los cuestionarios 2021–2025 | Idéntica: «¿En los últimos 12 meses… ha consumido alguna bebida alcohólica o licor?» (1 Sí, 2 No, 8 No sabe); se salta si `QS206` (alguna vez en la vida) es «No». La descripción «Tomó cerveza» de los diccionarios 2021–2022 es un desalineamiento del PDF |
| Codificación del entrenamiento | Correcta: quienes nunca bebieron (198) cuentan como «no»; el único «no sabe» queda como faltante |
| Integración con la API | Correcta: la API construye la misma fila que el entrenamiento en los 8,897 registros comparados (diferencia máxima de probabilidad: 0.00009) |
| Interpretación de la contribución | Explica la clase positiva y se mide respecto de la persona promedio (77% bebió). Para quien bebió es −0.046 log-odds (odds × ≈ 0.96). No es un efecto protector |
| Asociación cruda | 5.5% de diagnóstico reportado entre quienes bebieron frente a 9.0% entre quienes no (OR 0.60) |
| Ajustada por edad y sexo | OR 0.84 (IC 95%: 0.70–1.03; p = 0.09). Las personas mayores y las mujeres beben menos y reportan más diagnóstico |
| Ajustada por los predictores del modelo web | OR 0.83 (IC 95%: 0.67–1.01; p = 0.07) |
| Ajustada por los predictores del modelo completo | OR 0.81 (IC 95%: 0.65–0.99; p = 0.04) |
| Cambios por año, edad o sexo | Sin evidencia (interacciones, p ≥ 0.48) |
| Bebió alguna vez pero no en 12 meses, frente a nunca bebió | OR ajustado 0.98 (IC 95%: 0.55–1.77) |
| Validación cruzada con y sin alcohol | AUC-ROC 0.782 en ambos; Brier 0.0538 en ambos; diferencia media en 50 particiones: −0.0001 |

## Diferencia entre el modelo completo y el modelo web (p = 0.04 frente a p = 0.07)

No se debe al tamaño de la muestra: con la misma muestra, el modelo web da p = 0.068. Se debe a las
variables de ajuste, en particular al **índice de riqueza**. Los hogares de mayor riqueza beben más y
también reportan más diagnóstico; al ajustar por riqueza, el OR del alcohol se aleja algo de 1 y el
valor p cruza 0.05. Que la significancia dependa de una variable de ajuste indica que la asociación
residual es débil y sensible a la especificación del modelo.

## Conclusión

- **No hay error** de codificación, de integración ni de interpretación de la contribución.
- Es una **asociación observada**, explicada en gran parte por la edad y el sexo. La asociación
  residual es débil, no significativa con los predictores del modelo web y sensible al ajuste.
- **Su causa no puede determinarse** con la ENDES, que no registra cuándo ni por qué alguien dejó de
  beber ni la fecha del diagnóstico. El cambio de hábitos tras el diagnóstico (causalidad inversa) es
  una hipótesis, no un hallazgo; también son posibles el azar, la confusión residual y la clasificación
  errónea del desenlace.
- **El alcohol no aporta al modelo web** según el criterio prefijado.

## Decisiones

- Se conserva el modelo congelado (opción A): no se reentrena ni se usa 2025 para estos ajustes.
- El formulario mantiene la pregunta de alcohol, porque el modelo la usa.
- El sistema web solo muestra las contribuciones de edad, sexo, composición corporal (IMC y perímetro
  abdominal) e hipertensión diagnosticada, con la aclaración de que no son consejos ni efectos
  causales. Las contribuciones de alcohol, tabaco, frutas y verduras no se muestran.
- En futuras versiones del modelo, el alcohol podría excluirse de los predictores.
