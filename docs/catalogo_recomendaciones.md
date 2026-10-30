# Catálogo de recomendaciones preventivas

Versión 1.0 (2026-10-21), sometida al juicio de expertos. Los textos de la sección 3 son **idénticos** a los que muestra el sistema web (`backend/app/services/recomendaciones.py`); una prueba automática verifica que coincidan.

## 1. Propósito y principios

Junto con la probabilidad estimada y las principales contribuciones del modelo, el sistema muestra dos o tres recomendaciones generales. Se rigen por estos principios:

1. **Sustento:** cada mensaje se basa en una guía o fuente de salud citada.
2. **Activación por criterio, no por contribución:** un mensaje se muestra cuando los datos de la persona cumplen el criterio de la guía (por ejemplo, IMC ≥ 25), no porque una contribución del modelo sea positiva o negativa.
3. **Sin consejos protectores:** una contribución negativa (por ejemplo, realizar actividad física, que *reduce* la estimación) se explica, pero **nunca** genera un mensaje del tipo "siga así, esto le protege".
4. **Sin promesas:** ningún mensaje promete reducir el riesgo ni cuantifica cuánto bajaría la probabilidad al cambiar un hábito. Las contribuciones del modelo no son efectos causales.
5. **Prioridad de los factores modificables:** actividad física, peso corporal y tabaco van antes que los mensajes generales.

## 2. Regla de selección

1. Se identifican los mensajes de factores modificables cuyo criterio se cumple y se ordenan según la contribución SHAP del factor relacionado, de mayor a menor.
2. Si la persona cumple el criterio de tamizaje de la ADA, se muestran hasta **dos** mensajes modificables más el de la **prueba de laboratorio**.
3. Si no lo cumple, se muestran hasta **tres** mensajes modificables. Si resultan menos de dos mensajes, se agrega "Cuándo realizarse una prueba" y, si aún faltan, "Síntomas que requieren consulta".

Así, cada persona recibe siempre dos o tres mensajes.

## 3. Mensajes

| Id | Tipo | Criterio de activación | Fuentes |
|---|---|---|---|
| `actividad_fisica` | Modificable | no realiza actividades físicas recreativas moderadas o vigorosas en una semana típica | OMS-AF, ADA-3 |
| `peso` | Modificable | IMC ≥ 25 kg/m² | ADA-3 |
| `tabaco` | Modificable | fuma actualmente (todos los días o algunos días) | CDC-TAB, ADA-3 |
| `prueba_tamizaje` | General | edad ≥ 35 años, o IMC ≥ 25 junto con al menos uno de estos factores: familiar de primer grado con diabetes, hipertensión diagnosticada o inactividad física | ADA-2, USPSTF |
| `tamizaje_futuro` | General | no cumple el criterio de la prueba de tamizaje y se muestran menos de dos recomendaciones sobre factores modificables | ADA-2 |
| `sintomas` | General | los demás criterios dan, en total, menos de dos recomendaciones | ADA-2 |

### Actividad física (`actividad_fisica`)

> La Organización Mundial de la Salud recomienda que los adultos realicen cada semana entre 150 y 300 minutos de actividad física aeróbica moderada (por ejemplo, caminar a paso rápido) o entre 75 y 150 minutos de actividad vigorosa, además de ejercicios de fortalecimiento muscular dos o más días por semana. Si tiene alguna enfermedad o limitación, consulte con un profesional de salud antes de empezar.

- **Criterio:** no realiza actividades físicas recreativas moderadas o vigorosas en una semana típica.
- **Fuentes:** OMS-AF, ADA-3.

### Peso corporal (`peso`)

> Su índice de masa corporal está en el rango de sobrepeso u obesidad (25 o más). Para adultos con sobrepeso u obesidad y mayor riesgo de diabetes, la Asociación Americana de Diabetes recomienda programas de cambio de estilo de vida, con alimentación saludable y actividad física, que buscan una pérdida de al menos 5 a 7 % del peso inicial. Un profesional de salud o de nutrición puede orientarle sobre un plan adecuado para usted.

- **Criterio:** IMC ≥ 25 kg/m².
- **Fuentes:** ADA-3.

### Tabaco (`tabaco`)

> Fumar es una de las causas de la diabetes tipo 2: según los CDC, las personas que fuman tienen entre 30 y 40 % más probabilidad de desarrollarla que quienes no fuman. La Asociación Americana de Diabetes indica que las personas con riesgo de diabetes deben recibir orientación para dejar de fumar. Puede pedir apoyo para dejar de fumar en su establecimiento de salud.

- **Criterio:** fuma actualmente (todos los días o algunos días).
- **Fuentes:** CDC-TAB, ADA-3.

### Prueba de laboratorio (`prueba_tamizaje`)

