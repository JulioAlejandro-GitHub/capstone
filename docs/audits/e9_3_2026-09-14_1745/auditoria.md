# E9.3 — Seguimiento operativo del 14/09/2026, 17:49 America/Santiago

**EN SEGUIMIENTO; no aprobada.** 36 experimentos: 31 pendientes, 1 activo, 4 fallidos, 0 completados y 0 verificados. Cinco intentos, todos ordinal 1; cero reintentos adicionales. E9.2 sigue PARCIAL por la enmienda ponderada. No se inició E9.4 ni se abrió TEST.

Snapshot inicial: 2026-09-14 20:45:02.292161+00:00; final: 2026-09-14 20:49:58.374133+00:00 (UTC; restar tres horas para America/Santiago). PostgreSQL se consultó en transacciones explícitas READ ONLY. Los archivos JSON son evidencia de auditoría, no fallback de resultados ni autoridad alternativa a PostgreSQL.

## Revisión y alcance

HEAD inicial 59c980521183ac2d00c167868b8abba76fbc1470, árbol inicialmente limpio. Fuente efectiva d8569d8faaa80eca42b130e6096203d851e2c663b4cdb8cd599dda950fbe6430, idéntica al contrato. Docker carece de Git: no se reemplazó su git_commit null por el HEAD host. Base malaria_experiments/public, Alembic 20260912_02, readiness database/migrations/storage ready. Se conservaron las auditorías anteriores. No se encontró AGENTS.md en la búsqueda del repositorio; las búsquedas de ancestros constan en E9.1. Referencias: operación E9, plan E9.1, auditorías E9.1/E9.2/E9.3, protocolos E7/E8 y decisión posterior del usuario.

Se revisaron execution/campaign.py, execution/train.py, execution/repository.py, execution/artifacts.py, data/loaders.py y evaluation/clinical_metrics.py. El bucle ejecuta exclusivamente TRAIN, verifica el checkpoint y termina; no encadena EVALUATE/EXPLAIN. Las doce configuraciones congeladas mantienen calibrate_threshold=false y evaluate_best_on_test=false. La validación interna usa VAL a 0,5. No se modificó la meta científica ni se seleccionaron resultados.

## Inventario de los 36 experimentos

