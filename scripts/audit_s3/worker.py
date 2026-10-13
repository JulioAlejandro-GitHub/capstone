"""Docker-only validation/freeze; an exception leaves the source version untouched."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any
from sqlalchemy import Connection, text

from malaria_split.governance.freeze import freeze_dataset_version
from malaria_split.governance.trainability import get_dataset_version_trainability
from malaria_split.persistence.database import create_postgresql_engine
from malaria_split.persistence.same_split import VERSION_ID
from malaria_split.persistence.smear_validation import prepare_smear_validation
from malaria_split.sources.thin_blood_smears_pf import inspect_thin_blood_smears_pf
from evidence import inventory, protected_state, snapshot_database, version_core

RAW = Path('/app/malaria_dl_local_project/data/NIH-NLM-ThinBloodSmearsPf')
CELL = Path('/app/malaria_dl_local_project/data/malaria_dataset_versions/d8c0cab5-09dd-597f-9de7-7ca01aee2ec2')


def main() -> None:
    mode = sys.argv[1]
    if mode not in ('--preflight', '--apply'):
        raise ValueError('Expected --preflight or --apply')
    payload = json.load(sys.stdin)
    engine = create_postgresql_engine(os.environ['DATABASE_URL'])
    inspections = [inspect_thin_blood_smears_pf(RAW, annotation_set=s) for s in ('Polygon Set', 'Point Set')]

    def integrity_guard(connection: Connection) -> None:
        if protected_state(snapshot_database(connection)) != payload['protected_database']:
            raise ValueError('STOP: protected Cell/S2 rows changed')
        if inventory(RAW) != payload['raw'] or inventory(CELL) != payload['cell']:
            raise ValueError('STOP: RAW or Cell files changed; freeze prohibited')
        version = dict(connection.execute(text('SELECT * FROM dataset_versions WHERE id=:id'), {'id': VERSION_ID}).mappings().one())
        if version_core(version) != version_core(payload['s2_version']):
            raise ValueError('STOP: S2 version scientific definition changed')

    with engine.connect() as connection:
        before = dict(connection.execute(text('SELECT * FROM dataset_versions WHERE id=:id'), {'id': VERSION_ID}).mappings().one())
        checks_before = [dict(r) for r in connection.execute(text('SELECT * FROM dataset_split_validation_checks WHERE dataset_version_id=:id ORDER BY check_name'), {'id': VERSION_ID}).mappings()]
        statistics_before = [dict(r) for r in connection.execute(text('SELECT * FROM dataset_split_statistics WHERE dataset_version_id=:id'), {'id': VERSION_ID}).mappings()]
        # Before any writes, compare protected rows against committed S2 evidence.
        if protected_state(snapshot_database(connection)) != payload['protected_database']:
            raise ValueError('STOP: protected rows differ from S2')
        prepared = prepare_smear_validation(connection, inspections, payload['expected_assignments'])
    if mode == '--apply':
        outcome = asdict(freeze_dataset_version(engine, VERSION_ID, source_inspections=inspections,
                         expected_assignments=payload['expected_assignments'], integrity_guard=integrity_guard))
    else:
        with engine.connect() as connection:
            integrity_guard(connection)
        outcome = {'result': 'PREFLIGHT_PASS'}
    with engine.connect() as connection:
        after = dict(connection.execute(text('SELECT * FROM dataset_versions WHERE id=:id'), {'id': VERSION_ID}).mappings().one())
        protected_after = protected_state(snapshot_database(connection))
        checks = [dict(r) for r in connection.execute(text('SELECT * FROM dataset_split_validation_checks WHERE dataset_version_id=:id ORDER BY check_name'), {'id': VERSION_ID}).mappings()]
        statistics = [dict(r) for r in connection.execute(text('SELECT * FROM dataset_split_statistics WHERE dataset_version_id=:id'), {'id': VERSION_ID}).mappings()]
        trainability = asdict(get_dataset_version_trainability(connection, VERSION_ID))
    print(json.dumps(dict(outcome=outcome, before=before, after=after, protected_after=protected_after,
                         validation=asdict(prepared.formal), manifest=prepared.manifest,
                         manifest_fingerprint=prepared.manifest_fingerprint, fingerprints=prepared.fingerprints,
                         checks_before=checks_before, statistics_before=statistics_before,
                         persisted_checks=checks, persisted_statistics=statistics, trainability=trainability), sort_keys=True, default=str))
    engine.dispose()


if __name__ == '__main__':
    main()