> Según los criterios de la Asociación Americana de Diabetes, a su perfil le corresponde una prueba de tamizaje de diabetes y prediabetes, como la hemoglobina glicosilada (HbA1c) o la glucosa en ayunas. Solo un análisis de laboratorio puede indicar si sus valores son normales. Si el resultado es normal, la guía recomienda repetir la prueba al menos cada 3 años.

- **Criterio:** edad ≥ 35 años, o IMC ≥ 25 junto con al menos uno de estos factores: familiar de primer grado con diabetes, hipertensión diagnosticada o inactividad física.
- **Fuentes:** ADA-2, USPSTF.

### Cuándo realizarse una prueba (`tamizaje_futuro`)

> Con los datos ingresados, las guías de la Asociación Americana de Diabetes todavía no indican una prueba de tamizaje. Recomiendan empezar a los 35 años, o antes si se presenta sobrepeso junto con otro factor de riesgo, como tener un familiar directo con diabetes, hipertensión o inactividad física.

- **Criterio:** no cumple el criterio de la prueba de tamizaje y se muestran menos de dos recomendaciones sobre factores modificables.
- **Fuentes:** ADA-2.

### Síntomas que requieren consulta (`sintomas`)

> Si presenta sed excesiva, necesidad de orinar con mucha frecuencia o pérdida de peso sin causa aparente, acuda a un establecimiento de salud, aunque la estimación de este sistema sea baja.

- **Criterio:** los demás criterios dan, en total, menos de dos recomendaciones.
- **Fuentes:** ADA-2.

## 4. Aviso para personas de 60 a 69 años

Se añadió el 2026-10-21, **después de la evaluación final**, y no es una recomendación. En el conjunto de prueba, la AUC-ROC del modelo en el grupo de 60 a 69 años fue de 0.573 (n = 736), frente a 0.744 en el total. El aviso se muestra a las personas de 60 años o más y no cambia la probabilidad estimada:

> En personas de 60 a 69 años, la evaluación del modelo mostró que distingue poco entre personas de la misma edad: en ese grupo, la estimación ayuda menos a saber quién tiene la HbA1c elevada. Tome este resultado con especial cautela. A su edad, las guías indican realizarse una prueba de laboratorio, que es la única forma de conocer su HbA1c.

## 5. Fuentes

- **ADA-2.** American Diabetes Association Professional Practice Committee. 2. Diagnosis and Classification of Diabetes: Standards of Care in Diabetes—2026. Diabetes Care. 2026;49(Suppl 1):S27–S49. doi:10.2337/dc26-S002
- **ADA-3.** American Diabetes Association Professional Practice Committee. 3. Prevention or Delay of Diabetes and Associated Comorbidities: Standards of Care in Diabetes—2026. Diabetes Care. 2026;49(Suppl 1):S50–S60. doi:10.2337/dc26-S003
- **USPSTF.** US Preventive Services Task Force. Screening for Prediabetes and Type 2 Diabetes: US Preventive Services Task Force Recommendation Statement. JAMA. 2021;326(8):736–743. doi:10.1001/jama.2021.12531
- **OMS-AF.** Bull FC, Al-Ansari SS, Biddle S, et al. World Health Organization 2020 guidelines on physical activity and sedentary behaviour. Br J Sports Med. 2020;54(24):1451–1462. doi:10.1136/bjsports-2020-102955
- **CDC-TAB.** Centers for Disease Control and Prevention. Smoking and Diabetes. Tips From Former Smokers. https://www.cdc.gov/tobacco/campaign/tips/diseases/diabetes.html (revisado el 13 de octubre de 2023)

## 6. Decisiones de diseño

1. **Criterio de tamizaje.** La ADA incluye la ascendencia latina entre los factores de riesgo de su tabla 2.5. El sistema no pregunta la etnia, y el criterio se aplica solo con la edad, el IMC, el antecedente familiar, la hipertensión y la actividad física.
2. **Perímetro abdominal.** Ningún mensaje se activa por el perímetro abdominal, porque no se pudieron verificar puntos de corte específicos para población sudamericana.
3. **Recursos locales.** Los mensajes remiten de forma genérica a un "establecimiento de salud".
4. **Fuentes.** Las guías citadas son de EE. UU. y de la OMS.

## 7. Calificación

Para cada mensaje, cada experto califica de 1 (no cumple con el criterio) a 4 (alto nivel), en la ficha de validación (`juicio_expertos/Ficha_juicio_expertos.docx`):

| Criterio | Pregunta |
|---|---|
| Sustento | El mensaje es coherente con la fuente citada |
| Pertinencia | El mensaje corresponde al criterio que lo activa |
| Claridad | Una persona sin formación en salud lo entiende |
| Prudencia | No promete resultados ni puede interpretarse como diagnóstico |

Los mensajes con V de Aiken menor a 0.80 se corrigen. Cada cambio queda registrado con fecha en el protocolo, y la versión del catálogo se actualiza.
