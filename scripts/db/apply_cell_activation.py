"""Apply only the versioned cell-activation migration; never activate a model."""
import json
import os
import subprocess
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

TABLES = ('runs', 'run_lineage', 'model_versions', 'artifacts', 'stage2_model_publications',
          'stage2_model_publication_events', 'deployed_model_versions', 'assessment_attempts',
          'assessment_identities', 'assessment_results')


def fingerprint(engine):
    with engine.connect() as connection, connection.begin():
        connection.exec_driver_sql('SET TRANSACTION READ ONLY')
        return {table: connection.execute(text(f"""
          SELECT count(*),md5(coalesce(string_agg(payload,'' ORDER BY payload),'')) FROM (
            SELECT (to_jsonb(t)-ARRAY['evaluation_attempt_id','threshold_assessment_attempt_id'])::text payload
            FROM public.{table} t) rows
        """)).one()._tuple() for table in TABLES}


def main():
    # Credentials stay in memory; neither the URL nor environment is printed.
    url = make_url(os.environ['PGV2_DATABASE_URL'])
    database = url.database
    engine = create_engine(url, hide_parameters=True)
    try:
        before = fingerprint(engine)
        result = subprocess.run([sys.executable, '-m', 'alembic', '-c', '/app/alembic_v2.ini',
            '-x', 'activation_migration=true', '-x', f'activation_database={database}', 'upgrade', 'head'],
            env={**os.environ, 'PGV2_DATABASE_URL':url.render_as_string(hide_password=False)},
            capture_output=True, text=True)
        if result.returncode:
            message = result.stderr.replace(url.password or '[no-password]', '[redacted]')
            raise RuntimeError(message)
        after = fingerprint(engine)
        assert before == after, 'Scientific or publication rows changed during schema migration'
        with engine.connect() as connection:
            revision = connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one()
        print(json.dumps({'revision': revision, 'rows_unchanged': before == after,
                          'row_counts': {table: row[0] for table, row in after.items()}}, indent=2))
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
