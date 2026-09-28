# E10.OP3 — Preparación de migración operativa controlada

**ESTADO E10.OP3 PREPARACIÓN: NO LISTO.**

**STOP — PRECHECK FAILED.** El precheck de almacenamiento histórico falla:
43 de los 70 checkpoints referenciados por E9 no existen en sus rutas registradas.
Los 27 disponibles coinciden en bytes y SHA-256. Además, el wrapper oficial no
propaga los timeouts propuestos a sus procesos PostgreSQL.

Se detuvo la secuencia antes de crear el backup y la restauración nuevos. No se
intentó reparar almacenamiento ni cambiar scripts. Tras el STOP se completaron
únicamente comprobaciones de lectura y esta documentación. No se ejecutó DDL,
preflight transaccional de migraciones, TRAIN, TEST, claim, resume o recuperación.

Referencias leídas y contrastadas: [PRE11](e10_pre11_campaign_audit.md),
[OP1](e10_op1_preclaim_schema_guard.md), [OP2](e10_op2_migration_rehearsal.md),
[evidencia OP2](e10_op2_migration_rehearsal_evidence.json),
[runbook de backup](../capstone_backup_runbook.md) y
[política Alembic](../alembic_simple_policy.md).

Evidencia nueva: [e10_op3_preparation_evidence.json](e10_op3_preparation_evidence.json).
SHA-256: `ad7b7f600abfa05376f23b62f22fcaabee90536eb2065cbff4a1b16a09e36ec3`.
No contiene credenciales, contraseñas de roles ni dumps.

## 1. Identidad congelada del código y del destino

| Dato | Valor comprobado |
|---|---|
| HEAD | `a261a7d466650374a280229b667ac7a857653c87` |
| Estado Git inicial | Limpio; sin diff pendiente |
| SHA-256 de diff inicial vacío | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Base / schema / usuario | `malaria_experiments` / `public` / `julio` |
| Host configurado | `db:5432`, coincide con el contenedor db |
| PostgreSQL | `17.9 (Debian 17.9-1.pgdg13+1)` |
| System identifier | `7668020338728398886`, idéntico por backend y socket de db |
| Revisión instalada | `20260915_01` |
| Head único | `20260922_01` |
| Migración pendiente | `alembic/versions/20260922_01_result_events.py` |
| SHA-256 de migración | `8c2014ddfdd43244c81223095acc90be4b1cd83bad67064f86c181c4b7107290` |

La migración, `env.py` y los scripts de backup/migración son exactamente los
ensayados en OP2. La evidencia contiene sus hashes y también los de Makefile,
common.sh, Compose, E10.10 completion y OP1. Se compararon los archivos de
migración, env, completion y schema guard dentro del backend con el checkout:
coinciden. OP1 exige precisamente el head esperado; los contratos/readers de
E10.10 preservan la clasificación legacy comprobada en OP2. No se volvió a
entrenar para verificar compatibilidad.

| Contenedor | ID | Imagen / identidad |
|---|---|---|
| backend | `6283301a7b5e374d01e3eddd405c02b000fa9fccff70673ff9cc187811e87777` | `capstone-malaria-backend`; image ID en evidencia |
| db | `2604ff9884655b3b78ffc85997cbe30d6392afca7b904b5df2b37dacedb30d89` | `postgres:17.9`; image ID en evidencia |

Sólo se observaron backend, db y frontend activos. No hay segundo contenedor
PostgreSQL activo ni proceso PostgreSQL local observado. No se modificó Compose,
el comando del backend, mounts, imágenes ni release/deployment. Los dos archivos
nuevos al cierre son documentación/evidencia y no alteran la ruta ejecutable.

## 2. Resultado de los quince prechecks

Snapshot de prechecks: **2026-09-28 20:41:14.471204 UTC**, READ ONLY y
REPEATABLE READ. Los resultados no constituyen una reserva de ventana ni impiden
que aparezcan escritores después; deben repetirse antes de un eventual GO.

