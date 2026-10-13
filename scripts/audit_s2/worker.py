"""Docker entry point; RAW is mounted read-only by the existing compose service."""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

from sqlalchemy import text

from malaria_split.persistence.database import create_postgresql_engine
from malaria_split.persistence.same_split import apply_same_split, preflight
from malaria_split.sources.thin_blood_smears_pf import inspect_thin_blood_smears_pf

RAW = Path('/app/malaria_dl_local_project/data/NIH-NLM-ThinBloodSmearsPf')


def main() -> None:
    inspections = [inspect_thin_blood_smears_pf(RAW, annotation_set=s) for s in ('Polygon Set', 'Point Set')]
    engine = create_postgresql_engine(os.environ['DATABASE_URL'])
    if sys.argv[1:] == ['--apply']:
        result = apply_same_split(engine, inspections)
    elif sys.argv[1:] == ['--preflight']:
        with engine.connect() as connection:
            result = preflight(connection, inspections)
    else:
        raise ValueError('Specify --preflight or --apply')
    with engine.connect() as connection:
        result["postgresql"] = dict(connection.execute(text("SELECT current_database() AS database, current_user AS role, version() AS server")).mappings().one())
    print(json.dumps(result, sort_keys=True, default=str))
    engine.dispose()


if __name__ == '__main__':
    main()
