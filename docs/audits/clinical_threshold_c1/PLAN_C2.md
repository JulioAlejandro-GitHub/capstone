# C2 — Propuesta mínima, sin implementación

Estado documental: `HISTORICAL_AUDIT` — propuesta derivada de C1; requiere aprobación independiente para implementarse.

**Metodología: auditoría estática, sin ejecución de código, pruebas ni consultas PostgreSQL.**

## Decisión técnica propuesta

Reutilizar `find_threshold_for_target_recall` y el flujo de eventos/proyecciones existente. No crear otro calibrador, tablas ni migraciones como punto de partida. El ejecutor ya llama al algoritmo: la brecha de activación está en la configuración pública del protocolo, acompañada de correcciones de semántica y trazabilidad. Conservar inmutables campañas, scores, evaluaciones y checkpoints históricos B1.

La propuesta adopta para **un nuevo protocolo C2** el objetivo solicitado `recall >= 0.98`. E7 declara `>0.98` y posee otro selector con desempates distintos; no se debe renombrar E7 ni afirmar equivalencia. C2 debe versionar explícitamente el criterio y preservar el comportamiento histórico. C1 no cambia ninguno de ellos.

## Intervenciones clasificadas

| Intervención | Clasificación | Alcance mínimo / criterio revisable |
| --- | --- | --- |
| Búsqueda desde labels/scores VAL | **Ya implementada** | Reutilizar evaluation/threshold_calibration.py:154. No cargar modelos para retrospectiva. |
| Invocación después del checkpoint | **Ya implementada** | execution/train.py:273–299; conservar independencia frente al entrenamiento por época. |
| threshold_grid → calibrate_threshold | **Ya implementada** | campaigns/contracts.py:318–343; no agregar flag redundante al ejecutor de campaña. |
| Exposición en configuración pública | **Requiere conexión** | Incluir elección none/threshold_grid en nuevo protocolo normalizado, catálogo y formulario/contrato aplicable; snapshot/hash deben recogerla. No introducir override de campaña congelada. |
| Semántica >= frente a > | **Requiere corrección** | Documentar/versionar comparador y desempates de C2, resolver divergencia con E7 sin alterar reportes ni protocolo antiguo. |
| Restricciones no factibles | **Requiere corrección** | Conservar candidato fallback sólo como diagnóstico; informar cumplimiento de recall, especificidad y conjunto por separado. No aplicar/presentar fallback como decisión clínica aprobada. |
| Consumo clinical en evaluación E6 | **Requiere corrección** | assessment.contracts.threshold verifica evidencia VAL/umbral pero no factibilidad; propagar la distinción diagnóstico/aprobado sin recalibrar TEST. |
| Validación de entrada antes de búsqueda | **Requiere corrección** | Exigir arrays no vacíos de igual largo, labels exactamente {0,1}, ambas clases, scores finitos en [0,1]; no ocultar errores con clip. Homogeneizar precisión candidatos/métricas. |
| beta | **Requiere corrección** | Buscador directo debe rechazar beta≠2 como ya hace resolver; no fingir F-beta general. |
| Colapso final | **Requiere corrección** | Definir política explícita para resultado calibrado y propagar min_class_fraction/rechazo si son restricciones; no heredar implícitamente la aptitud del checkpoint a .5. |
| Objetivo de cierre TRAIN | **Requiere corrección** | Diferenciar cumplimiento de selección a .5 y cumplimiento de evaluación final al threshold aplicado. Usar target y comparador congelados; no basarse sólo en selection. |
| Persistencia de umbral, pareja y conteos | **Ya implementada** | Reutilizar ResultService y v2_projection; hashes de checkpoint/protocolo/población. |
| Flags, restricciones y advertencias en vista/API | **Requiere corrección** | Completar proyección de columnas existentes o lectura explícita del evento; no fabricar valores ante null ni tomar 'latest' como identidad científica. |
| Ceros Python frente a null SQL | **Requiere corrección** | Rechazo de una clase para calibración; documentar contrato nullable de evaluación y probar su consistencia, sin modificar métricas históricas. |
| Verificación aislada de algoritmo y persistencia | **Requiere corrección** | Añadir casos faltantes y pruebas de contratos; su ejecución corresponde a C2 autorizado, no C1. |
| Nuevo sistema Youden o tercera búsqueda | **No necesaria** | No responde al contrato identificado; evitar duplicación frente a TRAIN/E7. |
| Cambiar umbral de checkpoint .5 | **No necesaria** | La calibración final es una decisión separada. Mantener selección comparable salvo futura revisión científica independiente. |
| TRAIN, modelos, inferencia, TEST para retrospectiva | **No necesaria** | Scores VAL históricos bastan si su integridad actual se confirma. |
| Cambiar .env, activar Metal, dependencias o migraciones | **No necesaria** | No habilitan las conexiones identificadas. |

## Secuencia propuesta