| Nº | Precheck | Resultado / evidencia |
|---|---|---|
| 1 | Base canónica | PASS: identidad backend/socket y system identifier coinciden |
| 2 | Revisión actual | PASS: 20260915_01 |
| 3 | Head esperado único | PASS: 20260922_01 |
| 4 | Campañas conocidas | PASS: ambas paused; E9 identificada |
| 5 | TRAIN activo | PASS: cero runs TRAIN running/pending y attempts active/completed |
| 6 | Sessions pendientes | PASS: cero active/completed |
| 7 | Local jobs retenidos | PASS: cero held/calculation_reported; job histórico released |
| 8 | GlobalGate | PASS: owner ausente, db_pid NULL, blocked_reason NULL |
| 9 | Procesos pendientes | PASS: evidencia retenida vacía/verificada, sin procesos gestionados en backend ni TRAIN/Local worker/agent observados en host |
| 10 | Transacciones incompatibles | PASS: sin otras transacciones abiertas ni prepared transactions en el snapshot |
| 11 | Locks relevantes | PASS: sin locks de otras conexiones sobre ledger, revisión, sessions, attempts o campañas |
| 12 | Espacio | PASS: host 469.485.264.896 bytes libres; Docker data/WAL 855.169.388.544 bytes libres; DB ~1,42 GB, ledger ~4,35 MB |
| 13 | Almacenamiento histórico | **FAIL: 43 checkpoints referenciados ausentes; recuperabilidad externa no acreditada** |
| 14 | Permisos | PASS: rol propietario/superuser, CONNECT, USAGE/CREATE y SELECT; no se probó permiso ejecutando DDL |
| 15 | Segunda instancia accidental | PASS: una instancia activa identificada y coincidencia de cluster por dos rutas |

No se adquirió GlobalGate ni advisory locks. No se llamó a un verificador de
dataset que escriba auditoría. No se inspeccionaron queries con parámetros
sensibles en pg_stat_activity; sólo estado, antigüedad y locks.

## 3. Bloqueo B1: almacenamiento externo

Las lecturas de archivos no cargaron Keras ni ejecutaron inferencia. Se verificaron
los 70 registros artifact de E9 contra los bytes y SHA-256 registrados:

| Run | Referencias | Disponibles e íntegros | Ausentes |
|---|---:|---:|---:|
| `3894deef-252f-424e-a4ad-d6cd555e063e` | 7 | 0 | 7 |
| `61bf6d6d-9db9-498e-a9ee-c26e94e46f2d` | 9 | 0 | 9 |
| `79f39931-ac71-4bc1-a317-149a975d1f74` | 5 | 0 | 5 |
| `8ebbd308-2cec-4275-93b7-ad56fa9e6931` | 6 | 0 | 6 |
| `a5f36df1-3341-43fd-94b9-ee1cedb834c5` | 4 | 0 | 4 |
| `d1a1413b-760c-43a2-89ee-7913e780e87a` | 27 | 27 | 0 |
| `ec0975b2-b355-4d5c-a4ec-beac31da72dd` | 12 | 0 | 12 |

Los ausentes pertenecen a los seis runs failed y apuntan a
`/app/var/artifacts/campaign_runs/<run>/epoch_<n>.keras`. Esa raíz no figura entre
los mounts persistentes actuales. No se encontraron rutas que contuvieran esos
run IDs entre los checkpoints del workspace inspeccionado. **No se concluye que
no exista alguna copia externa:** su localización y recuperación siguen sin
acreditarse. Tampoco se atribuye esta ausencia a OP2: allí no se verificaron bytes
externos, por lo que no hay comparación física anterior que permita fecharla.

Los 27 checkpoints del run verified se encuentran en `/app/var/local_artifacts`,
un bind compartido con el host. El seleccionado `epoch_15.keras` coincide con
5.150.117 bytes y SHA-256
`6fa921295a276a061f9a874d19814337bb1906de1067eb7ffcaa657ef7737015`.

La materialización del dataset existe; se contaron 22.180 imágenes TRAIN,
2.693 VAL y 2.685 TEST, coincidentes con el snapshot. Contar/leer directorios no
es ejecutar esos stages. No se afirma que esos conteos sustituyan un backup
externo restaurado o una validación exhaustiva de cada imagen.

Pg_dump no respalda esos bytes, el volumen `scientific_storage`, roles globales
ni secretos/configuración de conexión. Se inventariaron flags de roles y
membresías sin passwords, y mounts sin exportar variables secretas. La existencia
del bind/volumen no acredita por sí sola una copia recuperable. No se realizó
ninguna corrección, remapeo, copia científica ni restauración de archivos.

