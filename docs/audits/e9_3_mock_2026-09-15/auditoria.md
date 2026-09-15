# Auditoría de persistencia y orquestación con mocks — 15/09/2026

**AUDITORÍA PARCIAL.** Los contrastes de proceso/persistencia y el motor TRAIN mínimo están verificados. No se acredita aún un recorrido integral TRAIN→VAL→selección E7→TEST con gobernanza sintética completa. No se aprueba E9.3.

## Resultado de la hipótesis

Para el run real `79f39931-ac71-4bc1-a317-149a975d1f74`: **fallo de proceso demostrado**, OOM de RAM probable. Evento process_exit=-9, delta oom_kill=1, cinco épocas persistidas y log de sexta época, sin completion ni verification. No hay evidencia de fin de fit, finalización exitosa o error PostgreSQL que explique el SIGKILL. Los checkpoints parciales no prueban cálculo completo. Un error de BD inyectado demuestra que ese escenario es posible y distinguible; no demuestra que ocurriera en el histórico.

## Orden real y fronteras transaccionales

1. `GlobalGate.acquire` toma advisory lock y comprueba identidad/recursos/procesos. Las reservas E9.3 requieren el propietario en SQL. `ControlledRepository.reserve` o `ExecutionRepository.claim` crean intento/run/sesión en una transacción. El primero conserva idempotencia por request_id y permite el intento único con campaña paused.
2. `campaign.run_child` crea hijo con handshake, persiste su identidad y autoriza ejecución; `worker.main` valida token, carga sesión/revisión y llama a `execution.train.train`.
3. TRAIN crea datasets TRAIN/VAL y compila el adaptador. Persiste runtime. Dentro de cada on_epoch_end: `put(epoch)` confirma una transacción; calcula selección; `put(artifact_prepared)` confirma otra; guarda archivo partial y renombra; `put(artifact)` y `put(selection)` confirman por separado; calcula predicciones VAL internas y las persiste. Archivo y BD NO forman una única transacción atómica.
4. Tras volver de fit se persiste phase/completed. Se carga el checkpoint seleccionado, calcula calibración VAL y la persiste. Sólo entonces construye records_hash y llama a `finish(completed)`.
5. `ExecutionRepository.finish` actualiza sesión, intento y run dentro de una misma transacción. Un rechazo en la última actualización revierte las anteriores; registros de épocas de transacciones anteriores permanecen.
6. El padre espera la salida y descendientes. Código cero por sí solo no acredita éxito. Comprueba completion y `verify_session`, incluyendo hash/carga/checkpoint exacto; `finish(verified)` confirma la verificación. Cola secuencial reserva el siguiente sólo después; controlled termina sin avanzar.
7. `assessment.service.run` es otra ejecución, no la validación interna de fit: reserva identidad/intento, predice batches, write_batch confirma resultados, verify comprueba y finish(verified) confirma terminal. Fallos se registran en ese intento, conservando TRAIN.
8. E7 `ScienceRepository.freeze_final` lee reporte VAL, resuelve linaje/dataset, reconstruye identidad TEST y escribe lock exacto. TEST E6 requiere ese lock. No es una fase automática del coordinador TRAIN.

## Pruebas reales realizadas

Compose canónico y PostgreSQL real, esquemas aleatorios capstone_test_e4_. Ningún SQLite ni otra BD. `make_visible` confirma la transacción de creación del esquema y ofrece conexiones independientes con search_path exclusivo: las lecturas posteriores sí comprueban commits visibles. No se simulan métodos de persistencia. Inyección SQL mediante triggers sólo en tablas sintéticas. SIGKILL sólo al PID de un hijo creado por la prueba; no se provocó OOM.

Nueve casos finales nuevos aprobados en 8.12 s, 3 warnings de dependencias/Keras. Previamente se ejecutaron 46 pruebas conjuntas, 1 control histórico E6 excluido, 3 warnings, en 25.77 s. Hay solapamiento: no sumar 46+9 como casos independientes. El control público E6 exige un head histórico y no forma parte de estas pruebas sintéticas. No se cuentan pruebas antiguas como nuevas.

