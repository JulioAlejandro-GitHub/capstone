import hashlib
import json
from collections.abc import Iterable

from sqlalchemy import inspect, text


RELEVANT_TABLES = (
    "datasets", "dataset_splits", "dataset_split_images", "run_dataset_images",
    "run_io_records", "runs", "model_versions", "artifacts", "predictions",
    "training_history", "run_metrics", "run_clinical_metrics", "run_lineage",
    "schema_migrations", "alembic_version",
)


def has_column(columns: Iterable[dict], column_name: str) -> bool:
    return any(column["name"] == column_name for column in columns)


def classify_table(table_name: str, available_tables: set[str]) -> str:
    return "EXISTING" if table_name in available_tables else "MISSING"


def _jsonable(value):
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return str(value) if value is not None and not isinstance(value, (str, int, float, bool)) else value


def audit_database(engine, schema: str = "public") -> dict:
    """Introspect PostgreSQL using a transaction explicitly marked READ ONLY."""
    inspector = inspect(engine)
    available_tables = set(inspector.get_table_names(schema=schema))
    available_views = set(inspector.get_view_names(schema=schema))
    selected = [name for name in RELEVANT_TABLES if name in available_tables]
    tables = {}
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            identity = dict(connection.execute(text(
                "SELECT current_database() database_name, current_schema() schema_name, version() postgres_version"
            )).mappings().one())
            for table_name in selected:
                quoted = '"' + table_name.replace('"', '""') + '"'
                row_count = connection.execute(text(f'SELECT COUNT(*) FROM "{schema}".{quoted}')).scalar_one()
                columns = inspector.get_columns(table_name, schema=schema)
                tables[table_name] = {
                    "row_count": row_count,
                    "columns": [column["name"] for column in columns],
                    "primary_key": inspector.get_pk_constraint(table_name, schema=schema),
                    "foreign_keys": inspector.get_foreign_keys(table_name, schema=schema),
                    "indexes": inspector.get_indexes(table_name, schema=schema),
                    "unique_constraints": inspector.get_unique_constraints(table_name, schema=schema),
                    "check_constraints": inspector.get_check_constraints(table_name, schema=schema),
                }
            checksum = {"populated": None, "null": None}
            if "dataset_split_images" in tables and "checksum_sha256" in tables["dataset_split_images"]["columns"]:
                checksum = dict(connection.execute(text(
                    "SELECT COUNT(*) FILTER (WHERE checksum_sha256 IS NOT NULL) populated, "
                    "COUNT(*) FILTER (WHERE checksum_sha256 IS NULL) null "
                    "FROM public.dataset_split_images"
                )).mappings().one())
            run_type_counts = {}
            if "runs" in tables:
                run_type_counts = dict(connection.execute(text(
                    "SELECT run_type, COUNT(*) FROM public.runs GROUP BY run_type ORDER BY run_type"
                )).all())
            dataset_records = []
            if "datasets" in tables:
                dataset_records = [dict(row) for row in connection.execute(text(
                    "SELECT id::text, name, source, version, total_images, local_path, checksum, metadata "
                    "FROM public.datasets ORDER BY name, version"
                )).mappings()]
            split_storage = []
            if "dataset_split_images" in tables:
                split_storage = [dict(row) for row in connection.execute(text(
                    "SELECT dataset_id::text, dataset_name, dataset_source, dataset_dir, split_name, COUNT(*) image_count, "
                    "COUNT(*) FILTER (WHERE absolute_path IS NOT NULL) absolute_paths, "
                    "COUNT(*) FILTER (WHERE relative_path IS NOT NULL) relative_paths "
                    "FROM public.dataset_split_images GROUP BY dataset_id,dataset_name,dataset_source,dataset_dir,split_name "
                    "ORDER BY dataset_dir,split_name"
                )).mappings()]
            run_lineage_summary = []
            if "runs" in tables:
                run_lineage_summary = [dict(row) for row in connection.execute(text(
                    "SELECT run_type, COUNT(*) total, COUNT(dataset_id) with_dataset_id, "
                    "COUNT(*) FILTER (WHERE parameters ? 'dataset_dir' OR execution_parameters ? 'dataset_dir') with_dataset_dir, "
                    "COUNT(*) FILTER (WHERE parameters ? 'split_type' OR execution_parameters ? 'split_type') with_split_type, "
                    "COUNT(*) FILTER (WHERE parameters ? 'patient_id' OR parameters ? 'grouping_field' "
                    "OR execution_parameters ? 'patient_id' OR execution_parameters ? 'grouping_field') with_grouping_metadata "
                    "FROM public.runs GROUP BY run_type ORDER BY run_type"
                )).mappings()]
            evaluation_lineage_count = None
            if "run_lineage" in tables:
                evaluation_lineage_count = connection.execute(text(
                    "SELECT COUNT(*) FROM public.run_lineage rl JOIN public.runs r ON r.id=rl.child_run_id "
                    "WHERE r.run_type='evaluation' AND rl.relationship_type='evaluates_checkpoint_from'"
                )).scalar_one()
            migration_state = None
            if "alembic_version" in available_tables:
                migration_state = connection.execute(text("SELECT version_num FROM public.alembic_version ORDER BY version_num")).scalars().all()
            elif "schema_migrations" in available_tables:
                columns = tables["schema_migrations"]["columns"]
                order_column = "version" if "version" in columns else columns[0]
                migration_state = connection.execute(text(
                    f'SELECT "{order_column}" FROM public.schema_migrations ORDER BY "{order_column}"'
                )).scalars().all()
            transaction.rollback()
        except Exception:
            transaction.rollback()
            raise
    payload = {
        "database": identity,
        "tables": tables,
        "views": sorted(available_views),
        "checksum_counts": checksum,
        "run_type_counts": run_type_counts,
        "dataset_records": dataset_records,
        "split_storage": split_storage,
        "run_lineage_summary": run_lineage_summary,
        "evaluation_lineage_count": evaluation_lineage_count,
        "migration_state": migration_state,
    }
    normalized = json.dumps(_jsonable(payload), sort_keys=True, separators=(",", ":"))
    payload["schema_fingerprint_sha256"] = hashlib.sha256(normalized.encode()).hexdigest()
    return _jsonable(payload)