| Posición | Miembro | Arquitectura | Optimizador | Semilla | Estado | Intentos |
|---:|---|---|---|---:|---|---:|
| 0 | 2fbd5862-b68b-4845-9445-a30d7ec61382 | custom_cnn | adadelta | 11 | failed | 1 |
| 1 | 48f036da-ad4e-47e1-af82-c1624ee042d6 | custom_cnn | adadelta | 29 | failed | 1 |
| 2 | ae6cc2bb-c48d-4c76-b9c5-90502afac7fe | custom_cnn | adadelta | 47 | failed | 1 |
| 3 | effa8851-52ce-419f-8c72-59aa8ac739f4 | custom_cnn | adam | 11 | failed | 1 |
| 4 | 6be69e51-c956-4a2a-97b8-0293e4780dbe | custom_cnn | adam | 29 | active | 1 |
| 5 | e1ceb448-195a-4b80-9c96-a4e67734e16a | custom_cnn | adam | 47 | pending | 0 |
| 6 | da652973-fb5c-4cfe-92a7-393c92010bff | custom_cnn | adamw | 11 | pending | 0 |
| 7 | 481c1b88-83d2-40c0-9209-c10c226d36f4 | custom_cnn | adamw | 29 | pending | 0 |
| 8 | 46bcb7fa-ee2f-457f-95fa-3d71c5d1de92 | custom_cnn | adamw | 47 | pending | 0 |
| 9 | 332d0f6d-cd5c-46a4-be01-e1b9aab6c116 | custom_cnn | sgd | 11 | pending | 0 |
| 10 | 2adccda7-a9ee-40f7-8704-67a202e0a80c | custom_cnn | sgd | 29 | pending | 0 |
| 11 | 111f7197-e4f7-49bb-a5da-58cd1461cbd2 | custom_cnn | sgd | 47 | pending | 0 |
| 12 | 555d58d4-4821-4cb6-b43a-1d9f66e36c6c | densenet121 | adadelta | 11 | pending | 0 |
| 13 | 3898b92d-f3d7-4863-93b2-4fb054c542b7 | densenet121 | adadelta | 29 | pending | 0 |
| 14 | 305c153b-821d-4c31-a6aa-cc4c0bd1ec94 | densenet121 | adadelta | 47 | pending | 0 |
| 15 | cfe368f3-3adc-4def-b893-0ac23cfd4c82 | densenet121 | adam | 11 | pending | 0 |
| 16 | b0ffb6fe-53e2-4420-9759-870eb8e2fa77 | densenet121 | adam | 29 | pending | 0 |
| 17 | 1587e852-dff5-4c64-a6e2-c57f86457d33 | densenet121 | adam | 47 | pending | 0 |
| 18 | 0cd9cfc3-d5f4-44aa-9036-b9f7c549fba6 | densenet121 | adamw | 11 | pending | 0 |
| 19 | 6ef48d0e-40df-496b-a19b-da45ea19a7f4 | densenet121 | adamw | 29 | pending | 0 |
| 20 | a591fbc3-bd32-421b-bb2f-b3dc5217e99c | densenet121 | adamw | 47 | pending | 0 |
| 21 | 1799d954-1042-4096-8208-c18e6ba5f06c | densenet121 | sgd | 11 | pending | 0 |
| 22 | ac84826f-0d5b-48f3-a511-192ac4e1da50 | densenet121 | sgd | 29 | pending | 0 |
| 23 | 1477c7f5-884d-45ad-8ac5-ca694125eb41 | densenet121 | sgd | 47 | pending | 0 |
| 24 | cda79eea-7313-44b9-9a20-07188f6cf603 | vgg16 | adadelta | 11 | pending | 0 |
| 25 | 33921d5b-53f5-4899-8246-0efae7573f82 | vgg16 | adadelta | 29 | pending | 0 |
| 26 | e6d0d9a6-96cc-43bd-a0fe-c50a285febc6 | vgg16 | adadelta | 47 | pending | 0 |
| 27 | 2e5bada2-a3df-41ef-ad0f-724f22ae2f38 | vgg16 | adam | 11 | pending | 0 |
| 28 | af6c53e1-fd81-4b6e-bc33-a218f3419b46 | vgg16 | adam | 29 | pending | 0 |
| 29 | c4741856-79f8-414a-9262-f632ef578b73 | vgg16 | adam | 47 | pending | 0 |
| 30 | 3021aa82-713d-4c67-a37a-f127623e6c4f | vgg16 | adamw | 11 | pending | 0 |
| 31 | eb8ba6dc-00bf-4f4d-8b9c-9d1665019ccc | vgg16 | adamw | 29 | pending | 0 |
| 32 | 3ce3b53d-6f24-4976-9c75-09674d581325 | vgg16 | adamw | 47 | pending | 0 |
| 33 | 4905eb35-085c-4fbc-870d-f23b149e167d | vgg16 | sgd | 11 | pending | 0 |
| 34 | 9bf0572c-ff6c-42f7-9cad-88de4339c65d | vgg16 | sgd | 29 | pending | 0 |
| 35 | 229d6d38-1ce5-406f-b99c-46dc1d9e6ae8 | vgg16 | sgd | 47 | pending | 0 |

## Intentos y fallos

