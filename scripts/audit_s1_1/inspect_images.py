"""Exhaustive local image audit. Reads datasets; writes only audit artifacts."""
from __future__ import annotations
import gzip
import ast
import csv
import hashlib
import io
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image

OUT = Path('docs/audits/s1_1')
CELL = '3f4058c7-5671-4c2f-a089-d1482d5661f4'
SMEAR = '3ea11683-fddb-5ed5-8fa1-c41000a9ebd1'

def pixel_info(data: bytes) -> tuple[int,int,str]:
    with Image.open(io.BytesIO(data)) as image:
        rgb = image.convert('RGB')
        return rgb.width, rgb.height, hashlib.sha256(rgb.tobytes()).hexdigest()

def filename_patient(name: str) -> str | None:
    return name.split('_cell_')[0].split('_IMG_')[0] if '_cell_' in name and '_IMG_' in name else None

def candidate(name: str) -> str | None:
    match = re.fullmatch(r'\d+(C.+)',name)
    return match.group(1) if match else None

def write_csv(name: str, rows: list[dict]) -> None:
    with (OUT/name).open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

def main() -> None:
    db=json.loads((OUT/'db_before.json').read_bytes() if (OUT/'db_before.json').exists() else gzip.decompress((OUT/'db_before.json.gz').read_bytes()))
    assert db['freeze_matches'], 'STOP: frozen contract mismatch'
    ids={i['id']:i for i in db['clinical_identities']}
    assignments={i['source_record_id']:i for i in db['dataset_split_assignments'] if i['dataset_version_id']==db['version']['id']}
    records=[r for r in db['dataset_source_records'] if r['dataset_id']==CELL]
    by_name={(r['class_name'],r['source_filename']):r for r in records}
    mappings=defaultdict(set);mapping_summary={}
    for path in sorted(Path('malaria_dataset_split_project/var/audit/source').glob('*.csv')):
        rows=list(csv.reader(path.open(encoding='utf-8-sig')))
        for row in rows:
            for filename in ast.literal_eval(','.join(x for x in row[1:] if x.strip())):
                mappings[filename].add(row[0].strip())
        mapping_summary[path.name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'rows':len(rows),'ids':len({r[0].strip() for r in rows})}
    archive=next(Path('data/tensorflow_datasets/downloads/malaria').glob('*.zip'))
    summary={'mapping':mapping_summary,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'archive_size':archive.stat().st_size}
    materialized=Path('malaria_dl_local_project/data/malaria_dataset_versions')/db['version']['id']
    historical=Path('malaria_dl_local_project/data/malaria_physical_split')
    history=list(csv.DictReader((historical/'files_manifest.csv').open()))
    tfrecords={}
    import tensorflow as tf
    for shard in sorted(Path('data/tensorflow_datasets/malaria/1.0.0').glob('*.tfrecord-*')):
        for raw in tf.compat.v1.io.tf_record_iterator(str(shard)):
            features=tf.train.Example.FromString(raw).features.feature
            encoded=features['image'].bytes_list.value[0]
            label=features['label'].int64_list.value[0]
            h=hashlib.sha256(encoded).hexdigest()
            tfrecords.setdefault((h,label),[]).append(pixel_info(encoded))
    summary['tfrecord_examples']=sum(map(len,tfrecords.values()));summary['tf_feature_keys']=sorted(features)
    audit=[]; filename_discrepancies=[]; unmapped=[]
    with zipfile.ZipFile(archive) as z:
        for member in sorted(z.namelist()):
            if not member.endswith('.png'):continue
            parts=Path(member).parts;cls=parts[-2].lower();name=parts[-1]
            r=by_name[(cls,name)];a=assignments[r['id']];pid=ids[r['clinical_identity_id']]['source_identifier']
            data=z.read(member);sha=hashlib.sha256(data).hexdigest();w,h,pixel=pixel_info(data)
            mat=materialized/a['split_name']/cls/name
            matdata=mat.read_bytes();matsha=hashlib.sha256(matdata).hexdigest();matinfo=pixel_info(matdata)
            old=historical/history[r['tfds_index']]['relative_path'];olddata=old.read_bytes();oldinfo=pixel_info(olddata)
            tfmatches=tfrecords.get((sha,0 if cls=='parasitized' else 1),[])
            parsed=filename_patient(name)
            if parsed!=pid:filename_discrepancies.append({'filename':name,'filename_prefix':parsed,'official_patient_id':pid})
            if mappings[name]!={pid}:unmapped.append(name)
            audit.append({'filename':name,'class':cls,'patient_id':pid,'source_record_id':r['id'],'clinical_identity_id':r['clinical_identity_id'],'split':a['split_name'],'width':w,'height':h,'channels':3,'nlm_encoded_sha256':sha,'decoded_pixel_sha256':pixel,'tfds_encoded_matches':len(tfmatches),'tfds_pixel_match':tfmatches==[(w,h,pixel)],'materialized_encoded_sha256':matsha,'materialized_pixel_match':matinfo==(w,h,pixel),'historical_encoded_sha256':hashlib.sha256(olddata).hexdigest(),'historical_pixel_match':oldinfo==(w,h,pixel),'db_hash_match':r['source_file_sha256']==sha and r['decoded_pixel_sha256']==pixel,'db_dimensions_match':(r['image_width'],r['image_height'])==(w,h)})
    write_csv('image_comparison.csv',audit)
    summary.update({'images':len(audit),'class_counts':dict(Counter(r['class'] for r in audit)),'filename_parse_discrepancies':filename_discrepancies,'official_mapping_mismatches':unmapped,'patient_ids':len({r['patient_id'] for r in audit}),'filename_prefix_ids':len({filename_patient(r['filename']) for r in audit}),'checks':{k:sum(r[k] for r in audit) for k in ['tfds_pixel_match','materialized_pixel_match','historical_pixel_match','db_hash_match','db_dimensions_match']},'tfds_same_encoded_bytes':sum(r['tfds_encoded_matches']==1 for r in audit),'materialized_same_encoded_bytes':sum(r['materialized_encoded_sha256']==r['nlm_encoded_sha256'] for r in audit),'historical_same_encoded_bytes':sum(r['historical_encoded_sha256']==r['nlm_encoded_sha256'] for r in audit)})
    patients=[]
    for ident in sorted((i for i in ids.values() if i['dataset_id']==CELL),key=lambda i:i['source_identifier']):
        rr=[r for r in audit if r['clinical_identity_id']==ident['id']]
        patients.append({'patient_id':ident['source_identifier'],'clinical_identity_id':ident['id'],'records':len(rr),'parasitized':sum(r['class']=='parasitized' for r in rr),'uninfected':sum(r['class']=='uninfected' for r in rr),'split':','.join(sorted({r['split'] for r in rr}))})
    write_csv('cell_patients.csv',patients)
    cellids={r['patient_id']:r for r in patients};matrix=[]
    for ident in sorted((i for i in ids.values() if i['dataset_id']==SMEAR),key=lambda i:i['source_identifier']):
        pid=ident['source_identifier'];cand=candidate(pid);rr=[r for r in db['dataset_source_records'] if r['clinical_identity_id']==ident['id']];cr=cellids.get(cand)
        matrix.append({'polygon_patient_id':pid,'cell_patient_candidate':cand,'transformation':'remove leading decimal digits before C (candidate only)','match_status':'UNRESOLVED','evidence':'textual suffix and existing UNVERIFIED hint; no authoritative cross-source identity map','cell_dataset_present':cr is not None,'cell_split':'','cell_class_records':json.dumps({'parasitized':cr['parasitized'],'uninfected':cr['uninfected']}) if cr else '', 'polygon_images':len(rr),'polygon_RBC':sum(r['metadata']['annotation']['rbc_count'] for r in rr),'polygon_parasitized_RBC':sum(r['metadata']['annotation']['label_counts'].get('Parasitized',0) for r in rr),'polygon_uninfected_RBC':sum(r['metadata']['annotation']['label_counts'].get('Uninfected',0) for r in rr)})
    write_csv('polygon_cell_matrix.csv',matrix)
    summary['suspected_aliases']=[r for r in patients if r['patient_id'].startswith('C47P8')]
    summary['case_collisions']=len(patients)-len({r['patient_id'].casefold() for r in patients})
    summary['cross_source_status']=dict(Counter(r['match_status'] for r in matrix))
    (OUT/'image_summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps({k:v for k,v in summary.items() if k!='filename_parse_discrepancies'},indent=2))

if __name__=='__main__':main()