1. Fijar contrato nuevo: recall inclusivo, criterio lexicográfico conocido, especificidad mínima explícita (sin inventar una cifra clínicamente aceptable), colapso, entrada válida y resultado no factible. Reutilizar y corregir el buscador actual, con compatibilidad versionada.
2. Conectar configuración pública a `threshold_grid`, manteniendo las validaciones de conflictos y el hash de protocolo. Verificar que request, resolved, snapshot RUN y flag ejecutado coincidan.
3. Corregir el cierre y la proyección v2, conservando evento completo, pareja default/selected y evaluación final inequívoca. No confundir `recorded`, `completed` o `policy_satisfied` con aptitud clínica.
4. Añadir pruebas puras y de contratos. Las pruebas de BD sólo en entorno de ensayo autorizado; nunca sobre B1. Mantener TEST excluido de calibración y de esta validación de implementación.
5. Para retrospectiva B1, recuperar exclusivamente los scores existentes ligados al checkpoint seleccionado. Producir resultados derivados separados, con algoritmo/protocolo/fecha e identidad de origen; conservar el umbral histórico y las métricas originales.

## Retrospectiva B1: requisitos y límite de la vía existente

Evidencia B1 Q17 acredita 12 × 2693 scores y labels del mismo VAL (1325 positivos, 1368 negativos). Los CSV públicos contienen resultados agregados y snapshots, no las listas completas. Se necesita lectura futura autorizada de `train_execution_records(kind='predictions')`, enlazada a final VAL/artifact/epoch, o un snapshot íntegro acreditado.

Validar unicidad por muestra, concordancia de población/label mapping, ambas clases, rango y finitez, checkpoint/hash y versión de dataset; preservar precisión original y declarar operador inclusivo. No recalibrar usando métricas redondeadas ni selección de una época diferente. Registrar para cada RUN métricas a .5 y propuesta, conteos, satisfacción separada, colapso y motivo de fallback.

La función numérica ya acepta arrays y no necesita TensorFlow/modelos. **La ruta CLI `calibration_cli.main` sí carga modelo e infiere**, por lo que no es la entrada adecuada para esta retrospectiva. C2 necesitaría una conexión acotada de datos históricos al buscador existente.

No insertar ingenuamente una calibración nueva como si hubiera ocurrido en el TRAIN B1: `v2_calibration_pair_guard` exige target del RUN y las proyecciones están vinculadas a eventos/protocolo originales. El formato mínimo inicial puede ser un resultado derivado separado; cualquier persistencia oficial debe reutilizar contratos existentes tras revisar su elegibilidad, sin sobreescribir el histórico. Esa elegibilidad para resultados retrospectivos no quedó demostrada por C1. El comparador E7 ya conserva propuestas separadas, pero sus requisitos de linaje E6 y su política estricta impiden asumir que acepte B1 sin adaptación.

## Pruebas recomendadas

| Caso | Aserción necesaria |
| --- | --- |
| Recall exactamente 49/50 | Cumple C2 >=.98; no se confunde con E7 >.98. |
| Recall y especificidad incompatibles | Estado conjunto no factible; no aceptación clínica por recall aislado. |
| Sólo positivos / sólo negativos / vacío | Error explícito antes de búsqueda; no sensibilidad/especificidad ficticia. |
| NaN, ±Inf, −.1, 1.1, labels fraccionarios | Rechazo sin clip/truncamiento silencioso. |
| Empates, orden invertido, extremos 0/1 | Resultado determinista; >= consistente; score=1 no queda excluido por t=1. |
| Float64 próximos a frontera float32 | Igual semántica de candidatos, conteos y threshold aplicado. |
| Predicción colapsada al calibrar | Estado y política final explícitos, independientes del checkpoint. |
| Calibración apagada | .5/default, ausencia de evento de calibración efectiva; final VAL disponible en ruta con emitter. |
| Calibración encendida | Mismo t/matriz entre buscador, evaluación, evento, pareja relacional y API. |
| Snapshot/protocolo y CLI | threshold_grid se resuelve en true; none en false; conflictos rechazados; campaña congelada sin override. |
| Final calibrado satisface y selección .5 no | Flags de selección/final distintos y explicables. |
| Persistencia/reintento | Pareja y evento idempotentes; fallos sin aprobación falsa; restricciones/warning no desaparecen. |
| Retrospectiva | Sólo scores de selected checkpoint y VAL; ningún TRAIN/model.predict/TEST; originales idénticos. |

## Criterios de aceptación de C2

Un protocolo nuevo reproducible activa el flujo existente; threshold y métricas corresponden exactamente a la misma decisión; restricciones y denominadores indefinidos tienen estado explícito; el resultado se reconstruye desde snapshot/evento/evaluación con linaje intacto; la API presenta ese mismo resultado; pruebas pertinentes acreditan los casos anteriores. B1 permanece inalterado y cualquier propuesta retrospectiva se rotula exploratoria. Alcanzar sensibilidad puntual en VAL no certifica seguridad clínica, calibración probabilística ni generalización externa.
