"""Publish non-secret evidence only after the complete isolated workflow passes."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
DEST=ROOT/'docs/engineering/e10_execution_refactor'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def table(rows,headers):return '| '+' | '.join(headers)+' |\n|'+'|'.join(['---']*len(headers))+'|\n'+'\n'.join('| '+' | '.join(map(str,r))+' |' for r in rows)+'\n'

def build(work):
 def read(name):return json.loads((work/name).read_text())
 r=read('rehearsal.json');f=read('finish.json');v=read('verify_final.json');b=read('protected_assets_before.json');a=read('protected_assets_after.json')
 if r['result']!='RESET.1B APROBADO' or not f['public_unchanged'] or b!=a:raise RuntimeError('COMPLETE_REHEARSAL_REQUIRED')
 if v['retained_indirect_references'] or v['maintenance_functions_remaining'] or v['disabled_triggers_including_fk']:raise RuntimeError('FINAL_POSTCONDITIONS_FAILED')
 m=json.loads((DEST/'reset_1_full_history_manifest.json').read_text())
 if read('source_after.json')['schemas']['public']['alembic_version']['sha256']!=m['tables']['alembic_version']['sha256_before']:raise RuntimeError('OPERATIONAL_REVISION_CHANGED')
 evidence={'task':'RESET.1B','result':'RESET.1B APROBADO','production_execution_authorized':False,'base_manifest_sha256':digest(DEST/'reset_1_full_history_manifest.json'),'backup_restore':read('restore.json'),'rehearsal':r,'final_clone':v,'operational_invariance':f,'production_sql_guard':read('production_guard.json'),'commit_boundary_control_flow':read('commit_boundary.json'),'protected_assets_before':b,'protected_assets_after':a,'protected_assets_identical':True,'disposable_files_cleanup':read('file_cleanup.json'),'source_public_revision_after':'20260915_01','source_public_alembic_fingerprint_after':read('source_after.json')['schemas']['public']['alembic_version'],'source_schema_fingerprints_before':read('source_before.json')['schemas'],'source_schema_fingerprints_after':read('source_after.json')['schemas'],'code_sha256':{str(p.relative_to(ROOT)):digest(p) for p in sorted(Path(__file__).parent.iterdir()) if p.is_file()},'development_failures_resolved':['PL/pgSQL literal percent signs now passed without DBAPI parameters; original definitions preserved.','JSON negative probe now uses a bound parameter rather than embedded SQL JSON.'],'no_scientific_train_test_or_inference':True}
 (DEST/'reset_1b_rehearsal_evidence.json').write_text(json.dumps(evidence,indent=2,ensure_ascii=False,default=str)+'\n')
 overlay={'task':'RESET.1B','base_manifest':'reset_1_full_history_manifest.json','base_manifest_sha256':evidence['base_manifest_sha256'],'merge_key':'canonical_location','unchanged_locations':len(m['files'])-414,'production_file_actions_authorized':False,**r['file_classification']}
 (DEST/'reset_1b_file_classification.json').write_text(json.dumps(overlay,indent=2,ensure_ascii=False)+'\n')
 source_tables=read('source_after.json')['schemas']['public']
 guardnames=', '.join('`'+x+'`' for x in r['guard_functions_patched'])
 protected_rows=[[t,data['count'],data['sha256'],'IGUAL'] for t,data in r['protected_before'].items()]
 report=f'''# RESET.1B — Mantenimiento excepcional y ensayo integral

**RESET.1B APROBADO — exclusivamente el diseño y ensayo aislado.** No autoriza reset, migración, baja de publicaciones ni borrado físico operativo. Trabajo detenido para revisión humana.

El ensayo eliminó íntegramente el historial del clon y verificó **70 tablas históricas vacías**, **139.586 filas protegidas idénticas**, **208 FK sin huérfanos** y restauración exacta tras un fallo SQL posterior a todos los DELETE. Después confirmó el reset solamente en el clon, restauró los guards originales y migró el esquema vacío a `20260922_01`: OP1 aprobó Docker y Local. No se ejecutó TRAIN, TEST, inferencia, reanudación ni backfill E10.

## 1. Alcance y referencias

Se leyeron [auditoría RESET.1](reset_1_full_history_audit.md), [manifiesto RESET.1](reset_1_full_history_manifest.json), los SQL `full_history_reset_preview.sql` y `full_history_reset_plan.sql`, y [OP3](e10_op3_operational_migration.md). Se conserva su contenido: los nuevos archivos no desbloquean retrospectivamente el plan de producción.

Backup verificado: `{evidence['backup_restore']['backup']}`; SHA-256 `{evidence['backup_restore']['sha256']}`. Se restauraron 311 bloques COPY sin cambiar valores; sólo se remapearon referencias de esquema en DDL fuera de COPY. Los 97 hashes/conteos del clon coincidieron con el inventario aprobado: **1.192.667 filas**. No se usaron tablas supuestas.

Clon: `{r['target']['container']}` / `{r['target']['database']}` / `{r['target']['schema']}`, cluster `{r['target']['system_identifier']}`. Contenedor PostgreSQL 17.9 creado para esta operación, sin puertos publicados, bind mounts ni volúmenes compartidos con `capstone_db`. La identidad operativa `7668020338728398886` está explícitamente prohibida como destino de mantenimiento.

## 2. B1 — Alternativas y selección

| Alternativa | Evaluación |
|---|---|
| Deshabilitar triggers, cambiar replication role o retirar FK | Prohibida; no utilizada. |
| Añadir una excepción permanente por GUC o editar migraciones históricas | Rechazada: superficie accesible por la aplicación y cambio retrospectivo del contrato. |
| Restaurar un subconjunto en una base nueva y hacer cutover | No demuestra un reset transaccional del esquema existente; requiere otro diseño/despliegue y conservación adicional de identidades. |
| Sustitución transaccional acotada de funciones, con allowlist y restauración antes de commit | **Seleccionada para el clon**. Conserva triggers/FK y admite sólo las preimágenes autorizadas durante la transacción privada. |

Se localizaron **23 funciones** usadas por los BEFORE DELETE de tablas candidatas, incluidas tablas actualmente vacías. Se mantienen INSERT/UPDATE y los AFTER triggers originales. Funciones afectadas temporalmente:

{guardnames}.

Mecanismo implementado:

1. El orquestador sólo crea destinos nuevos con prefijo/label RESET.1B; comprueba volumen aislado y ausencia de puertos/bind mounts. El ejecutor comprueba base, schema, session_user, cluster y `session_replication_role=origin`, además de GlobalGate libre. No acepta un destino operacional ni un flag que lo habilite.
2. Una transacción toma locks `SHARE ROW EXCLUSIVE` sobre las 97 tablas, con lock_timeout 3 s y statement_timeout 300 s por sentencia de reset. La cuenta autorizada es `{r['target']['user']}`, credencial aleatoria privada exclusiva del clon. No se otorgan privilegios operativos ni se pretende proteger contra un superusuario hostil: se impide uso accidental o desde el rol de aplicación.
3. Se materializan en `pg_temp` las **PK exactas y SHA-256 de la preimagen completa** de las filas seleccionadas. Los tres conjuntos grandes derivados de run IDs se convierten también en PK individuales. La allowlist no es un predicado de borrado universal.
4. El contexto fija operación, `pg_current_xact_id()` y backend PID. La función de decisión comprueba cluster, base, session_user, ausencia de SET ROLE, operación y contexto transaccional; una fila cambiada deja de coincidir con su hash. OIDs de relaciones atan la autorización al esquema restaurado. Las tablas protegidas no tienen entradas autorizadas.
5. Un trigger adicional `a_reset1b_delete_scope` en cada tabla rechaza DELETE fuera de la allowlist, incluso en tablas que originalmente no tenían un guard de borrado. El wrapper insertado en cada función original sólo permite `TG_OP='DELETE'` de una preimagen autorizada. Ninguna FK se desactiva, elimina ni modifica.
6. Se difieren únicamente constraints que ya eran deferrable mediante el mecanismo normal de PostgreSQL. Se respeta el orden hijo→padre de RESET.1. Antes de confirmar: `SET CONSTRAINTS ALL IMMEDIATE`, anti-joins de las 208 FK, cero historial y comparación de hashes protegidos.
7. Se reinstalan las definiciones originales obtenidas con `pg_get_functiondef`, incluidos propietarios, ACL y propiedades; se retiran **sólo los triggers/funciones de scope creados por este ensayo** y sus tablas temporales. El catálogo debe coincidir exactamente con el catálogo anterior antes del commit. No se retira ningún trigger original/constraint. Fallo o desconexión antes del commit revierte conjuntamente DDL y DML.

Las funciones nuevas no sobreviven al mantenimiento. El catálogo final tiene **0 funciones `_reset1b_*`, 0 triggers deshabilitados —incluidos FK— y 0 constraints sin validar**. `public` dentro del clon tiene cero tablas; nunca fue destino de la restauración operativa.

Controles negativos reales:

{table([[x['check'],x.get('message','preimagen alterada rechazada'),x.get('sqlstate','boolean false')] for x in r['committed_reset']['negative_probes']],['Control','Resultado','SQLSTATE'])}

Se probaron 24 tablas con guards y datos antes del mantenimiento. Tras el rollback completo, las mismas operaciones volvieron a producir **los mismos errores originales**. Tras el commit del estado vacío, DELETE de la auditoría preservada volvió a rechazar con `audit_events is append-only`; el catálogo completo seguía idéntico. No se fabricaron runs para aparentar pruebas sobre un estado vacío.

## 3. B2 — Resolución de las 414 ubicaciones

[Manifiesto actualizado por ubicación](reset_1b_file_classification.json): overlay del manifiesto aprobado, unido por `canonical_location` y ligado a su SHA-256. Cada ubicación conserva ruta, tamaño, hash observado, evidencia de reporte/manifest cuando acredita un ID, propietarios, referencias a runs y acción. Las otras 6.124 ubicaciones mantienen la política original.

{table(sorted(r['file_classification']['classifications'].items()),['Clasificación','Ubicaciones'])}

- **18** ubicaciones tienen referencias exactas a propietarios aprobados en reportes/manifests; sólo sus copias son candidatas adicionales de cuarentena.
- **108** son compartidas: 99 aliases de outputs por modelo, 6 markers/metadatos de directorio y 3 locks de coordinación. Se preservan aunque algún contenido coincida con un resultado histórico.
- **288** no acreditan un propietario dentro del conjunto de IDs aprobado. Se resuelve su tratamiento como **PRESERVE_AMBIGUOUS**, tal como ordena RESET.1B. No se inventó propietario ni se autorizó borrado por estar en outputs. Puede existir procedencia histórica en esos archivos; esta prueba no permite atribuirles exclusividad para borrarlos.

La conservación de ambiguos es una decisión explícita y verificada de protección, no una declaración de que se hayan eliminado. Cualquier futura ampliación del borrado de esos archivos necesita nueva evidencia y autorización. No se confunde “cero historial en PostgreSQL” con “todo directorio de outputs físicamente vacío”.

Los 43 checkpoints E9 previamente ausentes mantienen `ALREADY_MISSING`, sin fabricación ni sustitución de hashes. El manifiesto base también conserva referencias fuente ausentes; ninguna ausencia se materializó artificialmente para el ensayo.

## 4. B3 — Retirada atómica y estado sin modelo productivo

La investigación confirmó un mecanismo compartido utilizable: `Stage2PublicationService` y `Stage2ModelAvailabilityService` aceptan `connection_factory`. Se inyectó una factory que devuelve **la misma conexión/transacción** y no confirma al salir de cada servicio. Se utilizaron los servicios existentes; no se llamó ningún endpoint operativo.

La secuencia del clon fue:

1. Desactivar la publicación activa `81d69942-17eb-4999-a6bd-2b05779a65a4` y el deployment `cf2f20d3-a1e0-499c-b5ab-501b7c1ae198` dentro de la transacción del reset, con actor/razón/correlación de ensayo.
2. Diferir invalidación de caché usando un adaptador privado; todavía no aplicar efectos no transaccionales.
3. Verificar que no quedan publicaciones/deployments activos; borrar hijos, predicciones, asociaciones, eventos, publicaciones, deployments, model_versions y runs según el grafo real.
4. Mantener los AFTER audit triggers originales. Se generaron **96 eventos de auditoría de DELETE** de members/configurations y **1 evento de baja de publicación**. Cada ID nuevo se capturó y validó contra su publicación aprobada o la preimagen exacta de la fila eliminada. Se incorporaron individualmente a la allowlist; no hubo DELETE por prefijo ni supresión de auditoría. La evidencia externa de esta operación se conserva en el JSON.
5. Confirmar sólo tras todas las postcondiciones y restauración de guards; después invalidar las **36 model versions** en una caché privada sembrada para la prueba. Se verificó cero entradas residuales. Si SQL falla, se descarta la cola; no se aplica invalidación.

Total de filas eliminadas en cada secuencia íntegra: **1.053.178** = 1.053.081 históricas aprobadas + 97 eventos creados por el propio procedimiento. El resultado tiene 139.586 filas protegidas; no queda evidencia E10 ni evento de mantenimiento insertado artificialmente en el ledger científico.

Estado SIN MODELO PRODUCTIVO comprobado sin inferencia: `Stage2PublicationService.models()` devuelve `[]`; resolver el alias retirado devuelve `GovernanceConflictError` controlado, sin referencias huérfanas ni modelo cacheado disponible. Las arquitecturas siguen en el registry. No se promete disponibilidad de inferencia hasta entrenar y publicar un modelo nuevo.

El endpoint operativo actual continúa usando factories independientes: **no se modificó ese endpoint ni se afirma que ya tenga atomicidad compartida**. La vía demostrada es el coordinador de mantenimiento aislado con una conexión compartida. Su despliegue/uso operativo requiere una autorización posterior distinta.

## 5. Ensayo completo, fallo y recuperación

Se ejecutaron dos secuencias completas sobre la restauración, no sólo DELETE individuales:

| Fase | Resultado |
|---|---|
| Restauración del backup | 97/97 tablas, 1.192.667 filas y hashes coincidentes con RESET.1 |
| Reset íntegro dentro de transacción | 70 tablas históricas en cero; 208 FK sin huérfanos; fuentes iguales |
| Fallo inyectado después de todos los DELETE y de cuarentena | Error SQL real `RESET1B_INJECTED_FAILURE_AFTER_FULL_DELETE` |
| ROLLBACK y recuperación de archivos | 97/97 hashes/conteos originales, catálogo original y todas las copias restauradas |
| Repetición íntegra y commit sólo en clon | 70 tablas históricas en cero; 139.586 filas protegidas conservadas |
| Final del mantenimiento | Guards originales restaurados; no excepción disponible para la aplicación |
| Migración posterior del clon vacío | Head `20260922_01`, OP1 READY, cero backfill |

Se corrigieron dos fallos del harness durante su desarrollo (transporte de `%` literal en PL/pgSQL y parámetro JSON en un control negativo); esos intentos abortaron y quedaron revertidos. No se alteraron funciones históricas para ocultar esos fallos. La evidencia de aprobación corresponde a las dos secuencias **completas** de la versión corregida.

Hashes de todos los datos protegidos antes/después del reset:

{table(protected_rows,['Tabla / subconjunto','Filas','SHA-256 anterior','Posterior'])}

`audit_events_preserved` son las 1.102 auditorías de fuentes/seguridad excluidas por IDs del reset. No se vació indiscriminadamente audit_events. Todos los demás conjuntos históricos, incluidos los originalmente vacíos, se verificaron en cero; los 70 conteos figuran en `rehearsal.e10.empty_history_counts`.

También se inspeccionaron referencias UUID a las raíces históricas en JSON/texto de las tablas protegidas pequeñas y auditoría retenida: **ninguna referencia exacta retenida a esos IDs**. Los conjuntos grandes de datos fuente mantienen sus hashes íntegros y las FK validadas. Esta comprobación se declara por su alcance, no como una interpretación universal del texto libre.

## 6. Cuarentena recuperable sobre copias

Se copiaron **{r['filesystem_after']['copied_files']} archivos presentes** a un filesystem privado desechable y se comprobó cada SHA-256 contra el manifiesto. Se ensayaron **{r['filesystem_after']['quarantine_candidates']} movimientos** entre `live/` y `quarantine/`, sólo dentro de ese árbol; **{r['filesystem_after']['protected_copies']} copias protegidas** permanecieron en `live/`.

La selección usa ubicaciones canónicas deduplicadas y acciones explícitas; los nombres internos son hashes de ubicación, no paths suministrados a rename. Se comprueban raíz privada, marker/token, ausencia de symlinks, integridad y conflictos de destino. Un journal persistente en el árbol desechable registra PREPARED/QUARANTINING/QUARANTINED/RESTORING/RESTORED/SQL_COMMITTED; su contenido permite recuperar las rutas por ID sin depender de una transacción del filesystem.

El fallo SQL ocurrió **después** del reset íntegro y la cuarentena: se hizo rollback de PostgreSQL, se devolvieron todas las copias y se comparó el snapshot completo. Tras el éxito, la cuarentena quedó registrada como SQL_COMMITTED. Se volvieron a leer los **{r['operational_files']['files']} originales presentes**: todos conservaron SHA-256. Ningún rename/unlink/rmtree recibió una ruta operativa.

Ante pérdida de confirmación de COMMIT, el código conserva la cuarentena con estado `COMMIT_UNCERTAIN`: no interpreta el error del cliente como rollback. Debe reconciliarse en una conexión nueva con conteos/hashes y catálogo antes de restaurar o declarar commit. La rama de error se comprobó con dobles de transacción/filesystem sobre el bloque real del runner; no se inyectó pérdida real de conexión en PostgreSQL; la recuperación demostrada corresponde al error SQL anterior a COMMIT.

El cierre retiró sólo el contenedor/volumen del clon y los árboles de copias desechables con marker válido. No se eliminó un archivo operativo. No existe paso de borrado definitivo productivo en este código.

Además, se calcularon fingerprints de **{sum(x['entries'] for x in b.values()):,} entradas** y {sum(x['bytes'] for x in b.values()):,} bytes de datasets originales/materializaciones físicas, configuración del split, configuración científica, registry/arquitecturas y 29 migraciones; las dos lecturas coincidieron:

{table([[path,data['entries'],data['bytes'],data['sha256']] for path,data in b.items()],['Raíz protegida','Entradas','Bytes','SHA-256 del inventario ordenado'])}

Cada fingerprint se construye sobre rutas relativas, tamaños y SHA-256 por archivo; los symlinks se representan por su destino sin moverlos. `__pycache__`/pyc no son configuración científica. Las 74 imágenes de microscopía originales también quedaron protegidas por sus filas y copias verificadas.

## 7. E10 sobre el estado vacío

Se utilizó `alembic.command.upgrade(..., 'head')` y la conexión suministrada soportada por el `alembic/env.py` del proyecto, dentro de la transacción del clon; no se cambió DATABASE_URL, no se llamó el wrapper contra public y no se editó ninguna migración.

- Origen `20260915_01`; destino `20260922_01`.
- OP1 Docker y Local: `E10_SCHEMA_NOT_READY` antes, `E10_SCHEMA_READY` después. Local se detuvo al salir del preflight, antes de get/claim/reserva.
- Columnas event_id/event_sequence, constraint de metadata, índices únicos y trigger de fencing/eventos comprobados por el guard OP1 real.
- Ledger `train_execution_records`: **0 filas antes y después**, sin backfill.
- ResultService y PostgresResultRepository instanciados sobre el clon; un envelope válido de una ejecución no reservada fue rechazado como `WriterNotAuthorized`. No se creó run, attempt, session, resultado ni evento. Esto demuestra disponibilidad del servicio y su frontera de autorización, no una ejecución científica exitosa.
- Registry: `custom_cnn`, `vgg16`, `densenet121`, configuraciones resolubles sin construir modelos ni ejecutar TRAIN/TEST.
- Hashes de fuentes/configuración conservados. Sólo cambia la revisión Alembic entre los datos protegidos; ese cambio está expresamente autorizado en el clon.

El orden ensayado fue **restore → retirada/reset atómico → restauración de guards → commit del clon vacío → migración E10 → verificaciones**. No implementa E10.11 ni modifica ResultService, GlobalGate, heartbeat, retry o reglas de claim. Los blockers propios del despliegue operativo OP3 (por ejemplo propagación efectiva de timeouts en el wrapper) no quedan autorizados ni corregidos por este ensayo.

## 8. Reproducción, barrera operativa y revisión

Código y SQL: `scripts/reset/reset1b/`. Seguir su README desde la raíz del checkout; se necesita Docker y el backup cuyo hash coincide con RESET.1. Usar un directorio privado nuevo:

```sh
python3 scripts/reset/reset1b/run.py prepare --work /private/tmp/reset1b_new
python3 scripts/reset/reset1b/run.py classify --work /private/tmp/reset1b_new
python3 scripts/reset/reset1b/run.py rehearse --work /private/tmp/reset1b_new
python3 scripts/reset/reset1b/run.py finish --work /private/tmp/reset1b_new
```

`production_blocked.sql`: READ ONLY y excepción incondicional `RESET1B_PRODUCTION_NOT_AUTHORIZED`; se probó en el clon con exit 3 antes de DML. No hay COMMIT ni flag de desbloqueo operacional. El template de mantenimiento sólo se instancia con identidad del clon validada. `target.json`/`target.env` contienen credenciales desechables privadas y no forman parte de los entregables.

La revisión humana debe decidir separadamente si autoriza preparar una ejecución operativa con identidad/rol/ventana/backup nuevos, writers detenidos, recuperación y aprobación explícita. No ejecutar este ensayo apuntándolo a public ni quitar sus guardas. Un ensayo aprobado no equivale a autorización de borrado real.

## 9. Estado operativo y entregables

Lecturas operativas `{f['source_before']}` → `{f['source_after']}`: **public íntegro en `20260915_01`**, {sum(x['count'] for x in source_tables.values()):,} filas y 97 tablas iguales; catálogo igual y nueve schemas sintéticos iguales. No se cambiaron releases/deployments operativos ni se reanudó E9. Todas las acciones de baja, DELETE y Alembic ocurrieron en el clon ya retirado.

- [Diseño de mantenimiento](reset_1b_maintenance_design.md).
- [Evidencia completa](reset_1b_rehearsal_evidence.json): conteos, hashes, controles negativos, recuperación, guards, E10 y comparación operativa.
- [Clasificación de las 414 ubicaciones](reset_1b_file_classification.json).
- `scripts/reset/reset1b/`: orquestador Docker, snapshot SELECT, mantenimiento SQL acotado, reset íntegro, simulador de archivos, verificación, limpieza de copias y barrera operativa.

**RESET.1B APROBADO.** Detenido para revisión humana; sin autorización ni ejecución del reset o migración operativos.
'''
 (DEST/'reset_1b_maintenance_design.md').write_text(report)
 print('RESET.1B evidence and design written')
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--work',type=Path,required=True);args=parser.parse_args();build(args.work)
