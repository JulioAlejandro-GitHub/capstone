# E9.3 — Instalación operativa de exclusividad y cola secuencial

**INSTALACIÓN VERIFICADA**, 14/09/2026, America/Santiago (evidencias UTC del 15/09). E9.3 sigue EN SEGUIMIENTO: instalar no completa los TRAIN. E9.2 permanece parcial. Campaña `3acf89b7-dc42-4b7a-8e2a-ca6ea024c344`; dataset obligatorio `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`.

Autorización: solicitud adjunta `fe3333c5-c78a-40d3-aa7a-06ac3ed480f2`. Permite respaldo, instalación y registro técnico; no permite activar la campaña ni reservar trabajo. No se usó --resume, no se ejecutó TRAIN científico, EVALUATE, EXPLAIN ni TEST.

## Preflight y revisión

Los 29 archivos del manifiesto preparado coinciden: cero discrepancias. HEAD `1fc5201474bb158a8f84d12b543b255abb1d3d7e`; árbol con cambios preparados conservado. No se modificó código funcional durante la instalación. No se encontró AGENTS.md en repositorio/ancestros inspeccionados. Se leyeron los wrappers de migración/respaldo, migraciones 01/02 y mecanismos de revisión/coordinación. La fuente efectiva del contenedor coincide con la propuesta; el registro distingue esa revisión técnica de la fuente científica original.

Estado inicial: paused, 36 experimentos, 31 pendientes, 5 fallidos, 0 activos/completados/verificados; 5 intentos. Revisión pública 20260912_02; objetivo único 20260914_02. No procesos gestionados ni sesiones activas. Las políticas Compose restart=always relanzan uvicorn, PostgreSQL y frontend, no un coordinador. No hay cron/supervisor en las ubicaciones inspeccionadas ni LaunchAgents/Daemons con referencias al sistema de entrenamiento. No se acredita inexistencia de automatizaciones externas no declaradas; ninguna fue observada y no se reinició servicio alguno.

/ready inicial: HTTP 503, database/storage ready, migrations not_ready. Referencias de publicación y deployment capturadas antes de escribir. Dataset, contrato y matriz exactos en snapshot; cero discrepancias de dataset en los intentos.

## Dos controles excluidos: resolución explícita

- `tests/test_campaign_executor_postgres.py::test_public_e5_revision_readonly`: exige exactamente 20260912_01, tres tablas E5 y train_record_guard habilitado. Ejecutado antes de migrar: FALLA exclusivamente porque obtiene 20260912_02; tablas y trigger correctos. No se contabiliza como aprobado. Requiere opt-in RUN_STAGE5_POSTGRES_TESTS=1 y PostgreSQL. El pin histórico no representa el head actual y no justifica un downgrade.
- `tests/test_assessment_postgres.py::test_public_e6_revision_readonly`: exige exactamente 20260912_02, seis tablas assessment y ocho triggers activos. Ejecutado antes de migrar: APROBADO. Requiere opt-in RUN_STAGE6_POSTGRES_TESTS=1 y PostgreSQL. Tras avanzar a E9.3 su pin también queda histórico; no se volvió a declarar aprobado contra la nueva revisión.

Evidencia alternativa posterior: `integridad_final.json` demuestra la cadena Alembic con E5/E6 como ancestros, tablas conservadas, los ocho triggers E6 y train_record_guard activos, además de guards E9.3 e índices únicos globales válidos. `comparacion_final.json` reúne las aserciones. Así se conserva el control estructural sin relajar las pruebas históricas. La exclusión inicial afectaba pines de revisión, no un fallo pendiente de exclusividad.

## Respaldo e instalación

Se ejecutó `make db-migrate-check`, luego **únicamente `make db-migrate`**. El wrapper generó respaldo custom, comprobó identidad canónica, tamaño no nulo y entradas de esquema/datos/constraints requeridas mediante pg_restore --list. SHA-256 se recalculó desde el archivo y coincide. Ruta, tamaño y digest en `backup.json`; no se realizó restauración y no se afirma restaurabilidad probada.

Migraciones aplicadas, en orden: `20260912_02 → 20260914_01 → 20260914_02`. Preflight transaccional llegó a 02, hizo rollback y confirmó desde otra conexión que persistía 20260912_02; después se instaló y verificó head 20260914_02. Registro completo en `instalacion_wrapper.txt`.

