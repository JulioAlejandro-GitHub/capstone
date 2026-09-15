# E9.3 — Único intento controlado

**EN EJECUCIÓN**, observación al 14/09/2026 22:12:40 America/Santiago. No se declara completado ni verificado. E9.3 y E9 no aprobadas; E9.2 sigue parcial.

## Autorización y preflight

Solicitud `f84cc89d-9038-44db-a2f7-48bb1a1d5b21`: exactamente un intento desde cero, campaña pausada y sin habilitar la cola. Campaña `3acf89b7-dc42-4b7a-8e2a-ca6ea024c344`, dataset obligatorio `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`, revisión técnica `3ec6fa57-be3f-5433-8557-8c12c3eea740`.

Se leyeron instrucciones y auditoría/manifiesto/procedimiento de instalación. No se encontró AGENTS.md en los ancestros inspeccionados. HEAD actual `144da5cbd6ce34647a3e109daa3542af75c0606c`, árbol inicialmente limpio. El commit cambió desde la instalación, pero todos los archivos del manifiesto y hashes de fuente registrados coinciden. No se editó código funcional ni configuración científica. El entorno efectivo y el persistido en la sesión coinciden con la revisión autorizada.

Inicialmente: migración 20260914_02, /ready HTTP 200 en todos los componentes, campaña paused, 31 pendientes y 5 fallidos, 5 intentos, cero procesos/sesiones gestionados activos. Global gate disponible. Aproximadamente 6,5 GiB de RAM disponibles y 835241608 KiB libres en el filesystem de artefactos. OOM kill inicial=5. Disponibilidad observada no garantiza que el entrenamiento quepa.

Dry-run oficial controlado: execution_ready=true, revisión registrada, ordinal siguiente 2, writes=0. Antes de reservar, execute_one aplica el preflight E1 y coteja dataset sellado, snapshot, configuración y revisión. La reserva posterior confirma que esa ruta no falló. No se sustituyeron datos mediante fixtures ni se regeneró split. La validación interna de TRAIN es la del protocolo; no se lanzó EVALUATE ni se abrió TEST.

## Selección y reserva

El miembro posición 5 del dry-run de cola general estaba pendiente, sin intento fallido previo: no satisface el contrato de ejecución controlada instalada. Se utilizó el miembro explícito del procedimiento controlled y primer fallido en orden canónico, sin seleccionar por rendimiento:

- Experimento `2fbd5862-b68b-4845-9445-a30d7ec61382`, posición 0, CustomCNN, Adadelta, semilla 11.
- Configuración hash `9caaac5ec278e315c7af400729920b93e348af752ae24eedff40cb72893bb2b0`; payload congelado conservado en seleccion.json.
- Intento previo `8279db36-7bfe-4e22-8bf3-872ac215eae2`, run `a5f36df1-3341-43fd-94b9-ee1cedb834c5`, causa original CHILD_EXIT_OR_INCOMPLETE_RESULTS. Atribución individual a OOM no demostrada; no se inventa el código de salida perdido.
- Solicitud idempotente `7d4cacb1-3d85-53f6-9828-8a7b1e0164c5`, conservada antes del lanzamiento.
- Nuevo intento ordinal 2: `4cd0cf3f-37df-4490-9f26-eb2763f3b4e6`.
- Nuevo Run ID `79f39931-ac71-4bc1-a317-149a975d1f74`.

Se invocó exactamente una vez controlled execute mediante Compose exec desacoplado, sin --resume. No se lanzó un worker manual ni otro coordinador. La reserva atómica vinculó campaña, miembro, revisión e intento anterior. Se parte desde cero; los cuatro checkpoints parciales antiguos permanecen intactos.

## Seguimiento observado

Ejecutor controlado PID 42342, worker TRAIN PID 42346. Son padre e hijo del mismo experimento, no dos entrenamientos. No aparecen otros procesos TRAIN gestionados. La evidencia incluye identidad PID/inicio/sesión y gate oficial.

01:10:00 UTC: lote 17/347, RSS worker 2514010112 bytes; 01:11:13: lote 56/347, RSS 4069691392 bytes. En ese intervalo de 73,6 s, CPU worker 1003,9% (100%=un núcleo), contenedor 1006,6%. 01:12:40: lote 97/347, RSS worker 4318326784 bytes (4,02 GiB); contenedor 5003014144 bytes (4,66 GiB), RAM disponible 3271880704 bytes. El contador oom_kill sigue en 5. cgroup memory.max=max, no significa RAM física ilimitada; valores de swap/cpu están en observaciones.

Hay progreso real en log y consumo de CPU, no sólo estado de BD. Todavía no termina la primera época: sólo registro runtime persistido, sin épocas ni checkpoint nuevo finalizado. No se calcula hash definitivo de archivos en escritura. Código de salida, selección final, model version y verificación completa permanecen pendientes.

## Estado al dejar el seguimiento

36 experimentos: 31 pendientes, 1 activo, 4 fallidos, 0 completados y 0 verificados. 6 intentos totales: cinco fallidos históricos y un nuevo activo. Campaña paused. No se asignó ningún experimento posterior. Publicación y deployment coinciden con referencia inicial. No se ejecutó TRAIN adicional, EVALUATE, EXPLAIN, ensembles, calibración, threshold ni E9.4.

La memoria creció durante el primer tramo; no se afirma que secuencialidad resuelva los OOM. El último tramo no demuestra estabilidad de todo el entrenamiento. No se redujeron batch, resolución, precisión, épocas u otros parámetros. No se ejecutaron nuevas pruebas sintéticas: la implementación no cambió y sus pruebas son antecedentes, no resultados nuevos de esta intervención.

El proceso continúa desacoplado de la terminal mediante el mecanismo oficial, que espera al único worker, conserva salida, verifica artefactos si termina correctamente y sale sin avanzar la campaña. No hay monitor autónomo añadido ni promesa de seguimiento fuera de esta sesión. `operacion.md` contiene las consultas para retomarlo. No repetir el lanzamiento; consultar por la misma solicitud. Si falla, preservar evidencia y no reintentar sin autorización posterior.

**Recomendación:** dejar terminar este único intento con sus controles instalados. Antes de decidir continuación, revisar salida/recursos, checkpoint/linaje, lectura desde otra conexión y ausencia de procesos hijos. No declarar éxito por un checkpoint parcial ni desbloquear un gate con evidencia incierta. La siguiente campaña/cola necesita nueva autorización.