| Run ID | Estado | Inicio UTC | Fin UTC | Épocas persistidas | Último registro UTC |
|---|---|---|---|---:|---|
| a5f36df1-3341-43fd-94b9-ee1cedb834c5 | failed | 2026-09-14 11:47:21.974005+00:00 | 2026-09-14 13:01:39.655583+00:00 | 4 | 2026-09-14 13:00:45.793650+00:00 |
| 8ebbd308-2cec-4275-93b7-ad56fa9e6931 | failed | 2026-09-14 13:01:49.711679+00:00 | 2026-09-14 14:13:10.465508+00:00 | 6 | 2026-09-14 14:12:17.981762+00:00 |
| 3894deef-252f-424e-a4ad-d6cd555e063e | failed | 2026-09-14 14:13:20.562758+00:00 | 2026-09-14 15:27:23.159006+00:00 | 7 | 2026-09-14 15:21:36.192960+00:00 |
| 61bf6d6d-9db9-498e-a9ee-c26e94e46f2d | failed | 2026-09-14 15:27:33.378611+00:00 | 2026-09-14 16:57:05.141240+00:00 | 9 | 2026-09-14 16:56:04.755766+00:00 |
| ec0975b2-b355-4d5c-a4ec-beac31da72dd | active | 2026-09-14 16:57:15.417610+00:00 | None | 3 | 2026-09-14 18:27:11.831526+00:00 |

Los cuatro fallidos conservan CHILD_EXIT_OR_INCOMPLETE_RESULTS, sin phase/completion ni versión final acreditada. No se retuvo el código de salida individual: no puede reconstruirse ni afirmarse exit 137. No se descartan semillas.

RAM: oom_kill=4 a las 20:49:35 UTC, frente a 3 en la evidencia previa de las 16:41 UTC. Una muerte OOM adicional coincide con un nuevo fallo entre snapshots; la atribución al Run 61bf6d6d sigue siendo PROBABLE, no confirmada, porque faltan PID víctima y timestamp del evento. Los otros tres fallos también mantienen RAM como causa probable, con atribución individual no determinada. No hay evidencia de OOM GPU. VM MemTotal 8125656 kB; 16 CPU; memory.max=max no equivale a RAM ilimitada. Worker observado con VmHWM 6718980 kB y swap 592352 kB; cgroup swap 812257280 bytes. No se cambió memoria ni servicios.

Datos, serialización, almacenamiento y código: no se ha demostrado una causa fatal concreta en estos cuatro intentos. Los registros parciales y sus bytes válidos no prueban que toda la ejecución haya sido correcta. Coordinación: está confirmado el defecto de diagnóstico que agrupa salidas no cero e incompletitud bajo una sola causa. Su parche preparado anterior conserva exit code, pero NO está aplicado y NO corrige por sí mismo OOM.

La ruta activa realiza model.predict por lote en collect_predictions, además de validación clínica y persistencia VAL por época, y usa map/prefetch AUTOTUNE. Son candidatos a instrumentar; no se afirma una fuga ni se modifica concurrencia sin comprobar orden y reproducibilidad. No se provocó un OOM de prueba.

## Actividad y verificación

Coordinador PID3475 y worker PID96740 conservan start_ticks 20672733/22533557. Entre 20:45:02 y20:49:58 el worker aumenta utime 2315565→2504856 y stime 1063979→1143777. Argumentos y Run ID corresponden a ec0975b2-b355-4d5c-a4ec-beac31da72dd, CustomCNN/Adam/29. Actividad confirmada aunque el último registro de época sea anterior. No existe heartbeat temporizado; no se interpretó updated_at antiguo como muerte. No se lanzó ni reanudó otro coordinador.

26/26 checkpoints de los cuatro intentos terminales coinciden en tamaño y SHA-256 con PostgreSQL, mediante file_identity oficial. Se verificaron pertenencia de ruta y Run ID. No se cargaron modelos ni se calcularon métricas; ningún checkpoint parcial convierte un TRAIN fallido en completado/verificado. Los archivos del worker activo se dejaron sin hash definitivo. Historial, configuración/dataset/environment y asociación miembro-intento coinciden en las cinco sesiones; unmatched_attempts vacío. La lectura final se hizo desde otra conexión.

Para todos los TRAIN siguen pendientes: terminación válida, fase completa, época/criterio final, versión y checkpoint final, carga segura, verificación integral de linaje final y recuperación de esa finalización desde otra conexión. No se afirma durabilidad de resultados que aún no existen.

## Correcciones y límite seguro

