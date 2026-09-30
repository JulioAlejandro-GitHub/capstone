# E10.10.5E.1 — resolución ACL E-01 y nuevo bloqueo E-02

**E-01 RESUELTA Y BASELINE RECERTIFICADA EN AISLAMIENTO. E INCOMPLETA, BLOQUEADA POR E-02. GATE E NO SOLICITADO.**

## Alcance y autorización

E-01 fue aprobada explícitamente. Se añadió exclusivamente `GRANT SELECT ON TABLE public.alembic_version TO capstone_v2_runtime` después del `REVOKE ALL` existente. No se concedieron otros permisos, no se incorporó SECURITY DEFINER y ningún productor usa el migrador como runtime. El compilador, manifiesto, validador estático, prueba ACL, referencia de catálogo de adopción y hashes del contrato runtime quedaron actualizados. El verificador de restore reproduce la nueva ACL.

La [diferencia completa con D.4](e10_10_5e1_evidence/route_a/d4_catalog_delta.json) contiene solamente la ACL de `alembic_version` y su privilegio SELECT efectivo. Los restantes recursos SQL son idénticos. D-01 a D-06 no cambiaron. [D.4](e10_10_5d4_evidence/route_a/certificate.json) permanece como certificado histórico anterior a E-01; [preservación byte a byte contra Git HEAD](e10_10_5e1_evidence/d4_preservation.json). El validador verifica también los 54 archivos históricos originales.

## Certificado y hashes

[Certificado E.1](e10_10_5e1_evidence/route_a/certificate.json), limitado a baseline/ACL; no acredita integración E ni Route B nueva.

- Manifiesto SHA-256: `f5478ce2802af7bb4ee063edf4934bb5b9adf8f37e814264d7afa979fa01f25f`.
- Catálogo SHA-256: `71e650852595bcc01bf5de547d8cc5eed32e75aee95ac6667dd89c3b6b713238`.
- El hash del catálogo usa `sha256(json.dumps(snapshot, sort_keys=True, default=str).encode())`, igual que D.4.
- Identidad, puerto 55492, volumen exclusivo y system identifier: [target](e10_10_5e1_evidence/route_a/target.json). PostgreSQL `170009` verificado; instancia nueva sin reutilizar volumen E o D.4.

## Pruebas reales

| Comprobación | Resultado y evidencia |
|---|---|
| Alembic desde cero | Passed; [comandos](e10_10_5e1_evidence/route_a/commands.jsonl) |
| Catálogo completo, ownership, ACL | Instalado = renderizado PostgreSQL 17.9; única diferencia D.4: SELECT runtime |
| Constraints y privilegios baseline | 46 casos server, 45 D-03, 5 D-05; todos passed |
| Rollback de instalación | Fallo inyectado deja catálogo vacío y sin head |
| Idempotencia | Catálogo y fila de versión sin cambios |
| Backup/restore | Catálogos, datos de 103 tablas y secuencia iguales; ACL E-01 conservada |
| SELECT runtime | `session_user=current_user=capstone_v2_runtime`; head reconocido |
| INSERT/UPDATE/DELETE/TRUNCATE/ALTER/DROP de versión | Todos rechazados con SQLSTATE 42501 |
| PUBLIC | Sin entrada ACL sobre versión; catálogo restante idéntico a D.4 |
| Alembic stamp | CLI rechazada por identidad runtime; escritor real de Alembic sobre conexión runtime autenticada rechazado con 42501 |
| Alembic upgrade | CLI con URL runtime rechazada por `V2_AUTHORIZATION_MISMATCH` antes de conexión; no se debilita la guarda para forzar DDL |
| Revisión desconocida, vacía, múltiple | Rechazadas; ResultService tampoco emite DML antes del rechazo |
| Error SQL de inspección | Rechazado como `schema_inspection_failed`; sin fallback |
| Legacy | `20260922_01` reconocido con login runtime real en schema desechable y migraciones legacy reales; padres sintéticos, no certificación de baseline legacy completa |

[ACL, identidad y guarda](e10_10_5e1_evidence/route_a/runtime_acl_revision.json) · [Legacy](e10_10_5e1_evidence/route_a/legacy_revision.json) · [Restore](e10_10_5e1_evidence/route_a/restore_result.json) · [Rollback](e10_10_5e1_evidence/route_a/rollback_result.json).

Las conexiones de preparación alteran exclusivamente fixtures/revisiones del cluster atestado; las lecturas y operaciones que acreditan runtime se autentican realmente como runtime, sin SET ROLE. La CLI Alembic se rechaza antes de autenticarse por diseño: se informa por separado del ensayo SQL y del escritor stamp autenticados.

## Continuidad de E y E-02

Tras recertificar y pasar el preflight se invocó ResultService/PostgresResultRepository contra el runtime real. Se aceptó un evento de época, se reconoció su duplicado, se rechazó un owner distinto y se rechazó la evaluación sin procedencia, revirtiendo su append.

Para aislar la siguiente incompatibilidad se suministró **procedencia sintética explícita de fixture**. Esto no acredita producción ni sellado desde TRAIN. La evaluación final insertó su proyección dentro de la transacción, pero la actualización JSONB posterior falló:

