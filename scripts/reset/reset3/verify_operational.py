"""Read-only verification of prepared/final database; never reserve work."""
import argparse,json
from pathlib import Path
from sqlalchemy import create_engine,text
from app.db import get_primary_engine
from common import fingerprint,require,orphan_checks
from src.malaria_dl.execution.schema import require_e10_schema
p=Path(__file__).parent
parser=argparse.ArgumentParser();parser.add_argument('--database',choices=['malaria_reset3_ready_20260929','malaria_experiments'],required=True);args=parser.parse_args()
e=create_engine(get_primary_engine().url.set(database=args.database))
with e.connect().execution_options(postgresql_readonly=True,isolation_level='REPEATABLE READ') as c,c.begin():
 require(tuple(c.execute(text('SELECT current_database(),session_user,(SELECT system_identifier::text FROM pg_control_system())')).one())==(args.database,'julio','7668020338728398886'),'IDENTITY_MISMATCH')
 expected=json.loads((p/'candidate_snapshot.json').read_text());actual=fingerprint(c,'public')
 require(actual==expected,'CANDIDATE_DATA_MISMATCH')
 frozen=json.loads((p/'source_before.json').read_text())['schemas']['public']
 protected=['users','roles','user_roles','datasets','dataset_versions','dataset_version_sources','clinical_identities','dataset_source_records','identity_evidence','dataset_materializations','dataset_split_assignments','dataset_split_images','dataset_split_statistics','dataset_split_validation_checks','dataset_materialization_activations','dataset_splits']
 require(all(actual[t]==frozen[t] for t in protected),'PROTECTED_DATA_MISMATCH')
 allowed=set(protected)|{'models','schema_migrations','alembic_version','experiment_execution_gate'}
 require(all(v['count']==0 for t,v in actual.items() if t not in allowed),'HISTORY_PRESENT')
 require(c.execute(text('SELECT version_num FROM alembic_version')).scalar_one()=='20260922_01','HEAD_MISMATCH')
 capabilities=require_e10_schema(c)
 require(c.execute(text("SELECT count(*) FROM pg_trigger t JOIN pg_class r ON r.oid=t.tgrelid JOIN pg_namespace n ON n.oid=r.relnamespace WHERE n.nspname='public' AND t.tgenabled<>'O'")).scalar_one()==0,'DISABLED_TRIGGER')
 require(c.execute(text("SELECT count(*) FROM pg_constraint WHERE connamespace='public'::regnamespace AND NOT convalidated")).scalar_one()==0,'INVALID_CONSTRAINT')
 fks=orphan_checks(c,json.loads((p/'original_manifest.json').read_text()),'public')
 print(json.dumps({'result':'PASS_DATABASE_READY','database':args.database,'revision':'20260922_01','capabilities':capabilities,'table_fingerprints':actual,'protected_full_tables_equal':protected,'history_empty_tables':sorted(set(actual)-allowed),'foreign_keys_checked':len(fks),'disabled_triggers':0,'invalid_constraints':0},default=str))