**Revisión humana necesaria:** localizar y acreditar las copias faltantes, o
resolver formalmente la retención/ausencia histórica y su impacto. Este documento
no acepta una excepción ni elimina referencias para convertir el FAIL en PASS.

## 4. Golden actualizado y comparación con OP2

Snapshot completo: **2026-09-28 20:44:10.138359 UTC**, READ ONLY / REPEATABLE READ.

**97 tablas, 1.192.666 filas; cero diferencias de hashes respecto de OP2.** Se
incluyen auditoría, configurations, contratos, revisiones técnicas y todas las
tablas públicas, no sólo el ledger. Los nueve schemas históricos tienen los mismos
nombres y no recibieron escrituras. La evidencia registra cada count/hash/estado.

| Entidad | Cantidad | Estados |
|---|---:|---|
| runs | 99 | completed 88, failed 10, interrupted 1 |
| experimental_campaigns | 2 | paused 2 |
| campaign_members | 72 | pending 63, failed 7, interrupted 1, verified 1 |
| campaign_attempts | 11 | failed 9, interrupted 1, verified 1 |
| train_execution_sessions | 11 | failed 9, interrupted 1, verified 1 |
| local_execution_jobs | 1 | released 1 |
| train_execution_records | 360 | Legacy, sin metadata E10 |

Identidad E9:

- Campaign ID `3acf89b7-dc42-4b7a-8e2a-ca6ea024c344`, paused.
- 36 miembros, 12 configuration hashes, siete attempts/runs/sessions.
- Contract hash `02a63b0c76dc600bcb17c7163699abf7dd4e5579643b6adbc783f50d30fcf1ba`.
- Dataset version `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`.
- 359 records propios; presupuesto tres intentos/miembro, inalterado.
- Siete hashes legacy idénticos, incluidos los 138 registros del único verified.
  Su completion.records_hash sigue siendo
  `26ddc6680b16e07c65f7ee30146abca007b7981cf97a49a633276ee6fd6beb30`.
- Completion/verification y snapshots completos coinciden con OP2; los seis
  failed conservan completion/verification NULL. No se inventaron sellos.

La evidencia contiene los siete hashes, IDs, counts, hashes de filas de runs y
sessions, de configuración/dataset, y de completion/verification. El hash del
ledger usa el digest aprobado de `kind,phase,record_key,payload` con su orden
legacy. El hash de tablas usa el mismo algoritmo del inventario OP2. No hay un
cambio de golden de base de datos que requiera reinterpretar resultados clínicos.
B1 es una carencia física recién comprobada, no una modificación del golden SQL.

## 5. Backup nuevo y restauración: detenidos por el precheck

| Requisito | Estado OP3 |
|---|---|
| Backup nuevo | **NOT_RUN_PRECHECK_FAILED** |
| Archivo / tamaño / fecha / revisión origen del nuevo dump | No generados |
| SHA-256 de backup nuevo | **No existe; null en evidencia** |
| TOC del nuevo backup | No ejecutado |
| Restauración nueva | **NOT_RUN_PRECHECK_FAILED** |
| Contenedor de restauración OP3 | No creado |
| Comparación de nuevo restore con golden | Pendiente |

No se sustituyen estos requisitos con el backup temporal OP2, aunque su restauración
haya sido comprobada. Así se respeta la regla explícita «Si cualquier precheck
falla: STOP — PRECHECK FAILED». No se declara preparada la migración.

Ubicación persistente propuesta: `backups/e10_op3/<UTC aprobado>/` dentro del
workspace, fuera de `/tmp`. El padre existe, es escribible y está excluido de Git
por `backups/`. La subcarpeta no se creó por el STOP. Cuando se autorice retomar:

```sh
# Sólo tras resolver B1 y repetir/aprobar prechecks; no ejecutado en OP3.
umask 077
op3_backup_root="$PWD/backups/e10_op3/$(date -u +%Y%m%dT%H%M%SZ)"
install -d -m 700 "$op3_backup_root"
CAPSTONE_BACKUP_DIR="$op3_backup_root" make db-backup
```

Conservar el dump 0600, TOC, logs, checksum, origen y golden. Verificar formato
custom y SHA-256 antes/después de copiar; restaurar ese mismo archive en PostgreSQL
17.9 separado, sin puertos públicos ni volúmenes operativos. Reutilizar la estrategia
validada en OP2: schema propio distinto de public, COPY intacto y remapeo de schema
verificado por catálogo. No usar ninguno de los nueve schemas originales.