```sql
ALTER TABLE public.runs ADD CONSTRAINT ck_v2_no_result_json
CHECK (NOT parameters ? 'training_results');
```

El adaptador preparado en E escribe `runs.parameters.training_results`. PostgreSQL devolvió **23514 / ck_v2_no_result_json**. El requisito de proyectar ledger + ese JSONB + métricas tipadas contradice esta restricción de la baseline aprobada. La autorización E-01 sólo permite cambiar lectura de versión.

[Evidencia E-02 y rollback](e10_10_5e1_evidence/route_a/e10_projection.json): ledger=1 (época previa), evaluations=0, metrics=0, JSONB training_results ausente. No se devolvió ACCEPTED para la evaluación, no se dejó proyección parcial y no se modificaron bytes/hashes de eventos históricos. El probe termina con código 2 para evitar confundir diagnóstico reproducido con integración aprobada.

**Se detuvo E conforme al apartado 9 de la instrucción del usuario.** No se eliminó ni relajó `ck_v2_no_result_json`. No se cambió silenciosamente el destino JSONB.

## Decisión E-02 requerida

Recomendación para revisión: conservar la baseline y hacer explícito que, en v2, el JSONB de evidencia es `train_execution_records.payload.canonical_event`; resultados consultables en `evaluations`/`run_clinical_metrics`, sin duplicar `runs.parameters.training_results`. Legacy mantendría su proyección actual. Requiere confirmar esa interpretación del requisito ledger + JSONB + métricas y adaptar lectores/DTOs sin fallback científico.

Alternativa: exigir también `runs.parameters.training_results` en v2. Requeriría autorización adicional para modificar `ck_v2_no_result_json`, revisar el contrato de fuente de verdad y recertificar nuevamente; excede E-01. Ninguna alternativa fue implementada.

## Reproducción y limitaciones

Los scripts de recertificación y probes leen sólo descriptores aislados explícitos, nunca configuración operativa. Credenciales en archivos privados fuera del repositorio, rutas sin secretos en `private_paths.json`. Para una repetición desde cero usar otro directorio de evidencia y puerto libre; `setup` rechaza sobrescribir un target existente. No borrar ni reutilizar evidencia certificada.

```sh
PYTHONPATH=/private/tmp/e10_10_5d_parser312 /private/tmp/e10e-venv/bin/python scripts/db/build_v2_baseline.py --check
/private/tmp/e10e-venv/bin/python scripts/db/recertify_v2_e1.py setup
/private/tmp/e10e-venv/bin/python scripts/db/recertify_v2_e1.py preflight
/private/tmp/e10e-venv/bin/python scripts/db/recertify_v2_e1.py upgrade
/private/tmp/e10e-venv/bin/python scripts/db/recertify_v2_e1.py catalog
/private/tmp/e10e-venv/bin/python scripts/db/recertify_v2_e1.py server
/private/tmp/e10e-venv/bin/python scripts/db/recertify_v2_e1.py d05
/private/tmp/e10e-venv/bin/python scripts/db/recertify_v2_e1.py d03
/private/tmp/e10e-venv/bin/python scripts/db/recertify_v2_e1.py rollback
/private/tmp/e10e-venv/bin/python scripts/db/recertify_v2_e1.py idempotence
/private/tmp/e10e-venv/bin/python scripts/db/recertify_v2_e1.py backup_restore
/private/tmp/e10e-venv/bin/python scripts/db/probe_v2_e1_runtime.py
malaria_dl_local_project/.venv/bin/python scripts/db/probe_v2_e1_legacy.py
malaria_dl_local_project/.venv/bin/python scripts/db/probe_v2_e1_projection.py
# Último comando: exit 2 esperado por E-02, no éxito de integración.
malaria_dl_local_project/.venv/bin/python scripts/db/capture_v2_e1_certificate.py
```

[Orquestación](e10_10_5e1_evidence/route_a/orchestration.jsonl) registra comandos y resultados de baseline, incluido el primer rechazo del sandbox al socket Docker. Se ejecutó luego con la autorización de aislamiento. Hubo un intento de compilación sin pglast en sys.path, corregido usando el parser ya disponible. Los intentos iniciales del probe requirieron corregir token global e identidades de fixtures; sólo el JSON final acredita E-02 y rollback.

Siguen pendientes TRAIN local/Docker sintético, procedencia producida/sellada, VALIDATION completa y calibración, recuperación/reinicio/ACK, concurrencia, publicación/linaje, API/React y productores de historial/ensembles/XAI. No se sustituyen por pruebas unitarias. No hubo acceso operativo, cutover, campañas reales, alteración del dataset congelado ni cambios D-01 a D-06.

Estado final: [contenedor E.1 detenido](e10_10_5e1_evidence/isolated_shutdown.json), volumen conservado, ninguna sesión activa del probe y gate sin owner. Para repetir probes sobre esta evidencia se debe arrancar exclusivamente ese container_id y volver a validar aislamiento; no ejecutar setup sobre el target existente.
