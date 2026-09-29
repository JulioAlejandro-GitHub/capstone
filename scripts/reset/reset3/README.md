# RESET.3 — reconstrucción ejecutada

La ejecución definitiva del 28-09-2026 está documentada en `docs/engineering/e10_execution_refactor/reset_3_clean_rebuild.md`. La base canónica es E10, conserva **todas** las filas/columnas de autenticación y las 13 tablas de dataset/split, y tiene vacío el historial restante. No se ejecutó TRAIN/TEST.

Estos scripts son evidencia de una operación específica, con identidades y nombres cerrados; no son comandos de limpieza repetible. No volver a ejecutarlos sobre un sistema que ya recibió datos nuevos.

- `bootstrap_probe.py`: DDL legacy original excepto el seed 004 de ejemplos; ledger con checksum y Alembic oficial hasta 20260922_01, exclusivamente en un clon distinto del cluster operativo.
- `import_probe.py`: origen READ ONLY; COPY íntegro de las familias protegidas, incluyendo `last_login_at` y las 55.116 imágenes de split. Preserva IDs de roles oficiales y tres definiciones técnicas de arquitectura. Importa la versión temporalmente DRAFT y usa sus transiciones oficiales hasta su estado original FROZEN; compara el contenido final completo. No recalcula el split ni deshabilita guards.
- `verify_restore.py`: compara todas las tablas public y nueve schemas históricos de la restauración completa; normaliza solamente OID/nombres RI internos regenerados y casts de arrays literales equivalentes observados en pg_restore.
- `functional_probe.py`: OP1 Docker/Local antes de claim, registry, ResultService sin eventos, GlobalGate, 208 FK y ausencia de historial. El sufijo histórico LOGIN_PENDING se refiere al login con contraseña; la autenticación JWT se acredita separadamente.
- `api_probe.py`: GET HTTP reales y autenticados contra candidato/operativo, JWT firmado por la implementación oficial, usuario/permisos, health/readiness, dataset/split y deployments. No conoce la contraseña, no ejecuta `/auth/login`, no modifica `last_login_at`.
- `candidate_snapshot.py`, `verify_operational.py`: fingerprints de las 97 tablas, 16 tablas protegidas exactas, 77 tablas de historial vacías, E10 y guards antes/después del cambio y después del reinicio.
- `artifact_plan.py`, `artifact_quarantine.py`: inventario cerrado de raíces derivadas; copia completa verificada antes de retirar fuentes, journal persistente, verificación y restauración explícita con detección de conflictos. Dataset/configuración/fuentes originales quedan fuera de esas raíces.
- `rename_rehearsal.py`: commit y rollback reales de renombrado transaccional, sólo en dos bases vacías desechables del clon.
- `cutover.py`: nueva comprobación completa del origen, ausencia de conexiones y cambio transaccional de nombres, conservando la base anterior. Reconciliación de COMMIT mediante una conexión nueva y OID, sin asumir rollback por pérdida de respuesta.
- `validate_login.py`: validador manual del prototipo anterior; no se ejecutó. No es necesario ni apropiado ejecutarlo con su configuración temporal obsoleta.
- `freeze_backup_window.py`: propuesta anterior bloqueada por barrera incondicional; **no se utilizó**. La ejecución definitiva empleó parada normal de Docker Compose y cierre normal de DBeaver, autorizados en el nuevo RESET.3.

Los scripts requieren la imagen Python Docker instalada y configuración privada 0600; no ejecutar Python SQL contra PostgreSQL desde el host. `common.py` y el manifiesto de FK proceden de RESET.1B. Los orquestadores y evidencias exactos de esta ejecución se conservan en `backups/reset3_final/evidence`, junto con hashes; no contienen las credenciales temporales. El backup íntegro, la cuarentena y la base anterior deben conservarse mientras se mantenga la ventana de recuperación.
