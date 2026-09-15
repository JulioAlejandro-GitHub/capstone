# E9.3 — Verificación del intento controlado

**INTENTO FALLIDO.** Verificado el 15/09/2026, 05:43 America/Santiago. E9.3 permanece EN SEGUIMIENTO; E9 no aprobada. E9.2 parcial.

Campaña `3acf89b7-dc42-4b7a-8e2a-ca6ea024c344`; dataset `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`; run `79f39931-ac71-4bc1-a317-149a975d1f74`; revisión técnica `3ec6fa57-be3f-5433-8557-8c12c3eea740`; solicitud `7d4cacb1-3d85-53f6-9828-8a7b1e0164c5`. Miembro posición 0 CustomCNN/Adadelta/11, intento ordinal 2 `4cd0cf3f-37df-4490-9f26-eb2763f3b4e6`, conserva vínculo con el intento previo.

## Resultado comprobado

Run, sesión e intento están failed. Causa persistida `CONTROLLED_CHILD_EXIT_-9`. Evento oficial process_exit: worker PID 42346, exit_code=-9 (SIGKILL), remaining_pids=[], oom_kill_delta=1. El CLI terminó con código 1 y CampaignError NEW_CONTAINER_OOM_PAUSE. No fue terminación normal ni early stopping. Completion y verification son null.

Inicio 14/09 22:09:17 local; última actividad de registros 23:05:11; finalización del intento 23:05:39. Cinco épocas completas registradas, último epoch a 23:04:59. El log muestra Epoch 6/50 y lote final observado 13/347. No se infiere una sexta época completada ni un checkpoint final.

El verificador oficial verify_retained_processes confirmó ausencia de los procesos retenidos usando host/boot/PID/start_ticks/sesiones. Mismo boot_id que al lanzamiento. Escaneo actual no encuentra procesos gestionados ni hijos; advisory owners=0. El gate no tiene owner/db_pid, release_confirmed=true, pero mantiene blocked_reason=NEW_CONTAINER_OOM_PAUSE. No hay inconsistencia que requiera marcar manualmente un resultado o liberar una reserva.

## Recursos y atribución

Confirmado: hubo un nuevo OOM kill en el cgroup durante el intervalo del intento (5→6) y el worker salió por SIGKILL. Mismo contenedor 3dba8e7dcf1b, StartedAt 08/09/2026 16:27:29 UTC, RestartCount=0; contadores comparables. La marca Docker OOMKilled es evidencia adicional del contenedor, no identificación individual de víctima.

**Causa probable:** agotamiento de RAM asociado al fallo del worker, por coincidencia de salida y delta OOM con un único TRAIN. **Pendiente:** registro del kernel con PID víctima/timestamp que permita atribución individual inequívoca. El evento oficial explícitamente conserva individual_oom_attribution=not established. No hay ResourceExhaustedError en el log; no se acredita OOM de GPU.

Mayor muestra del worker disponible: 4318326784 bytes (4,02 GiB); mayor muestra del contenedor en las observaciones guardadas: 5118169088 bytes (4,77 GiB). Son máximos entre muestras tempranas, no picos durante los 56 minutos. memory.peak actual=7386435584 bytes (6,88 GiB), de vida del cgroup, no atribuible íntegramente a este intento. cgroup max=max no significa memoria física ilimitada. Datos CPU/swap originales permanecen en observaciones previas. En la consulta actual no quedan hijos consumiendo recursos.

## Artefactos y linaje

Cinco checkpoints parciales epoch_1.keras a epoch_5.keras, cada uno 5150212 bytes: existencia, tamaño y SHA-256 coinciden con sus referencias persistidas. Se conservaron todos; no se cargaron como modelo final ni se ejecutaron pruebas de carga nuevas. Hay cinco registros epoch, selection y predictions de validación interna, además de runtime. Estas evidencias no convierten un TRAIN fallido en completado. La selección final, model version final y verificación de carga/linaje de un resultado válido no se acreditan porque no existe completion.

El Run ID mantiene campaign_id y dataset exactos; la solicitud enlaza miembro, revisión y anterior sin reasignar históricos. Lecturas realizadas en procesos/conexiones separados concuerdan. El manifiesto de la intervención previa no presenta diferencias. No se cambió código, dataset, split, configuración ni revisión.

## Conciliación y alcance

36 experimentos: 31 pendientes, 5 fallidos, 0 activos, 0 completados y 0 verificados. Seis intentos totales, los seis fallidos (dos del miembro posición 0 y cuatro de otros miembros). Cero intentos adicionales tras el controlado. Campaña paused; publicación y deployment completos coinciden con la referencia previa. TEST no se leyó en esta intervención; no se ejecutó TRAIN, EVALUATE, EXPLAIN, ensembles ni E9.4. Sólo consultas READ ONLY, lectura/hash de archivos y verificación oficial de ausencia de procesos.

## Acción necesaria antes de otro intento

Mantener pausa y circuito OOM, sin ack-breaker ni reintentos. La ejecución secuencial no evitó este fallo. Antes de autorizar otro intento, obtener evidencia de memoria por fase y retención (carga de datos, fit, predicción interna y serialización) con instrumentación acotada propuesta y revisión técnica explícita, sin repetir un entrenamiento completo para reproducir OOM. Buscar primero un evento de kernel que identifique la víctima; si no está disponible, mantener atribución probable.

La corrección debe respaldarse en esa medición y preservar batch, resolución, precisión, optimizador, semillas y épocas. No hay evidencia suficiente para prescribir ahora una corrección concreta de fuga ni una cantidad garantizada de RAM. Si exige cambio científico o aumento de recursos, presentar requisito y enmienda antes de aplicarlo. No preparar activación de cola como siguiente paso de un intento fallido.

Consultas reproducibles: ver operacion.md. Logs completos permanecen en el volumen operativo; ruta, tamaño y hash registrados en evidencia_final.json. No se imprimieron trazas completas del driver ni credenciales. No se sobrescribieron auditorías anteriores.
