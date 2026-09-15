"""Metadata fingerprints + 64 TRAIN files only, explicit READ ONLY."""
import json
from pathlib import Path
from collections import Counter
from sqlalchemy import text
from src.malaria_dl.data.governed_dataset import dataset_read_connection
from src.malaria_dl.data.dataset_integrity import canonical_digest,materialized_relative_path,file_sha256
DID='d8c0cab5-09dd-597f-9de7-7ca01aee2ec2'
root=Path('/app/malaria_dl_local_project/data/malaria_dataset_versions')/DID
with dataset_read_connection() as c:
 def query(q):return c.execute(text(q),{'id':DID})
 row=query('SELECT status,methodology_json FROM dataset_versions WHERE id=:id').mappings().one()
 assert row['status']=='FROZEN';seal=row['methodology_json']['freeze_contract'];assert seal['dataset_version_id']==DID
 sources=query('SELECT r.id,r.clinical_identity_id,r.class_name,r.source_file_sha256,r.decoded_pixel_sha256 FROM dataset_source_records r JOIN dataset_version_sources vs ON vs.dataset_id=r.dataset_id WHERE vs.dataset_version_id=:id ORDER BY r.id').all()
 assert canonical_digest(sources)==seal['fingerprints']['source_population_sha256']
 assignments=query('SELECT source_record_id,clinical_identity_id,split_name FROM dataset_split_assignments WHERE dataset_version_id=:id ORDER BY source_record_id').all()
 assert canonical_digest(assignments,trailing_newline=False)==seal['fingerprints']['record_assignment_sha256']
 rows=query("SELECT a.source_record_id,a.clinical_identity_id,a.split_name,r.class_name,r.source_filename,r.source_file_sha256 FROM dataset_split_assignments a JOIN dataset_source_records r ON r.id=a.source_record_id WHERE a.dataset_version_id=:id AND a.split_name='train' ORDER BY a.source_record_id").mappings().all()
 collisions=Counter((r['split_name'],r['class_name'],r['source_filename']) for r in rows)
 refs={materialized_relative_path(r,collisions).as_posix():r for r in rows}
 selected=[]
 for label in ('uninfected','parasitized'):
  for p in sorted((root/'train'/label).glob('*.png'))[:32]:
   rel=p.relative_to(root).as_posix();reference=refs[rel];h=file_sha256(p)
   assert h==reference['source_file_sha256']
   selected.append({'path':rel,'sha256':h,'source_record_id':str(reference['source_record_id']),'split':'train'})
 assert len(selected)==64
 print(json.dumps({'dataset_version_id':DID,'freeze_contract':seal,'selected_train_samples':selected,'source_population_fingerprint_verified':True,'record_assignment_fingerprint_verified':True,'test_files_read':0},default=str,indent=2))
