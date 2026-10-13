"""Disposable PostgreSQL, actual constraints and synthetic physical TRAIN/VAL files."""
from collections.abc import Iterator
from contextlib import contextmanager
import gzip
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import psycopg
import pytest
from PIL import Image
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection, Engine

from src.malaria_dl.campaigns.contracts import canonical, expand_matrix
from src.malaria_dl.campaigns.service import frozen_contract, planning_environment
from src.malaria_dl.common.paths import DATA_DIR
from src.malaria_dl.data.dataset_integrity import canonical_digest, file_sha256
from src.malaria_dl.data.governed_dataset import REQUIRED_CHECKS
from src.malaria_dl.execution.repository import ExecutionRepository
from src.malaria_dl.persistence.dataset_evidence import verify_dataset_for_execution
from test_campaigns_e4 import protocol, request

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope='session')
def engine() -> Iterator[Engine]:
    # Fixed service/database on an internal network. Never consume host .env credentials.
    with psycopg.connect('host=db02c-db dbname=db02c_test user=postgres', autocommit=True) as c:
        dump = gzip.decompress((ROOT / 'tests/db02b/fixtures/operational_schema.sql.gz').read_bytes()).decode()
        c.execute('\n'.join(line for line in dump.splitlines() if not line.startswith('\\')))
        # Reproduce the already closed DB-02B fix in the disposable database only.
        c.execute((ROOT / 'scripts/db/capstone_db_02b/apply.sql').read_text())
        c.execute('INSERT INTO public.experiment_execution_gate(singleton) VALUES(true)')
        # No Alembic table at all: neither accepted nor fabricated migration stamps.
        c.execute('DROP TABLE public.alembic_version')
        for name in ('custom_cnn', 'vgg16', 'densenet121'):
            c.execute("INSERT INTO public.models(name,architecture,model_type,framework) VALUES(%s,%s,'cnn','tensorflow')", (name,name))
    instance = create_engine('postgresql+psycopg://postgres@db/db02c_test')
    yield instance
    instance.dispose()


@pytest.fixture
def statements() -> Iterator[list[str]]:
    seen: list[str] = []

    def capture(conn: Connection, cursor: object, statement: str, parameters: object,
                context: object, executemany: bool) -> None:
        seen.append(statement)
        assert 'alembic' not in statement.lower()
        assert not any(word in statement.lower() for word in
                       ('to_regclass', 'pg_get_functiondef', 'pg_get_triggerdef', 'pg_attribute', 'server_version'))

    event.listen(Engine, 'before_cursor_execute', capture)
    yield seen
    event.remove(Engine, 'before_cursor_execute', capture)


