# Propuesta v2 — Aprender pesos exclusivamente en VALIDATION

**PENDIENTE DE APROBACIÓN. No ejecutada ni activada.** Sustituye como propuesta a la ruta de pesos fijos v1, conservando ese documento histórico. La decisión del usuario sí aprueba principal individual E7, ensembles secundarios y baseline uniforme 1/3 por arquitectura. No hay autorización para fijar pesos desiguales ni para ejecutar este aprendizaje.

## Diseño propuesto

Se mantiene la matriz TRAIN, dataset/split sellado, arquitectura, preprocessing, aumentación y semillas. Dentro de la VAL existente se propone una asignación **analítica nueva** por paciente, sin modificar dataset_split_assignments: FIT para pesos/umbral y COMPARISON para contrastes secundarios. No se afirma que esta asignación existiera en E7.

Una sola asignación compartida por los 12 grupos optimizador-semilla: estratos por clases presentes en cada paciente (0,1,0+1); ordenar cada estrato por SHA256 de `e9_2_val_roles_v1|7302|UUID_PACIENTE_CANONICO` y desempatar por UUID; índices pares FIT e impares COMPARISON. Proporción objetivo 1:1. Antes de acceder a scores para ajustar, persistir membresía, reglas, conteos y hashes; exigir pacientes disjuntos, ambas clases y al menos dos pacientes por rol. Si falla, bloquear y revisar el diseño; no buscar otra semilla favorable. Ese mínimo sólo permite el procedimiento, no acredita potencia estadística.

Para cada grupo se exigen tres modelos exactos (Custom CNN, VGG16, DenseNet121), mismo optimizador/semilla, pacientes/muestras/clases alineados por ID, sin mezclar repeticiones. Se aprenden pesos separados para los 12 grupos, preservando todas las semillas.

## Objetivo y presupuesto cerrado

Evaluar una rejilla exhaustiva de vectores `(i/20,j/20,k/20)` con enteros no negativos cuya suma sea20 y al menos dos componentes positivos. Son228 vectores; agregar el uniforme exacto1/3 da **229 candidatos por grupo, 2748 puntuaciones como máximo en 12 grupos**. Sin reinicios, refinamiento, optimizador continuo ni candidatos posteriores a observar COMPARISON.

Objetivo propuesto: minimizar log-loss binaria media por paciente FIT. Primero promediar las pérdidas de sus células; luego promediar pacientes con igual peso. Para el cálculo de log solamente, recortar probabilidad a `[1e-7,1-1e-7]`; no modificar los scores almacenados ni el dominio de inferencia. Esta elección es nueva, propuesta por el asistente, no una regla histórica de E7 ni garantía de mejorar sensibilidad.

Desempates: candidatos con pérdida <= mínimo+1e-12; menor distancia cuadrática al uniforme; luego orden lexicográfico del vector en orden Custom CNN,VGG16,DenseNet121. Si gana uniforme, informar coincidencia con baseline; nunca forzar pesos desiguales. No evaluar 229 umbrales sobre COMPARISON para seleccionar vector.

## Orden, umbral y comparación

Probabilidades raw de miembros → sin calibrador individual → combinación → sin calibrador ensemble → umbral E7 obtenido **sólo en FIT**, después de elegir pesos. Para ese vector explorar scores FIT únicos más0/1; sensibilidad parasitized estrictamente >0,98, luego especificidad,F2,umbral mayor. Conservar fallback explícito de E7 y rechazo si no hay ambas clases.

Para contrastes comparables, derivar también umbrales específicos de esta comparación para uniforme y miembros usando el mismo FIT. No reemplazan el umbral ni la decisión original del principal E7. Evaluar cada resultado fijo una vez en COMPARISON, con comparación pareada por paciente, sin reseleccionar pesos/umbral/modelos por desempeño. El baseline siempre-parasitized se informa conforme a E7.

Presupuesto de umbral: una búsqueda finita `N_fit_scores_unicos+2` como máximo para el vector elegido, y una equivalente por baseline/miembro; no es una nueva búsqueda de pesos. Los IC conservan E7:1000 remuestreos de pacientes,seed7301,mínimo20 pacientes y95% de réplicas válidas. Si COMPARISON tiene menos de20 pacientes (posible con esta VAL), los IC quedan no estimables; no reducir el mínimo ni usar bootstrap de células. Se reportarán soportes y limitación, sin promesa de significancia.

Congelar pesos y umbral FIT; **no reajustarlos con toda VAL después de observar COMPARISON**. TEST sigue cerrado, y cualquier contraste final requerirá E9.5 e implementación posterior autorizada. No elegir un nuevo principal a partir de estos contrastes.

## Límite de independencia e impacto

La separación propuesta evita usar los mismos pacientes para aprender pesos y medir su contraste directo, pero **no deshace la exposición de toda VAL en selección de checkpoint/early stopping de E7**. FIT/COMPARISON siguen condicionados a esos checkpoints; el contraste es exploratorio y no un holdout independiente del proceso completo. No se llama prerregistro original a esta enmienda posterior al inicio de TRAIN.

No repetir TRAIN sólo por esta combinación posterior, ni alterar el coordinador. La única forma de sostener una separación más fuerte respecto de selección de checkpoint requeriría un protocolo futuro con selección anidada/datos no expuestos y posible repetición, fuera de esta propuesta. TEST tampoco se declara intacto por esta división analítica.

La fecha de aprobación futura, la exposición conocida (progreso TRAIN y estados ya visibles) y la exposición no verificable de otros actores deben persistirse antes del ajuste. Si hubiera resultados ensemble previos con otra decisión, conservarlos como otra revisión; no sobrescribirlos ni mezclarlos.

## Dependencias de activación

E8 actual sólo acepta procedencia predeclared de pesos fijos y ejecución VAL. No etiquetar pesos aprendidos como predeclared. Una subetapa posterior deberá implementar y probar una revisión explícita learned-weight que preserve membresías FIT/COMPARISON, hashes de fuentes, pérdidas de búsqueda, desempates, pesos/umbrales elegidos y lectura íntegra PostgreSQL antes de exportación. Esta especificación no está conectada al ejecutor y no modifica archivos bajo src/configs.

La autorización actual permite preparar esta propuesta, **no aprender pesos ni ejecutar comparaciones**. E9.2 sigue PARCIAL hasta aprobación de la enmienda; E9.3 TRAIN no depende de ella.