La validación debe comparar las 97 tablas, estados, E9, hashes legacy, contratos,
propietarios/ACL, secuencias, constraints y revisión origen. Exit code/TOC por sí
solos no bastan. Si falla, registrar **STOP — BACKUP NOT RESTORABLE** y no migrar.

Retención propuesta: sin purga automática; conservar hasta aceptación del
cambio y prueba de recuperación, y eliminar sólo con autorización explícita de
retención. Para recuperación ante pérdida del host hace falta además una copia
durable en otro dominio de fallo, validada, cuyo destino debe acordarse; un
subdirectorio persistente del mismo disco no acredita ese escenario.

## 6. B2: ruta oficial y timeouts efectivos

Ruta canónica única: **`make db-migrate` → `scripts/db/migrate.sh`**. Se conserva
la secuencia current/heads, adopción, backup oficial, preflight transaccional con
rollback, upgrade y current/heads posteriores. No se creó un ejecutor alternativo
que salte estas guardas.

Pruebas exclusivamente READ ONLY sobre nuevas conexiones del backend:

| Invocación de prueba | PGOPTIONS en proceso hijo | lock_timeout | statement_timeout |
|---|---|---|---|
| PGOPTIONS exportado en host + `docker compose exec -T backend` | Ausente | 0 | 0 |
| `docker compose exec -T -e PGOPTIONS='-c lock_timeout=5s -c statement_timeout=60s' backend` | Explícito | 5s | 1min |

Ambas conexiones confirmaron transaction_read_only=on. La segunda prueba sólo
leyó settings: no ejecutó Alembic. Demuestra el mecanismo, no su integración en
make db-migrate. **Exportar PGOPTIONS antes de make no resuelve el wrapper actual.**
Tampoco se debe cambiar la configuración persistente de roles/DB, Compose o
DATABASE_URL para eludir la falta de propagación durante esta preparación.

Límites propuestos: lock_timeout **5 s**, statement_timeout **60 s**, aplicados
al proceso de migración y al preflight transaccional. Falta autorizar e incorporar
su propagación en el wrapper oficial, validar con SELECT los valores efectivos
en sus conexiones y congelar el nuevo HEAD. No se implementó esa corrección en
OP3 ni se presenta como aprobada. El check sobre cambios no incorporados deberá
repetirse después de cualquier modificación autorizada.

Comando canónico propuesto, **no ejecutable con GO mientras B1/B2 sigan abiertos**:

```sh
# Sólo con wrapper revisado/incorporado, prechecks, backup restaurado y GO explícito.
# Ejecutar desde la raíz del checkout aprobado.
set -o pipefail
umask 077
CAPSTONE_BACKUP_DIR="$op3_backup_root" make db-migrate \
  2>&1 | tee "$op3_backup_root/migration.log"
```

`op3_backup_root` será la ubicación persistente aprobada del bloque anterior.
Se capturará el código de salida real con pipefail. El backup adicional que
produce migrate.sh no sustituirá al archive que ya se restauró y validó: conservar
ambos. Durante la ventana no deben admitirse escritores; si cambia el golden,
detenerse y revisarlo. No se cerró admisión ni se detuvo ningún servicio en OP3.

Cancelar ante lock timeout, statement timeout, código no cero o discrepancia de
identidad. No reintentar automáticamente, no matar sesiones ajenas ni asumir que
cancelar el cliente termina una transacción del servidor. Diagnosticar mediante
SELECT. El wrapper ya comprueba current/head tras el commit; completar además
los postchecks de la sección siguiente. No utilizar stamp, downgrade, DDL manual,
DROP SCHEMA, ALTER TABLE alternativo o índices concurrentes no aprobados.

## 7. Procedimiento posterior A–M, preparado y probado sólo en esquema anterior

Conservar el golden OP3 actualizado y aprobado en un archivo controlado. Copiar
la evidencia a `/tmp/e10_op3_golden.json` dentro del backend sólo para la lectura;
el archivo durable original permanece fuera de `/tmp`. Ejecutar el bloque Python
siguiente por `docker compose exec -T`, con PYTHONPATH del proyecto. No modifica
base, archivos científicos ni reservas.

