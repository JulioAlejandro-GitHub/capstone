#!/usr/bin/env python3
"""Purga de datos científicos por subsistema. El dry-run es el modo por defecto de facto.

Uso (dentro del contenedor backend de Docker Compose):

    python scripts/db/purge.py --dataset --run --cell           # sólo reporta (dry-run)
    python scripts/db/purge.py --cell                           # sólo reporta el subsistema cell
    PURGE_DB_ALLOW_EXECUTION=1 python scripts/db/purge.py --cell --yes   # ejecuta la purga real

Flags de subsistema (independientes y combinables):

  --dataset   Tablas de datos descargados de tensorflow_datasets y su versionado/registro
              (datasets, dataset_versions, dataset_source_records, dataset_split_*,
              clinical_identities, identity_evidence, dataset_materializations, …).
  --run       Tablas de ejecuciones de modelos: entrenamiento, evaluación, explicabilidad,
              predicciones, artefactos, lineage, despliegues y publicaciones stage-2.
  --cell      Tablas del análisis de frotis ("cell (análisis de frotis)"): jerarquía de
              espécimen, ingesta de imágenes, gate de calidad de microscopía, detección y
              clasificación de células, explicabilidad y la capa de validación científica.
              Incluye microscopy_* — es una capa del mismo pipeline, no un subsistema aparte
              (ver docs/audits/cell_vs_microscopy_resolution_2026-09-08.md).

`users` (usuarios del frontend) NUNCA es un flag y NUNCA se toca bajo ninguna combinación.
`audit_events`, `alembic_version` y `schema_migrations` tampoco se tocan.

Modelo transaccional: **una transacción por subsistema**. Si se piden varios flags, se
purgan en el orden fijo cell → run → dataset y cada subsistema se confirma por separado.
Un fallo en un subsistema posterior deja intactos (ya confirmados) los anteriores; el
script lo informa explícitamente. El chequeo de dependencias FK cruzadas se hace ANTES de
abrir ninguna transacción: si un flag no pedido tiene filas que dependen de uno pedido, el
script aborta indicando qué flag falta y no borra nada.

Este script NO toca var/storage/ ni ningún archivo: es exclusivamente datos de PostgreSQL.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import os
import sys
from collections import defaultdict
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

EXPECTED_HEAD = "20260901_01"
ALLOWED_SCHEMA = "public"
EXECUTION_ENV_FLAG = "PURGE_DB_ALLOW_EXECUTION"
VERIFIED_BACKUP_ENV = "CAPSTONE_VERIFIED_BACKUP"
BACKUP_MAGIC = b"PGDMP"

# --------------------------------------------------------------------------------------
# Mapeo subsistema -> tablas. Listas estáticas y revisables. La evidencia por tabla está
# en docs/audits/cell_vs_microscopy_resolution_2026-09-08.md. El orden de borrado NO se
# codifica aquí: se calcula en runtime por orden topológico de las FK reales (hijos antes
# que padres), con desempate alfabético para logs reproducibles.
# --------------------------------------------------------------------------------------

DATASET_TABLES = frozenset({
    "datasets",                            # baseline SQL 001
    "dataset_splits",                      # baseline SQL 001 (modelo de split legacy)
    "dataset_split_images",                # baseline SQL 012 (PK = image_id)
    "dataset_versions",                    # 20260811_01
    "dataset_version_sources",             # 20260811_01
    "clinical_identities",                 # 20260811_01 (dedup de identidad para el split)
    "dataset_source_records",              # 20260811_01
    "identity_evidence",                   # 20260811_01
    "dataset_split_assignments",           # 20260811_01
    "dataset_split_statistics",            # 20260811_01
    "dataset_split_validation_checks",     # 20260811_01
    "dataset_materializations",            # 20260811_01
    "dataset_materialization_activations", # 20260811_01
})

RUN_TABLES = frozenset({
    "experiments",                     # baseline SQL 001
    "runs",                            # baseline SQL 001
    "models",                          # baseline SQL 001
    "model_versions",                  # baseline SQL 001
    "run_metrics",                     # baseline SQL 001
    "training_history",                # baseline SQL 001
    "confusion_matrices",              # baseline SQL 001
    "classification_reports",          # baseline SQL 001
    "predictions",                     # baseline SQL 001
    "artifacts",                       # baseline SQL 001
    "explainability_results",          # baseline SQL 001
    "execution_logs",                  # baseline SQL 001
    "errors",                          # baseline SQL 001
    "environment_packages",            # baseline SQL 001
    "synthetic_data_runs",             # baseline SQL 001
    "run_dataset_images",              # baseline SQL 012
    "run_io_records",                  # baseline SQL 012
    "run_clinical_metrics",            # baseline SQL 017
    "run_checkpoint_policy",           # baseline SQL 017
    "run_threshold_calibration",       # baseline SQL 017
    "run_image_predictions",           # baseline SQL 017
    "run_lineage",                     # baseline SQL 022
    "model_governance_backfill_audit", # baseline SQL 023 (append-only)
    "deployed_model_versions",         # baseline SQL 025
    "run_model_deployments",           # baseline SQL 025
    "image_analysis_jobs",             # baseline SQL 026
    "stage2_model_publications",       # baseline SQL 029
    "stage2_model_publication_events", # baseline SQL 029 (append-only)
})

CELL_TABLES = frozenset({
    # jerarquía de espécimen + ingesta (20260727_01 / 20260727_02)
    "research_subjects", "scientific_cases", "blood_samples", "smear_slides",
    "microscopy_images", "image_ingestion_batches",
    # gate técnico de calidad de microscopía (20260727_03 / 20260727_04)
    "microscopy_analysis_runs", "microscopy_analysis_run_images", "image_quality_assessments",
    "microscopy_analysis_events", "quality_gate_decisions", "quality_assessment_queue_items",
    # detección de células (20260727_05)
    "cell_detection_runs", "image_connected_components", "cell_detections",
    "cell_detection_events", "cell_crops", "scientific_reviews",
    # clasificación + explicabilidad + resumen del frotis (20260728_01)
    "cell_classification_runs", "cell_classification_inputs", "cell_predictions",
    "cell_classification_events", "cell_classification_reviews", "cell_explanations",
    "smear_analysis_summaries",
    # capa de validación científica por experto humano (20260810_01 / 20260810_02).
    # Se incluye en --cell: una anotación de validación sobre un análisis que ya no existe
    # carece de sentido clínico. Decisión registrada en la resolución de la Fase 0.
    "scientific_validation_sessions", "scientific_validation_images",
    "scientific_validation_detection_runs", "scientific_validation_classification_runs",
    "scientific_validation_annotations", "scientific_validation_annotation_events",
})

SUBSYSTEMS: dict[str, frozenset[str]] = {
    "dataset": DATASET_TABLES,
    "run": RUN_TABLES,
    "cell": CELL_TABLES,
}

# Orden global de purga cuando se piden varios flags. cell no tiene padres RESTRICT en run
# ni dataset; run es hijo de dataset. Por eso: cell, luego run, luego dataset.
GLOBAL_PURGE_ORDER = ("cell", "run", "dataset")

# Nunca se tocan. `users`, `roles`, `user_roles` = subsistema de usuarios del frontend.
USERS_TABLES = frozenset({"users", "roles", "user_roles"})
SYSTEM_TABLES = frozenset({"alembic_version", "schema_migrations", "audit_events"})

# Estados que indican trabajo en curso; abortan la purga del subsistema correspondiente.
ACTIVE_WORK_CHECKS: dict[str, tuple[tuple[str, str, tuple[str, ...]], ...]] = {
    "cell": (
        ("image_ingestion_batches", "status", ("pending", "incomplete")),
        ("microscopy_analysis_runs", "run_status",
         ("created", "quality_pending", "quality_processing")),
        ("quality_assessment_queue_items", "status", ("queued", "running")),
        ("image_quality_assessments", "assessment_status", ("pending", "processing")),
        ("cell_detection_runs", "status", ("created", "processing")),
        ("cell_classification_runs", "status", ("created", "processing")),
    ),
    "run": (
        ("runs", "status", ("created", "pending", "queued", "running", "processing")),
        ("image_analysis_jobs", "status", ("pending", "queued", "running", "processing")),
    ),
    "dataset": (
        ("dataset_versions", "status", ("DRAFT", "GENERATED", "VALIDATED")),
    ),
}


class PurgeRefused(RuntimeError):
    """Guarda de preflight incumplida. El mensaje es apto para mostrar al operador."""


# --------------------------------------------------------------------------------------
# Lógica pura (sin I/O) — cubierta por tests unitarios.
# --------------------------------------------------------------------------------------

def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="scripts/db/purge.py",
        description="Purga de datos de PostgreSQL por subsistema científico.",
    )
    parser.add_argument("--dataset", action="store_true",
                        help="Purga el subsistema dataset (tensorflow_datasets + versionado).")
    parser.add_argument("--run", action="store_true",
                        help="Purga el subsistema run (ejecuciones de modelos).")
    parser.add_argument("--cell", action="store_true",
                        help="Purga el subsistema cell (análisis de frotis, incl. microscopy).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Explícito; ya es el comportamiento por defecto sin --yes.")
    parser.add_argument("--yes", action="store_true",
                        help=f"Ejecuta la purga real. Requiere además {EXECUTION_ENV_FLAG}=1 "
                             "y un backup PostgreSQL verificado.")
    parser.add_argument("--backup", default=None,
                        help=f"Ruta (dentro del contenedor) al backup .dump custom-format. "
                             f"Alternativa a la variable {VERIFIED_BACKUP_ENV}.")
    parser.add_argument("--verbose", action="store_true", help="Muestra cada sentencia SQL.")
    return parser.parse_args(argv)


def validate_backup(path_value: str | None) -> str:
    """Verifica que exista un backup PostgreSQL custom-format legible. Devuelve la ruta."""
    if not path_value:
        raise PurgeRefused(
            f"--yes requiere un backup verificado: pase --backup o exporte "
            f"{VERIFIED_BACKUP_ENV} (el wrapper scripts/db/purge.sh lo hace por usted)."
        )
    path = Path(path_value)
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise PurgeRefused(f"backup inválido: {path_value} no es un archivo regular absoluto.")
    if path.stat().st_size < 1024:
        raise PurgeRefused("backup demasiado pequeño; probablemente truncado.")
    with path.open("rb") as stream:
        if stream.read(len(BACKUP_MAGIC)) != BACKUP_MAGIC:
            raise PurgeRefused("backup no es un dump PostgreSQL custom-format (falta 'PGDMP').")
    return str(path)


def selected_subsystems(args: argparse.Namespace) -> list[str]:
    chosen = {name for name in SUBSYSTEMS if getattr(args, name)}
    if not chosen:
        raise PurgeRefused(
            "Debe indicar al menos un flag de subsistema: --dataset, --run y/o --cell."
        )
    return [name for name in GLOBAL_PURGE_ORDER if name in chosen]


def target_tables(subsystems: list[str]) -> set[str]:
    result: set[str] = set()
    for name in subsystems:
        result |= SUBSYSTEMS[name]
    return result


def classify_table(name: str) -> str | None:
    for subsystem, tables in SUBSYSTEMS.items():
        if name in tables:
            return subsystem
    if name in USERS_TABLES:
        return "users"
    if name in SYSTEM_TABLES:
        return "system"
    return None


def toposort(tables: set[str], edges: list[tuple[str, str]]) -> list[str]:
    """Devuelve las tablas con los hijos ANTES que los padres (orden de borrado).

    `edges` son parejas (hijo, padre). Se ignoran las aristas hacia/desde tablas que no
    están en `tables` y las autorreferencias. Desempate alfabético para reproducibilidad.
    """
    remaining = set(tables)
    # dependents[t] = tablas que tienen una FK -> t (es decir, deben borrarse antes que t).
    # own_parents[t] = tablas a las que t apunta por FK (t es hijo de ellas).
    dependents: dict[str, set[str]] = defaultdict(set)
    own_parents: dict[str, set[str]] = defaultdict(set)
    for child, parent in edges:
        if child == parent or child not in remaining or parent not in remaining:
            continue
        dependents[parent].add(child)
        own_parents[child].add(parent)

    ordered: list[str] = []
    # Listas para borrar primero: aquellas a las que nada apunta.
    ready = sorted(t for t in remaining if not dependents.get(t))
    while ready:
        node = ready.pop(0)
        ordered.append(node)
        remaining.discard(node)
        for parent in sorted(own_parents.get(node, ())):
            dependents[parent].discard(node)
            if not dependents[parent] and parent in remaining and parent not in ready:
                ready.append(parent)
        ready.sort()

    if remaining:
        # Ciclo por FK RESTRICT compuestas (p. ej. cadenas de identidad). El borrado
        # completo del conjunto con session_replication_role=replica lo resuelve igual;
        # se emiten al final en orden alfabético estable.
        ordered.extend(sorted(remaining))
    return ordered


def cross_subsystem_conflicts(
    selected: list[str],
    fk_edges: list[tuple[str, str]],
    referencing_rows_exist,
) -> list[str]:
    """Detecta subsistemas NO pedidos que dependen de uno pedido.

    Para cada FK (hijo, padre) con `padre` en el conjunto objetivo y `hijo` fuera de él:
      - si el hijo pertenece a otro subsistema no pedido y tiene filas que referencian al
        padre -> falta ese flag.
      - si el hijo no está clasificado -> dependencia desconocida (fail-closed).
    """
    targets = target_tables(selected)
    needed: set[str] = set()
    unknown: set[str] = set()
    for child, parent in fk_edges:
        if parent not in targets or child in targets:
            continue
        bucket = classify_table(child)
        if bucket is None:
            unknown.add(child)
        elif (
            bucket in SUBSYSTEMS
            and bucket not in selected
            and referencing_rows_exist(child, parent)
        ):
            needed.add(bucket)
        # bucket in {"users", "system"}: esas tablas no referencian los subsistemas
        # científicos; si alguna vez lo hicieran caería en "unknown".

    messages: list[str] = []
    for bucket in sorted(unknown):
        messages.append(
            f"dependencia desconocida: la tabla '{bucket}' referencia el conjunto a purgar "
            f"y no está clasificada en ningún subsistema. Abortando (fail-closed)."
        )
    for bucket in sorted(needed):
        messages.append(
            f"el subsistema '{bucket}' tiene filas que dependen del conjunto solicitado; "
            f"añada el flag --{bucket} o no será posible purgar sin romper integridad."
        )
    return messages


# --------------------------------------------------------------------------------------
# I/O de base de datos.
# --------------------------------------------------------------------------------------

def build_engine(database_url: str):
    url = make_url(database_url)
    if url.drivername not in {"postgresql", "postgresql+psycopg"}:
        raise PurgeRefused("DATABASE_URL debe usar postgresql:// o postgresql+psycopg://")
    if url.host != "db" or (url.port or 5432) != 5432:
        raise PurgeRefused("DATABASE_URL sólo permite el PostgreSQL de Docker en db:5432")
    if not url.database or not url.username:
        raise PurgeRefused("DATABASE_URL debe identificar usuario y base canónica")
    return create_engine(database_url, future=True), url


def validate_identity(connection, url) -> None:
    database, user, schema = connection.execute(
        text("SELECT current_database(), current_user, current_schema()")
    ).one()
    if database != url.database or user != url.username or schema != ALLOWED_SCHEMA:
        raise PurgeRefused("la identidad PostgreSQL no coincide con DATABASE_URL")
    revision = connection.execute(
        text("SELECT version_num FROM alembic_version")
    ).scalar_one_or_none()
    if revision != EXPECTED_HEAD:
        raise PurgeRefused(
            f"Alembic current ({revision}) != head esperado ({EXPECTED_HEAD}); "
            "ejecute las migraciones antes de purgar."
        )


def all_base_tables(connection) -> set[str]:
    return set(connection.execute(text(
        "SELECT tablename FROM pg_tables WHERE schemaname = :s"
    ), {"s": ALLOWED_SCHEMA}).scalars())


def assert_every_table_classified(connection) -> None:
    unclassified = sorted(t for t in all_base_tables(connection) if classify_table(t) is None)
    if unclassified:
        raise PurgeRefused(
            "tablas sin clasificar en ningún subsistema (fail-closed): "
            + ", ".join(unclassified)
            + ". Actualice SUBSYSTEMS en scripts/db/purge.py y la resolución de la Fase 0."
        )


def fetch_fk_edges(connection) -> list[tuple[str, str]]:
    rows = connection.execute(text("""
        SELECT c.conrelid::regclass::text AS child,
               c.confrelid::regclass::text AS parent
        FROM pg_constraint c
        WHERE c.contype = 'f'
          AND c.connamespace = 'public'::regnamespace
    """)).all()
    # Normaliza "public.tabla" -> "tabla".
    return [(child.split(".")[-1], parent.split(".")[-1]) for child, parent in rows]


def fetch_fk_columns(connection) -> dict[tuple[str, str], list[list[str]]]:
    """(hijo, padre) -> lista de conjuntos de columnas hijas (una por constraint)."""
    rows = connection.execute(text("""
        SELECT c.conrelid::regclass::text AS child,
               c.confrelid::regclass::text AS parent,
               (SELECT array_agg(a.attname ORDER BY k.ord)
                  FROM unnest(c.conkey) WITH ORDINALITY k(attnum, ord)
                  JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum
               ) AS child_cols
        FROM pg_constraint c
        WHERE c.contype = 'f'
          AND c.connamespace = 'public'::regnamespace
    """)).all()
    result: dict[tuple[str, str], list[list[str]]] = defaultdict(list)
    for child, parent, cols in rows:
        result[(child.split(".")[-1], parent.split(".")[-1])].append(list(cols))
    return result


def make_referencing_probe(connection, fk_columns):
    def probe(child: str, parent: str) -> bool:
        for cols in fk_columns.get((child, parent), []):
            predicate = " AND ".join(f'"{col}" IS NOT NULL' for col in cols)
            found = connection.execute(text(
                f'SELECT EXISTS (SELECT 1 FROM "{child}" WHERE {predicate})'
            )).scalar_one()
            if found:
                return True
        return False
    return probe


def detect_active_work(connection, subsystems: list[str]) -> None:
    for subsystem in subsystems:
        for table, column, states in ACTIVE_WORK_CHECKS.get(subsystem, ()):
            count = connection.execute(text(
                f'SELECT count(*) FROM "{table}" WHERE "{column}" = ANY(:states)'
            ), {"states": list(states)}).scalar_one()
            if count:
                raise PurgeRefused(
                    f"trabajo activo detectado: {count} fila(s) en {table}.{column} "
                    f"en estado {sorted(states)}. Espere a que terminen antes de purgar."
                )


def count_rows(connection, tables: list[str]) -> dict[str, int]:
    return {
        table: connection.execute(text(f'SELECT count(*) FROM "{table}"')).scalar_one()
        for table in tables
    }


# --------------------------------------------------------------------------------------
# Logging homogéneo con el resto de scripts/db/.
# --------------------------------------------------------------------------------------

def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(message: str) -> None:
    print(f"{_now()} purge.py {message}", flush=True)


# --------------------------------------------------------------------------------------
# Ejecución.
# --------------------------------------------------------------------------------------

def purge_one_subsystem(engine, url, subsystem: str, ordered_tables: list[str],
                        flags: list[str], verbose: bool) -> dict[str, int]:
    """Purga un subsistema en su propia transacción. Devuelve conteos por tabla."""
    deleted: dict[str, int] = {}
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(text(
                "SET LOCAL statement_timeout = '120s'; SET LOCAL lock_timeout = '5s'"
            ))
            validate_identity(connection, url)
            # replica: desactiva TODOS los triggers (RI + append-only/protected) sólo en
            # esta transacción. Requiere superusuario (verificado: el owner canónico lo es).
            # Por eso el borrado debe ser explícito tabla por tabla: los ON DELETE CASCADE
            # tampoco se disparan bajo replica.
            connection.execute(text("SET LOCAL session_replication_role = replica"))
            for table in ordered_tables:
                statement = f'DELETE FROM "{table}"'
                if verbose:
                    log(f"sql: {statement}")
                deleted[table] = connection.execute(text(statement)).rowcount
            remaining = {
                table: connection.execute(
                    text(f'SELECT count(*) FROM "{table}"')
                ).scalar_one()
                for table in ordered_tables
            }
            leftovers = {t: n for t, n in remaining.items() if n}
            if leftovers:
                raise PurgeRefused(
                    f"validación interna: {subsystem} no quedó vacío: {leftovers}"
                )
            total = sum(deleted.values())
            log(
                f"subsystem={subsystem} flags={','.join(flags)} dry_run=false "
                f"tables={len(ordered_tables)} rows_deleted={total}"
            )
            for table in ordered_tables:
                log(f"  subsystem={subsystem} table={table} deleted={deleted[table]}")
            transaction.commit()
        except BaseException:
            if transaction.is_active:
                transaction.rollback()
            raise
    return deleted


def run(argv=None) -> int:
    args = parse_args(argv)
    try:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise PurgeRefused("DATABASE_URL es obligatoria.")
        if args.dry_run and args.yes:
            raise PurgeRefused("--dry-run y --yes son contradictorios.")
        subsystems = selected_subsystems(args)
        engine, url = build_engine(database_url)

        execute = bool(args.yes)
        backup_path = None
        if execute:
            if os.environ.get(EXECUTION_ENV_FLAG) != "1":
                raise PurgeRefused(
                    f"{EXECUTION_ENV_FLAG}=1 es obligatorio junto con --yes para ejecutar."
                )
            backup_path = validate_backup(
                args.backup or os.environ.get(VERIFIED_BACKUP_ENV)
            )

        # ---- Planificación: una única transacción de sólo lectura. ----
        with engine.connect() as connection:
            plan_tx = connection.begin()
            try:
                connection.execute(text(
                    "SET TRANSACTION READ ONLY; "
                    "SET LOCAL statement_timeout = '60s'; "
                    "SET LOCAL lock_timeout = '5s'"
                ))
                validate_identity(connection, url)
                assert_every_table_classified(connection)
                detect_active_work(connection, subsystems)

                fk_edges = fetch_fk_edges(connection)
                fk_columns = fetch_fk_columns(connection)
                probe = make_referencing_probe(connection, fk_columns)
                conflicts = cross_subsystem_conflicts(subsystems, fk_edges, probe)
                if conflicts:
                    raise PurgeRefused(" / ".join(conflicts))

                ordered: dict[str, list[str]] = {}
                for subsystem in subsystems:
                    tables = set(SUBSYSTEMS[subsystem])
                    ordered[subsystem] = toposort(tables, fk_edges)
                counts = {
                    subsystem: count_rows(connection, ordered[subsystem])
                    for subsystem in subsystems
                }
            finally:
                plan_tx.rollback()

        # ---- Reporte. ----
        mode = "EXECUTE" if execute else "DRY-RUN"
        log(f"mode={mode} flags={','.join(subsystems)} database={url.database} user={url.username}")
        if backup_path:
            log(f"backup_verificado={backup_path}")
        grand_total = 0
        for subsystem in subsystems:
            subtotal = sum(counts[subsystem].values())
            grand_total += subtotal
            log(f"subsystem={subsystem} tables={len(ordered[subsystem])} rows={subtotal}")
            for table in ordered[subsystem]:
                log(f"  subsystem={subsystem} table={table} rows={counts[subsystem][table]}")
        log(f"total_rows_in_scope={grand_total}")

        if not execute:
            log("dry-run: no se eliminó ningún dato.")
            log(
                "para ejecutar (desde la raíz del repo, en el host): "
                f"{EXECUTION_ENV_FLAG}=1 ./scripts/db/purge.sh "
                f"{' '.join('--' + s for s in subsystems)} --yes"
            )
            return 0

        # ---- Ejecución: una transacción por subsistema, en orden global. ----
        completed: list[str] = []
        try:
            for subsystem in subsystems:
                purge_one_subsystem(
                    engine, url, subsystem, ordered[subsystem], subsystems, args.verbose
                )
                completed.append(subsystem)
        finally:
            if len(completed) != len(subsystems):
                pending = [s for s in subsystems if s not in completed]
                log(f"ERROR: purga incompleta. pendientes={','.join(pending)}")
                log(
                    "subsistemas ya confirmados y NO revertidos: "
                    + (", ".join(completed) if completed else "ninguno")
                )
        log(f"purga completada: subsistemas={','.join(completed)}")
        return 0

    except PurgeRefused as exc:
        print(f"PURGE_REFUSED: {exc}", file=sys.stderr)
        return 2
    except (KeyError, TypeError, OSError, ValueError, SQLAlchemyError) as exc:
        print(f"PURGE_ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