01 añade campaign_id nullable con FK, registro técnico e intento controlado; 02 añade gate/eventos, reserva con propietario y lock, índices parciales globales y vínculo de revisión. No hay backfill, eliminación ni DML correctivo sobre históricos; sólo se inicializa el singleton nuevo. Se reemplaza campaign_attempt_guard conforme al SQL preparado. ALTER TABLE y creación de índices requieren locks: se ejecutaron sin trabajos activos y finalizaron correctamente. No se aplicaron revisiones ajenas, DDL manual, downgrade ni stamp. No fue necesario recargar o reiniciar servicios.

## Revisión técnica persistida

UUID **`3ec6fa57-be3f-5433-8557-8c12c3eea740`**, asociado a la campaña autorizada. `revision_autorizada.json` conserva entorno original, hash contractual, archivos y pruebas preparados; actualiza exclusivamente la autorización documental de instalación/registro. No autoriza ejecución. La propuesta anterior permanece intacta.

Registro mediante `src.malaria_dl.execution.controlled register`, repetido con igual UUID/payload para verificar idempotencia. `revision_readback.json` confirma payload idéntico, una fila recuperada desde otro proceso/conexión y ninguna fila en controlled_requests, train_execution_revisions o execution_events públicos. Los parámetros del miembro fallido sirven al validador oficial de registro: no atribuyen la revisión al intento anterior ni crean uno nuevo. La matriz, configuración, entorno original y todo historial de intentos siguen iguales al snapshot inicial.

## Verificación posterior y dry-run

38 pruebas PostgreSQL aisladas aprobadas en 18.90 s: global execution + controlled train. Usan esquemas/UUID sintéticos, incluyendo procesos técnicos desechables; no la campaña real. La exclusividad se acredita con esas pruebas de concurrencia y con guards/índices instalados, no con la mera ausencia actual de procesos. Cero esquemas sintéticos remanentes. Las 128 pruebas del desarrollo siguen siendo antecedente, no fueron reejecutadas como conjunto.

Dry-run oficial: `execution_ready=true`, revision_registered=true, global installed/available=true, active_records=0, writes=0, reservations=0, campaign_state=paused, memory_optimization_required=false. Próximo miembro explícitamente verificado: `e1ceb448-195a-4b80-9c96-a4e67734e16a`, posición 5, CustomCNN / Adam / semilla 47. El campo expresa preparación técnica observada; no elimina la pausa ni autoriza lanzamiento. La selección de cola es determinística; se confirmó pertenencia de ese ID por SQL. El resultado completo se conserva en `dry_run.json`.

El preflight E1 de contenido sellado sigue siendo obligatorio antes de una futura reserva; el dry-run verifica el contrato congelado, no sustituye la comprobación integral de archivos. La instalación no necesita leer TEST ni lanzar diagnósticos reales. No se regeneraron manifiestos, splits o hashes científicos.

## Estado final y límites

/ready HTTP 200, database/migrations/storage ready. Campaña aún pausada: 31 pendientes, 5 fallidos, 0 activos/completados/verificados; 5 intentos, cero nuevos. Cero procesos gestionados observados; no se mantuvo un coordinador ni se adquirió el gate público para probarlo. 97 corridas históricas conservan campaign_id NULL; cero referencias de campaña huérfanas. Huellas y conteos de runs (excluyendo la nueva columna), run_lineage, model_versions, publicaciones, deployments y campaign_attempts idénticos antes/después. Publicación y deployment completos también coinciden.

No hay bloqueo material de instalación. Los cinco OOM históricos siguen sin resolución demostrada; el contador observado permanece en 5. El margen de recursos no garantiza que todas las arquitecturas quepan. Pausa ante incremento OOM, recursos insuficientes o fallos consecutivos sigue activa en el código instalado. El contrato Linux/Compose y la prueba conservadora de fin de procesos siguen aplicando; una pérdida de evidencia requiere recuperación auditada, nunca un desbloqueo por expiración.

La siguiente acción es obtener autorización de activación futura, volver a comprobar pausa/procesos/recursos/revisión/dataset y usar el procedimiento de `operacion.md`. **Finalizado sin activar campaña, abrir TEST ni iniciar E9.4.**

Incidencias sólo en scripts de auditoría: se corrigió la ruta explícita de Alembic, la lectura del miembro mediante consulta y un filtro incompleto del inventario de triggers. Todas fueron lecturas fallidas, sin modificar base ni código funcional. Los resultados finales completos son los conservados.