Mapeo: A revisión; B–G guard OP1 (columnas, constraint, índices, trigger y función);
H/K/L/M hashes/conteos íntegros de las tablas, incluidos estado, contratos,
configuraciones, snapshots y presupuesto; I siete hashes legacy; J metadata E10
nula en todos los registros históricos. El set de tablas debe ser idéntico.

La versión exacta del bloque se probó contra la base anterior: salida **2 esperada**,
A y B–G false, resto true, changed_tables vacío y siete hashes true. Es evidencia
de rechazo correcto antes de migrar, **no un postcheck de una migración realizada**.

```sh
# Lectura solamente. Después del cambio real se exige salida 0.
docker cp docs/engineering/e10_execution_refactor/e10_op3_preparation_evidence.json \
  capstone_backend:/tmp/e10_op3_golden.json
docker compose exec -T -w /app \
  -e PYTHONPATH=/app/malaria_dl_local_project:/app \
  -e PYTHONDONTWRITEBYTECODE=1 backend python - <<'PY'
"""Read-only postcheck; never migrates or reserves."""
import hashlib
import json
from sqlalchemy import text
from app.db import get_primary_engine
from src.malaria_dl.campaigns.contracts import digest
from src.malaria_dl.execution.schema import require_e10_schema, E10SchemaNotReady
from src.malaria_dl.persistence.execution_record_readers import read_legacy_execution_records

def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=True, default=str).encode()).hexdigest()

with open('/tmp/e10_op3_golden.json') as file:
    evidence = json.load(file)
baseline = evidence['golden']
checks = {}
with get_primary_engine().connect().execution_options(
        postgresql_readonly=True, isolation_level='REPEATABLE READ') as connection:
    with connection.begin():
        identity = connection.execute(text(
            "SELECT current_database(),current_schema(),current_user,"
            "current_setting('transaction_read_only')")).one()
        assert tuple(identity) == ('malaria_experiments', 'public', 'julio', 'on')
        cluster = str(connection.execute(text(
            'SELECT system_identifier FROM pg_control_system()')).scalar_one())
        assert cluster == evidence['postgres']['system_identifier']
        versions = connection.execute(text(
            'SELECT version_num FROM public.alembic_version')).scalars().all()
        checks['A_revision'] = versions == ['20260922_01']
        try:
            require_e10_schema(connection)
            checks['B_to_G_E10_capabilities'] = True
        except E10SchemaNotReady:
            checks['B_to_G_E10_capabilities'] = False
        tables = connection.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        )).scalars().all()
        checks['table_set'] = set(tables) == set(baseline['tables'])
        changed = []
        for table, original in baseline['tables'].items():
            if table == 'alembic_version':
                continue
            quoted = '"' + table.replace('"', '""') + '"'
            projection = ("to_jsonb(t)-ARRAY['event_id','event_sequence']"
                          if table == 'train_execution_records' else 'to_jsonb(t)')
            rows = connection.execute(text(
                f'SELECT ({projection})::text FROM public.{quoted} t '
                f'ORDER BY ({projection})::text')).scalars().all()
            if len(rows) != original['count'] or sha(rows) != original['sha256']:
                changed.append(table)
        checks['H_K_L_M_legacy_contracts_states_attempts'] = not changed
        hashes = {}
        for run in baseline['e9']['runs']:
            hashes[run['run_id']] = digest(read_legacy_execution_records(
                connection, run['run_id'])) == run['records_hash']
        checks['I_seven_legacy_hashes'] = len(hashes) == 7 and all(hashes.values())
        new_events = connection.execute(text(
            "SELECT count(*) FROM public.train_execution_records t "
            "WHERE to_jsonb(t)->>'event_id' IS NOT NULL "
            "OR to_jsonb(t)->>'event_sequence' IS NOT NULL")).scalar_one()
        checks['J_no_artificial_E10_events'] = new_events == 0
print(json.dumps({'postcheck_pass': all(checks.values()), 'checks': checks,
                  'changed_tables': changed, 'legacy_hashes': hashes}, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 2)
PY
```

Tras un cambio real se requiere salida 0 y todos los checks true. Ante otro
resultado, mantener admisión cerrada y aplicar la tabla de fallos. No usar TRAIN
como smoke test ni interpretar esquema compatible como permiso para reanudar E9.

