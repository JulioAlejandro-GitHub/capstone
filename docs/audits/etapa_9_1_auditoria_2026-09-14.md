# E9.1 — Conciliación del estado real

**APROBADA para conciliación y preparación condicionada de reanudación.** E9 no está aprobada. No se inició E9.2. El trabajo existente continúa; no se lanzaron, reanudaron, cancelaron ni reiniciaron procesos, no se cambiaron estados, no se ejecutaron pruebas con escritura, EVALUATE, EXPLAIN o TEST, ni se modificaron código funcional, configuración, publicación o deployment. Los únicos archivos creados son evidencia de E9.1.

## Observaciones fechadas

Fecha real: 2026-09-14. Zona local America/Santiago (UTC−03:00).

- Snapshot PostgreSQL: **12:24:39.910709 UTC / 09:24:39.910709 local**. Una transacción explícita REPEATABLE READ, READ ONLY cubre campañas, matriz, intentos, sesiones, registros, revisiones, referencias TEST y publicación inicial. No se usan consultas independientes para sumar los conteos.
- Procesos: 12:24:40.036131 UTC y 12:25:34.067417 UTC (09:24:40 y 09:25:34 local). Son observaciones posteriores y separadas del snapshot.
- Recursos: 12:24:40.104265 UTC. Readiness se consultó después en el mismo comando; el inventario conserva inicio/fin.
- Publicación final: **12:25:34.323171 UTC / 09:25:34.323171 local**, nueva lectura READ ONLY. Sin diferencias respecto del snapshot inicial.

Los estados pueden avanzar después de esas horas; este informe no congela la campaña ni pretende ser un monitor continuo.

## Entorno y fuente

Host HEAD `c782c4b8092a6c3cfbe7c9fb399939952b6ac554`; Git disponible en host, ausente en contenedor. Se preservaron los dos cambios funcionales E9 existentes (campaigns/service.py y models/optimizers.py) y todos los documentos/pruebas sin commit enumerados en la entrega anterior. No se encontró AGENTS.md en las búsquedas de repositorio y ancestros. Se leyeron las referencias de seguimiento/publicación/operación E9, E7/E8, linaje, almacenamiento, wrappers y aislamiento. No se ejecutó ningún wrapper de migración.

Base malaria_experiments, esquema public, revisión instalada `20260912_02`; backend database/migrations/storage ready. Entorno vigente coincide exactamente con environment de la campaña sucesora, incluida huella de fuente `d8569d8faaa80eca42b130e6096203d851e2c663b4cdb8cd599dda950fbe6430`. Git null en la evidencia del contenedor no se sustituye por el commit del host. La huella de fuente y la revisión host cumplen funciones distintas.

CPU lógicas 16; MemTotal 8125656 kB, MemAvailable 2699484 kB; disco libre 855573147648 bytes. No se observaron nodos /dev/nvidia*. La ausencia de GPU TensorFlow procede del preflight E9 histórico; no se importó TensorFlow para volver a enumerar dispositivos durante el TRAIN. E5 ejecuta un hijo a la vez por coordinador; sólo se observó el coordinador de la campaña y su worker correspondiente. PYTHONHASHSEED=42, TF_DETERMINISTIC_OPS no definido en entorno; la opción determinista por ejecución permanece en la configuración congelada. No se alteró concurrencia.

## Matriz e intentos conciliados

Fuente: configs/science/e7_v1.json y contrato E4 congelado en PostgreSQL. Las 12 claves de configuración coinciden con E7; semillas 11,29,47; expected_count=36. El repositorio valida contrato/hash y reconstrucción de configuraciones/miembros. Hay 36 pares únicos configuración-semilla y 36 IDs de miembro. No se mezcla optimizador ni se cuentan intentos como nuevos experimentos.

| Campaña | Estado | Previstas | Pendientes | Activas | Fallidas | Interrumpidas | Completadas | Verificadas | Intentos |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 3acf89b7-dc42-4b7a-8e2a-ca6ea024c344 | active | 36 | 35 | 1 | 0 | 0 | 0 | 0 | 1 |
| ec442763-7eea-499d-a94f-9a3ddfb7c0f0 (antecesora) | paused | 36 | 32 | 0 | 3 | 1 | 0 | 0 | 4 |

Sucesora: 35 experimentos sin intento; no hay duplicados de Run ID ni intentos sin miembro de la matriz. No hay estado canceled en las sesiones E5: la interrupción se informa bajo su estado real. La antecesora es historia de la misma matriz, no 36 experimentos adicionales aceptados. No hay reintentos ordinales >1 observados: la sucesora reinicia la matriz bajo otra huella de código y documenta su relación mediante purpose, no mediante un supuesto FK de reintento entre campañas.

Las 36 filas sintéticas previstas en el documento E7 son una condición no disponible y no forman parte de esta campaña original congelada. Los 24 grupos de ensemble E8 tampoco son TRAIN adicionales. No se fuerza un total de 72 o 96 entrenamientos.

Inventario estructurado: `etapa_9_1_inventario_2026-09-14.json`, con miembros, arquitectura, condición, semilla, hash, todos los intentos, sesiones, worker, última actividad, artefactos/versiones registradas, incidencias y acciones propuestas.

## Actividad confirmada

TRAIN `a5f36df1-3341-43fd-94b9-ee1cedb834c5`: Custom CNN, Adadelta, semilla 11; estado active. Padre PID 3475 y worker PID 3483 en el mismo hostname registrado. Los argumentos del padre contienen el campaign_id y los del worker el Run ID. Ambos mantienen start_ticks entre observaciones, evitando confundir reutilización de PID. El worker aumenta utime de 1082952 a 1111260 y stime de 1860615 a 1902305. **Actividad confirmada**. El padre en S es compatible con wait del hijo; no implica huérfano.