@pytest.fixture
def case(engine: Engine, tmp_path: Path) -> SimpleNamespace:
    version, source, materialization = uuid4(), uuid4(), uuid4()
    root = DATA_DIR / str(version)
    patients, assignments, sources, identities = [], [], [], []
    with engine.begin() as c:
        # Each test starts from an unused disposable gate. A released gate retains
        # this still-live pytest PID; it must not leak into another test case.
        c.execute(text("UPDATE experiment_execution_gate SET process_evidence='{}' WHERE owner IS NULL"))
        c.execute(text("INSERT INTO datasets(id,name) VALUES(:id,'DB02C synthetic')"), {'id': source})
        c.execute(text("""INSERT INTO dataset_versions(id,name,semantic_version,grouping_strategy,grouping_field,
            stratification_strategy,split_algorithm,split_algorithm_version,random_seed,
            target_train_ratio,target_val_ratio,target_test_ratio,positive_class)
            VALUES(:id,:name,'0.0.0','synthetic','patient','synthetic','synthetic','1',11,.34,.33,.33,'parasitized')"""),
            {'id': version, 'name': 'DB02C '+str(version)})
        c.execute(text("INSERT INTO dataset_version_sources(dataset_version_id,dataset_id,role) VALUES(:v,:d,'PRIMARY')"), {'v': version, 'd': source})
        for n, split in enumerate(('train', 'val', 'test')):
            for label, name in enumerate(('uninfected', 'parasitized')):
                patient, record = uuid4(), uuid4()
                filename = f'{n}_{label}.png'
                path = root / split / name / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                Image.new('RGB', (8, 8), (n*40, label*90, 20)).save(path)
                checksum = file_sha256(path)
                params = dict(p=patient, r=record, d=source, v=version, split=split,
                              label=label, name=name, filename=filename, sha=checksum)
                c.execute(text("""INSERT INTO clinical_identities(id,dataset_id,identity_type,source_identifier,status)
                    VALUES(:p,:d,'PATIENT',CAST(:p AS text),'VERIFIED')"""), params)
                c.execute(text("""INSERT INTO dataset_source_records(id,dataset_id,clinical_identity_id,
                    source_record_key,source_filename,class_index,class_name,source_file_sha256,decoded_pixel_sha256,identity_status)
                    VALUES(:r,:d,:p,CAST(:r AS text),:filename,:label,:name,:sha,:sha,'VERIFIED')"""), params)
                c.execute(text("""INSERT INTO dataset_split_assignments(dataset_version_id,source_record_id,
                    clinical_identity_id,split_name,class_index,class_name) VALUES(:v,:r,:p,:split,:label,:name)"""), params)
                patients.append((patient, split))
                assignments.append((record, patient, split))
                sources.append((record, patient, name, checksum, checksum))
                identities.append((patient, str(patient), 'VERIFIED'))
        fingerprints = dict(
            patient_assignment_sha256=canonical_digest(sorted(patients), trailing_newline=False),
            record_assignment_sha256=canonical_digest(sorted(assignments), trailing_newline=False),
            source_population_sha256=canonical_digest(sorted(sources)),
            clinical_identity_sha256=canonical_digest(sorted(identities)))
        freeze = dict(version='malaria_patient_split_freeze_v1', dataset_version_id=str(version),
                      dataset_materialization_id=str(materialization), fingerprints=fingerprints,
                      assignment_count=6, source_record_count=6, clinical_identity_count=6)
        c.execute(text("""INSERT INTO dataset_materializations(id,dataset_version_id,attempt_number,status,
            reconciliation_status,relative_root,record_count) VALUES(:m,:v,1,'READY','PASS',:root,6)"""),
            dict(m=materialization, v=version, root=str(version)))
        for check in REQUIRED_CHECKS:
            c.execute(text("""INSERT INTO dataset_split_validation_checks(dataset_version_id,check_name,status,
                blocking_for_validation,blocking_for_freeze) VALUES(:v,:check,'PASS',true,true)"""), dict(v=version, check=check))
        c.execute(text("UPDATE dataset_versions SET methodology_json=CAST(:contract AS jsonb) WHERE id=:v"),
                  dict(v=version, contract=canonical({'freeze_contract': freeze})))
        for state in ('GENERATED', 'VALIDATED', 'FROZEN'):
            c.execute(text('UPDATE dataset_versions SET status=:state WHERE id=:v'), dict(v=version, state=state))
    snapshot = verify_dataset_for_execution(str(version), required_splits=('train', 'val'), consumer='db02c.test')
    req, p, env = request([11, 12]), protocol(), planning_environment()
    req.update(models=['custom_cnn'], optimizers=['adam'])
    contract = frozen_contract(name='DB02C synthetic', purpose='stop before TRAIN', experiment_id=None,
        dataset=snapshot.metadata(), evidence_id=snapshot.evidence_id, requested=req, protocol=p, environment=env,
        matrix=expand_matrix(req, p, frozen=True, dataset=snapshot.metadata()))

    @contextmanager
    def scope(readonly: bool = False) -> Iterator[Connection]:
        with engine.begin() as c:
            if readonly:
                c.execute(text('SET TRANSACTION READ ONLY'))
            yield c

    repo, cid = ExecutionRepository(scope), str(uuid4())
    row = repo.create_frozen(cid, contract, 'db02c')
    return SimpleNamespace(engine=engine, repo=repo, cid=cid, row=row, root=root,
                           artifacts=tmp_path, snapshot=snapshot, contract=contract)
