"""Compare before/after DB snapshots and rehash all compared dataset images."""
from __future__ import annotations
import csv,hashlib,json,gzip
from collections import Counter
from pathlib import Path

OUT=Path('docs/audits/s1_1')

def main() -> None:
    before=json.loads((OUT/'db_before.json').read_bytes() if (OUT/'db_before.json').exists() else gzip.decompress((OUT/'db_before.json.gz').read_bytes()));after=json.loads((OUT/'db_after.json').read_bytes() if (OUT/'db_after.json').exists() else gzip.decompress((OUT/'db_after.json.gz').read_bytes()))
    assert before['freeze_matches'] and after['freeze_matches']
    assert before['fingerprints']==after['fingerprints']
    assert before['table_hashes']==after['table_hashes']
    assert before['version']==after['version']
    base=Path('malaria_dl_local_project/data');historical=base/'malaria_physical_split';materialized=base/'malaria_dataset_versions'/before['version']['id']
    history=list(csv.DictReader((historical/'files_manifest.csv').open()))
    records={r['id']:r for r in before['dataset_source_records']}
    checked=0;mismatch=[]
    for row in csv.DictReader((OUT/'image_comparison.csv').open()):
        source=records[row['source_record_id']]
        paths=[(materialized/row['split']/row['class']/row['filename'],row['materialized_encoded_sha256']),(historical/history[source['tfds_index']]['relative_path'],row['historical_encoded_sha256'])]
        for path,expected in paths:
            checked+=1
            if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:mismatch.append(str(path))
    smear='3ea11683-fddb-5ed5-8fa1-c41000a9ebd1';smear_records={r['id'] for r in after['dataset_source_records'] if r['dataset_id']==smear}
    result={'before':before['fingerprints'],'after':after['fingerprints'],'freeze_matches':True,'protected_tables_identical':before['table_hashes']==after['table_hashes'],'table_hashes':after['table_hashes'],'DB_writes_by_audit':0,'dataset_writes_by_audit':0,'assignments_changed':0,'physical_files_rehashed':checked,'physical_hash_mismatches':mismatch,'smear_patients':sum(r['dataset_id']==smear for r in after['clinical_identities']),'smear_source_records':len(smear_records),'smear_identity_evidence':sum(r['source_record_id'] in smear_records for r in after['identity_evidence']),'split_counts':dict(Counter(r['split_name'] for r in after['dataset_split_assignments'] if r['dataset_version_id']==before['version']['id']))}
    (OUT/'integrity.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert not mismatch

if __name__=='__main__':main()
