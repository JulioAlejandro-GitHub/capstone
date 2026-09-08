# Purga de datos por subsistema (`scripts/db/purge.py`)

Vacía las filas de uno o varios subsistemas científicos **completos** sin tocar el esquema,
índices, vistas ni triggers. No es una limpieza genérica ni recupera espacio de disco; no
toca `var/storage/` ni ningún archivo. Para vaciar sólo el análisis de frotis conservando
el resto de subsistemas con rigor de manifiesto/rollback físico, use
[`reset_smear_analysis`](smear_analysis_reset.md) en su lugar.

## Subsistemas y flags

| Flag | Subsistema | Tablas | Código dueño |
|---|---|---:|---|
| `--dataset` | Datos descargados de `tensorflow_datasets` + versionado/registro | 13 | `malaria_dataset_split_project/src`, `backend_api/app/services/governed_datasets.py` |
| `--run` | Ejecuciones de modelos: entrenamiento, evaluación, explicabilidad, predicciones, artefactos, lineage, despliegues, publicaciones stage-2 | 28 | `malaria_dl_local_project/src`, `backend_api/app/routes/{runs,governance,predictions,explainability}.py` |
| `--cell` | Análisis de frotis: espécimen → ingesta → gate de calidad de microscopía → detección → clasificación → explicabilidad → validación científica. **Incluye `microscopy_*`** (es una capa del mismo pipeline) y `scientific_validation_*`. | 31 | `backend_api/app/{repositories,services}/{scientific,cell_analysis,cell_classification,microscopy_analysis,image_ingestion,smear_workflow,scientific_validation}.py` |

`users` (usuarios del frontend) **nunca** es un flag y **nunca** se toca. Tampoco
`audit_events`, `alembic_version` ni `schema_migrations`.

La lista exacta de tablas por subsistema, su fecha de creación (migración Alembic) y la
resolución de por qué `microscopy_*` va dentro de `--cell` están en
`docs/audits/cell_vs_microscopy_resolution_2026-09-08.md`.

## Uso

```bash
# dry-run (por defecto): sólo reporta conteos por tabla, no borra nada
scripts/db/purge.sh --dataset --run --cell
make db-purge-plan FLAGS="--cell"

# purga real: backup automático + confirmación
PURGE_DB_ALLOW_EXECUTION=1 scripts/db/purge.sh --cell --yes
make db-purge-execute FLAGS="--cell"        # pide teclear PURGE
```

`db-purge-execute` y el wrapper con `--yes` ejecutan primero `scripts/db/backup.sh`
(backup custom-format verificado en `./backups/`, montado en `/app/backups` del contenedor)
y se lo pasan al script vía `CAPSTONE_VERIFIED_BACKUP`.

## Guardas (todas fallan cerrado)

1. **Identidad**: `current_database` / `current_user` / `current_schema` deben coincidir
   con `DATABASE_URL` (destino permitido `db:5432`); Alembic `version_num` debe ser el head
   del repositorio.
2. **Cobertura de esquema**: si aparece una tabla nueva sin clasificar en ningún
   subsistema, aborta (hay que actualizar `SUBSYSTEMS` en el script y la resolución).
3. **Trabajo activo**: aborta si hay `runs` / `image_analysis_jobs` en curso,
   `*_analysis_runs` en estado no terminal, colas de calidad activas o
   `dataset_versions` en `DRAFT`/`GENERATED`/`VALIDATED`.
4. **Dependencias FK cruzadas** (previo a cualquier transacción): si un flag **no**
   solicitado tiene filas que dependen por FK `RESTRICT` de uno solicitado, aborta
   indicando el flag que falta. Nunca borra en cascada un subsistema no pedido.
   - `--dataset` en solitario ⇒ pide `--run` (`runs`, `predictions`, `image_analysis_jobs`
     referencian `dataset_versions` / `dataset_split_images`).
   - `--run` en solitario ⇒ pide `--cell` (`cell_classification_runs` referencia
     `deployed_model_versions` / `stage2_model_publications`).
   - `--cell` en solitario ⇒ siempre válido.
5. **Ejecución**: `--yes` exige además `PURGE_DB_ALLOW_EXECUTION=1` y un backup
   custom-format verificado (magic `PGDMP`, ≥ 1 KiB, archivo regular absoluto).

## Modelo transaccional

**Una transacción por subsistema.** Orden global fijo `cell → run → dataset` (cell no
tiene padres `RESTRICT` en los otros; run es hijo de dataset). Cada subsistema:

1. `SET LOCAL session_replication_role = replica` — desactiva RI y todos los triggers
   append-only/protected sólo en esa transacción (requiere superusuario; el owner canónico
   lo es). Los `ON DELETE CASCADE` **tampoco** disparan bajo `replica`, por eso el borrado
   es explícito tabla por tabla y contado.
2. `DELETE FROM` en orden hijo→padre, calculado en runtime por orden topológico de las FK
   reales (desempate alfabético para logs reproducibles).
3. Verifica conteo cero en todas las tablas del subsistema; si no, `ROLLBACK`.
4. `COMMIT`.

Si un subsistema posterior falla, los anteriores **quedan confirmados** y el script lo
informa (`subsistemas ya confirmados y NO revertidos: …`). El chequeo FK cruzado previo
hace que este caso sea raro.

## Log

Una línea por evento, con timestamp UTC, a stdout (igual que `scripts/db/status.sh`):

```
<ts> purge.py mode=EXECUTE flags=cell database=malaria_experiments user=julio
<ts> purge.py backup_verificado=/app/backups/capstone_<ts>.dump
<ts> purge.py subsystem=cell flags=cell dry_run=false tables=31 rows_deleted=16231
<ts> purge.py   subsystem=cell table=cell_explanations deleted=13
...
<ts> purge.py purga completada: subsistemas=cell
```

## Tests

`backend_api/tests/test_db_purge_tool.py` (29 casos): flags aislados y combinados, orden
topológico, `--cell` nunca purga tablas de dataset/run, ninguna combinación toca
users/system, detección de FK cruzadas, backup obligatorio, URL canónica, y aislamiento
transaccional por subsistema con motor falso. Verificación dry-run completa en
`docs/audits/purge_script_verification_2026-09-08.md`.