| Escenario | Esperado | Observado |
|---|---|---|
| Cálculo simulado válido / fallo al guardar epoch | Sin completion; error SQL | 23514, sesión no completada, cierre failed |
| Archivo escrito / fallo de artifact | Archivo parcial identificable, sin falso éxito | Archivo conservado en fixture, rechazo SQL, failed; no se ejerció recuperación automática |
| Fallo final al actualizar runs | Rollback de sesión e intento de esa transacción | completion null y run no completed desde otra conexión |
| Commit y pérdida de confirmación cliente | Consultar antes de repetir | Commit real confirmado; excepción simulada después de retorno; readback y request idempotentes. No simula caída de red durante COMMIT |
| Conexión perdida | Error DB y conexión posterior utilizable | Invalidación sólo del cliente sintético; operación rechazada, nueva lectura válida |
| FK inválida | Rechazo sin fila huérfana | Rollback y conteo sin cambios |
| Finalización repetida | Sin duplicados | Rechazo conservador de transición; registro previo intacto. No devuelve éxito idempotente de finish |
| Dos reservas/coordinadores | Un propietario | Pruebas globales y E6 de concurrencia aprobadas |
| Muerte durante cálculo | Sin completion | Hijo SIGKILL -9, sin registros de fin; no se interpreta como OOM |
| Persistencia VAL/TEST rechazada | TRAIN válido intacto | TRAIN verified, assessment failed, cero predicciones parciales |
| Cálculo real mínimo | fit, serialización, commit, carga | Motor real train(), adaptador mínimo, 1 época, imágenes sintéticas; completed y verified desde nuevas conexiones |
| Cola de varios miembros | Verificar antes del siguiente | Prueba global de 12 miembros completó en orden, con motor simulado |

Nivel B usa un adaptador sólo de test (GlobalAveragePooling + Dense), compilador/callbacks/serialización/verificador/repositorio reales. Dos imágenes por partición, ambas clases, nombres UUID de pacientes disjuntos; TEST sintético creado pero no leído por TRAIN. Dataset con UUID de fixture distinto del real. No reproduce capacidad de modelos completos. La finalización usa registros de artefactos E5; no acredita inserción de una versión en todas las tablas históricas simplificadas.

## Límites que impiden declarar el recorrido integral solicitado

El fixture E4 declara explícitamente padres sintéticos simplificados (dataset_versions contiene sólo id, entre otros). El verificador E1 de gobernanza está sustituido por un snapshot de fixture. Las pruebas previas de freeze_final sustituyen read_report/read_evaluation/dataset_samples; la inyección de error TEST nueva usa un lock sintético directo sólo para aislar persistencia. Por tanto no se acredita generación de selección/manifiesto E7 real ni validación completa de población sellada por el flujo oficial. No se ocultó esto detrás de resultados verdes.

Tampoco hay todavía un único ensayo que una el cálculo real mínimo con VAL/TEST de cálculo real y umbral conocido, toda la selección oficial, y workers/subprocesos en cada frontera. Se verificaron esas piezas de forma separada. La recuperación trazable de archivo huérfano quedó limitada a identificación/conservación; no se ejecutó recuperación. La pérdida de ACK se simuló después del commit retornado, no con interrupción en el protocolo de red.

Para cerrar esta auditoría integral falta un fixture aislado de gobernanza completo: tablas/constraints de materialización, pacientes, manifiestos, versiones y linaje, más generación de evidencia E1 y reporte E7 sin sustituir lectores ni validadores. Debe mantenerse en el esquema desechable; no reutilizar dataset ni campaña reales. Esta entrega no presenta ese trabajo como realizado.

## Conservación del entorno

Campaña real `3acf89b7-dc42-4b7a-8e2a-ca6ea024c344`, dataset `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`: permanecen pausados/sin cambios. Run real failed, bloqueo NEW_CONTAINER_OOM_PAUSE conservado, contador OOM=6. Cero nuevas reservas reales. No se tocó TEST real, publicación o deployment ni se aplicaron migraciones públicas. Las migraciones usadas por fixtures se ejecutaron sólo en esquemas sintéticos y se eliminaron al finalizar.

Código funcional y revisión técnica registrados no cambiaron; únicamente se añadió test_pipeline_faults_postgres.py y documentación. No hace falta activar otra revisión de producción para estos tests (el fingerprint de ejecución excluye tests). No se corrigió ningún defecto de producción porque los casos probados no demostraron uno. La prueba mínima inicialmente rechazó un snapshot de fixture incoherente: se creó nueva evidencia sintética, conservando el evento anterior; no se relajó el validador.

Antes de otro TRAIN real: mantener pausa, investigar crecimiento de RAM por fase y obtener evidencia de víctima OOM si está disponible. No justificar un reintento como “corrección de BD” con estos resultados. Cualquier parche necesita prueba y revisión técnica nueva antes de activarse. Ninguna continuación fue ejecutada.