E5 no implementa un lease/heartbeat temporizado para estas sesiones: registra host/PIDs y progreso estructurado. La conciliación de `--resume` usa `dead_local`, que exige mismo host y ausencia probada de padre e hijo; un host distinto o permiso denegado no demuestra muerte. La edad de updated_at, por sí sola, no permite recuperar una sesión.

Último registro observado: 12:14:47.816173 UTC / 09:14:47.816173 local. Hay seis registros: runtime, epoch, artifact_prepared, artifact, selection y predictions (uno de cada tipo). No se recopilaron ni recalcularon métricas científicas en esta subetapa.

Checkpoint de época 1 registrado: epoch_1.keras, 5150212 bytes, SHA-256 registrado `231675fd96a823b48ea6380f44d4eab2c58b1c6c52b6bbf75e3fe01d247dc482`, version_id en payload `6b3d8f88-47b7-4fcd-8b8d-ebfd2fe676a3`. Es evidencia intermedia; no se afirma que sea el checkpoint final seleccionado ni una model_version relacional ya publicada. La lista de versiones relacionales consultada por TRAIN queda en el inventario. No se hashearon archivos del TRAIN activo para declararlos definitivos ni se cargaron modelos.

No hay TRAIN completed/verified en ninguna de las dos campañas al snapshot: la verificación de completados no tiene casos aplicables. Se distingue expresamente ese cero de una aprobación documental/física o científica. El verificador existente requiere registros completos, selección exacta, hash de bytes y carga del modelo; esa carga no se ejecutó en E9.1.

## Impacto de correcciones

Los informes E9 documentan ambas correcciones el 14 de septiembre, sin timestamp exacto del edit acreditado. `planning_environment` antes fallaba si faltaba git; el parche conserva null y digest. Falló creación antes de disponer de campaña en el intento inicial histórico; no se le atribuyen fallos TRAIN por inferencia.

En la antecesora, los tres runs `d99aac41-a1a3-4264-a110-48be6584d7a4`, `7e7ec232-2ab7-4f03-8458-d3f0b394d2a5`, `1b90a974-f81b-41cf-bdda-c3a24962689a` conservan causa genérica CHILD_EXIT_OR_INCOMPLETE_RESULTS y cero registros. La reproducción histórica documentó rechazo de learning_rate entero en Adadelta; la DB no guarda la excepción original específica para cada run, por lo que esa atribución se mantiene con ese límite. El cuarto run `66fa0104-e6f9-4099-b0c9-14b1b61995da` está interrupted, con runtime; la intervención SIGTERM pertenece a E9 anterior, no a E9.1.

La huella actual no coincide con la antecesora y sí con la sucesora. Las configuraciones/dataset/environment de todas las sesiones corresponden a sus respectivos contratos. El worker carga configuración desde PostgreSQL y los módulos al arrancar un nuevo proceso; la sucesora se creó después de la corrección y su sesión registra la misma huella actual. No se afirma medir en memoria cada módulo de un proceso ya vivo ni aplicar parches retroactivamente. Las 26+4+1 pruebas son evidencia histórica; no se repitieron.

## TEST y publicación

El cierre de TEST combina evaluate_best_on_test=false de TRAIN, guarda de identidad final E6 y assessment_final_locks, más la restricción VAL de E8. En el snapshot hay **cero assessment_identities/attempts** y cero final locks en la instancia: no hay TEST E6 atribuible a esta campaña. Eso es distinto de la configuración que prohíbe TEST y no descarta ejecuciones externas no registradas.

Históricos legacy: 36 evaluaciones, 12 con el UUID de dataset designado y 24 sin UUID. **Ausencia de uso histórico de TEST: no acreditada.** No se abrieron imágenes ni se evaluaron modelos; tampoco se declara TEST intacto.

Publicación activa `81d69942-17eb-4999-a6bd-2b05779a65a4`, datasource malaria/scope stage2. Deployment activo `cf2f20d3-a1e0-499c-b5ab-501b7c1ae198`, slot stage2/default. Ambos referencian versión `172b7031-9f79-44e3-a7ad-2dc10a9ffd08`, TRAIN `623ad00c-0b03-4cf0-8f2c-bb9496efb496`, checkpoint `44577ce0-1a80-4971-9f3d-bd78d2a63bf4`; la publicación referencia EVALUATE legacy `243b1d73-8bae-4a23-a92d-ae2d4b15de31`. IDs coinciden con la evidencia E9 anterior disponible; TRAIN/checkpoint se obtuvieron de lectura actual, no de memoria. Una selección activa observada por datasource y un deployment por slot; no se confunde este conteo con una prueba de todas las constraints de unicidad. Sin cambios entre consultas inicial y final. Persisten los hallazgos de publicación E9; esta subetapa no los repara.

## Conclusión

La matriz está conciliada, no hay ambigüedad que justifique iniciar otro worker y hay actividad confirmada. **La próxima acción segura es dejar continuar el coordinador existente y consultar estado.** La reanudación con escrituras queda preparada y condicionada a una interrupción acreditada, fuente compatible y controles del plan adjunto. Pesos ponderados pendientes bloquean ese ensemble, no los TRAIN individuales actuales. No hay candidato ni resultados finales; no se aprueba E9 ni se inicia E9.2.
