"""S1.1 SELECT-only snapshot; output goes to stdout, never to the database."""
import hashlib
import json
import os
from sqlalchemy import create_engine, text
from guards import require_read_only_select

VERSION = 'd8c0cab5-09dd-597f-9de7-7ca01aee2ec2'

def digest(rows: list) -> str:
    return hashlib.sha256(''.join('|'.join('' if v is None else str(v) for v in r)+'\n' for r in rows).encode()).hexdigest()

def main() -> None:
    engine = create_engine(os.environ['DATABASE_URL'], connect_args={'options': '-c default_transaction_read_only=on'}, isolation_level='REPEATABLE READ')
    with engine.connect() as c:
        assert c.execute(text('SHOW transaction_read_only')).scalar_one() == 'on'
        def rows(sql: str) -> list:
            require_read_only_select(sql)
            return [dict(r) for r in c.execute(text(sql), {'id': VERSION}).mappings()]
        version = rows('SELECT * FROM dataset_versions WHERE id=:id')[0]
        queries = {
          'source_population_sha256': 'SELECT r.id,r.clinical_identity_id,r.class_name,r.source_file_sha256,r.decoded_pixel_sha256 FROM dataset_source_records r JOIN dataset_version_sources vs ON vs.dataset_id=r.dataset_id WHERE vs.dataset_version_id=:id ORDER BY r.id',
          'clinical_identity_sha256': 'SELECT i.id,i.source_identifier,i.status FROM clinical_identities i JOIN dataset_version_sources vs ON vs.dataset_id=i.dataset_id WHERE vs.dataset_version_id=:id ORDER BY i.id',
          'patient_assignment_sha256': 'SELECT clinical_identity_id,split_name FROM dataset_split_assignments WHERE dataset_version_id=:id GROUP BY clinical_identity_id,split_name ORDER BY clinical_identity_id,split_name',
          'record_assignment_sha256': 'SELECT source_record_id,clinical_identity_id,split_name FROM dataset_split_assignments WHERE dataset_version_id=:id ORDER BY source_record_id',
        }
        fps = {}
        for k,q in queries.items():
            values = [list(r.values()) for r in rows(q)]
            fps[k] = hashlib.sha256('\n'.join('|'.join(str(v) for v in r) for r in values).encode()).hexdigest() if 'assignment' in k else digest(values)
        result = {'version': version, 'fingerprints': fps, 'freeze_matches': fps == version['methodology_json']['freeze_contract']['fingerprints'], 'read_only': True}
        if not result['freeze_matches']:
            print(json.dumps(result,default=str))
            raise SystemExit('STOP: frozen contract mismatch')
        for table in ['datasets','dataset_version_sources','clinical_identities','dataset_source_records','identity_evidence','dataset_split_assignments','dataset_materializations']:
            result[table] = rows('SELECT * FROM '+table+' ORDER BY id') if table != 'dataset_version_sources' else rows('SELECT * FROM dataset_version_sources ORDER BY dataset_version_id,dataset_id')
        result['table_hashes'] = {k: hashlib.sha256(json.dumps(v,sort_keys=True,default=str).encode()).hexdigest() for k,v in result.items() if isinstance(v,list)}
        print(json.dumps(result,default=str))

if __name__ == '__main__':
    main()