No se activó código funcional: sólo se añadió el diagnóstico de lectura y esta evidencia. No se ejecutaron nuevamente tests históricos ni pruebas con escritura; el script diagnóstico se ejecutó realmente en Compose y sus 26 comparaciones pasaron. El parche de diagnóstico anterior está en ../e9_3_diagnostico_2026-09-14/retener_exit_code.patch; sus pruebas anteriores son antecedentes, no pruebas repetidas hoy.

Procedimiento preparado: (1) antes de aplicar fuente, usar ExecutionRepository.pause(campaign_id, código de incidencia) para impedir el siguiente claim, sin señales al TRAIN; (2) esperar finalización del hijo y salida del padre, comprobando PIDs/identidad; (3) preservar artefactos y diagnóstico; (4) validar corrección con entradas sintéticas y pruebas afectadas en Compose; (5) establecer una transición explícita de revisión compatible con la campaña, conservando contrato y environment original y registrando revisión por intento; (6) sólo entonces recuperar mediante ruta oficial. Este procedimiento NO se ejecutó.

Bloqueo de activación: preflight exige igualdad estricta de source_sha256 antes de cada claim y worker. No existe transición de revisión implementada para la misma campaña; la ruta actual exige una sucesora, prohibida en esta tarea. No se falseará el hash ni se editará el contrato. Cualquier procedimiento nuevo requiere diseño y validación de integridad antes de activarse; no es una autorización para reiniciar ahora.

El coordinador admite máximo tres intentos y prioriza los 31 pendientes. No tiene bloqueo por miembro para omitir fallos repetidos. Antes de entrar en reintentos sin corrección debe detenerse en un límite seguro mediante pause; no se ha instalado un monitor automático ni se promete vigilancia fuera de esta sesión. No existe continuación exacta desde pesos parciales acreditada; un futuro intento sería desde inicio salvo verificación de todo el estado requerido.

## Campaña, publicación y límites

La asociación actual se crea atómicamente por session→attempt→member→campaign con ID explícito y FK; no existe runs.campaign_id literal en esta revisión. No se declaró implementada la propuesta de columna nullable ni se hizo migración/backfill. Los cinco intentos pertenecen a los miembros explícitos de esta campaña. No se tocaron históricos sin campaña ni su linaje. La revisión general de huérfanos/históricos de docs/engineering/campaign_scope_2026-09-14 es antecedente; hoy se verificó la pertenencia de los intentos inspeccionados, no se repitió una auditoría completa de todas las tablas.

Publicación inicial/final idéntica: 81d69942-17eb-4999-a6bd-2b05779a65a4; deployment cf2f20d3-a1e0-499c-b5ab-501b7c1ae198; model_version 172b7031-9f79-44e3-a7ad-2dc10a9ffd08. No se cambió deployment ni publicación. Cero assessments y final locks en los snapshots; no se cargó TEST. E9.2 parcial y E9 no aprobada. ARTIFACTS_ROOT sin volumen dedicado sigue siendo limitación de supervivencia a reemplazo del contenedor; no se reinició.

## Comandos reproducibles

Desde la raíz del repositorio, sólo lectura:

```sh
docker compose exec -T -w /app/malaria_dl_local_project -e PYTHONDONTWRITEBYTECODE=1 backend python -B run_train_all_models.py --campaign-id 3acf89b7-dc42-4b7a-8e2a-ca6ea024c344 --inspect
docker compose exec -T -w /app/malaria_dl_local_project -e PYTHONDONTWRITEBYTECODE=1 backend python -B - < docs/audits/etapa_9_1_consulta_2026-09-14.py
docker compose exec -T -w /app/malaria_dl_local_project -e PYTHONDONTWRITEBYTECODE=1 backend python -B - < docs/audits/e9_3_2026-09-14_1745/diagnostico.py
```

Recuperación condicionada: docs/science/plan_reanudacion_e9_1_2026-09-14.md contiene el comando --resume. No ejecutarlo con el propietario activo ni como reintento ciego ante el mismo fallo. Próxima acción: observar la terminación del TRAIN actual, verificar íntegramente si completa y resolver la corrección/procedencia antes de repetir fallidos. Esta entrega es un punto de seguimiento, no cierre de E9.3.