## 8. Manejo de fallos

| Momento | Acción |
|---|---|
| Precheck fallido | STOP sin DDL; caso actual B1 |
| Backup inválido | STOP; conservar logs; no utilizar OP2 como sustituto |
| Restauración inválida | STOP — BACKUP NOT RESTORABLE |
| Lock timeout | STOP y diagnóstico READ ONLY; sin retry ni cambio automático de DDL |
| DDL interrumpido | Verificar conexión/transacción, revisión y objetos; no asumir rollback |
| Respuesta perdida tras commit | Consultar revisión, capacidades y golden antes de decidir |
| Postcheck fallido | Mantener admisión cerrada; preservar evidencia y base fallida |
| Evidencia legacy alterada | STOP y plan de recuperación bajo autorización adicional |

El preflight transaccional del wrapper ejecuta DDL aunque finalmente haga rollback:
también requiere GO; **no se ejecutó en public durante OP3**. No se autoriza
restauración sobre public ni downgrade como solución automática.

## 9. Plan de recuperación pendiente del backup nuevo

El plan deberá vincularse al nuevo archivo y SHA-256 una vez creado y restaurado:

1. Conservar la base fallida y sus logs; impedir nuevos trabajos mediante una
   ventana autorizada. No destruir el estado que requiere diagnóstico.
2. Restaurar el archive nuevo validado a un PostgreSQL limpio y separado;
   comprobar revisión origen, conteos, hashes, golden E9, constraints y secuencias.
3. Restaurar roles/privilegios globales desde respaldo aprobado y revisar owner/ACL.
   La evidencia de OP3 registra roles y membresías, pero no sus secretos; los
   valores originales se obtendrán del almacén autorizado, sin volcarlos a Git.
4. Verificar datasets/checkpoints contra sus referencias. B1 impide acreditar
   actualmente la recuperación completa; no sintetizar ni recalcular archivos.
5. Comparar escrituras posteriores al backup y acordar su tratamiento. No aceptar
   pérdida silenciosa ni presentar un downgrade como restauración del historial.
6. Solicitar aprobación explícita del cambio de conexión/servicios y de sus
   credenciales, con destino y validaciones definidos. No ejecutarlo en OP3.

No se ejecutó un corte, restore ni recuperación destructiva. OP2 acredita el
método sobre su archivo; no acredita todavía un backup nuevo OP3 ni bytes externos.

## 10. Control GO/NO-GO y próximos pasos humanos

**NO-GO actual. No se solicita GO DDL con prechecks fallidos.**

Antes de poder solicitar GO para `20260922_01_result_events` sobre
`malaria_experiments.public`:

- Resolver/revisar B1 sin borrar evidencia ni aceptar excepciones implícitas.
- Autorizar e incorporar una solución B2 dentro del wrapper oficial; comprobar
  los límites reales y congelar nuevamente HEAD, status y hashes.
- Repetir todos los prechecks y el inventario; revisar cualquier cambio legítimo
  que afecte al golden autorizado.
- Crear el backup nuevo en ubicación durable y restaurarlo; registrar archivo,
  SHA-256, retención y evidencia de integridad completa.
- Acreditar respaldos externos, roles/configuración, responsables, ventana y
  criterios de cancelación/recuperación.
- Solicitar GO humano explícito que identifique commit, base/schema/cluster,
  revisión origen/destino, backup verificado, golden y ventana. Una aprobación
  de la preparación no se interpretará como esa autorización de DDL.

## 11. Cierre y archivos modificados

Se añadieron únicamente:

- `docs/engineering/e10_execution_refactor/e10_op3_operational_migration.md`.
- `docs/engineering/e10_execution_refactor/e10_op3_preparation_evidence.json`.

Git estaba limpio al inicio; no se modificaron migraciones ni scripts aprobados.
Public continúa en 20260915_01; el inventario y el postcheck de lectura conservaron
los hashes de las 97 tablas y los siete runs. E9 sigue paused, cero intentos nuevos,
ningún schema histórico modificado, ningún evento E10 fabricado, sin TRAIN/TEST,
sin E10.11 y sin cambios de release/deployment.

Trabajo detenido para revisión humana de B1 y B2.

**ESTADO E10.OP3 PREPARACIÓN: NO LISTO.**
