"""Read-only governed sampling and immutable official assets for isolated 01B."""
import hashlib,json,subprocess,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
E=Path(os.environ.get('BIOMEDCLIP_EVIDENCE_DIR',str(ROOT/'docs/audits/evidence/biomedclip_01b')))
E.mkdir(parents=True,exist_ok=True)
WORK=Path(os.environ.get('BIOMEDCLIP_WORK_DIR','/Users/julio/.cache/capstone-biomedclip-01b'))
WORK.mkdir(parents=True,exist_ok=True)
DATASET='d8c0cab5-09dd-597f-9de7-7ca01aee2ec2'
def sql(q):
    command=['docker','exec','-i','capstone_db','sh','-c','PGOPTIONS="-c default_transaction_read_only=on" psql -X -At -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"']
    return subprocess.check_output(command,input=q,text=True).strip()
def write(name,data):
    (E/name).write_text(json.dumps(data,indent=2)+'\n')
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def snapshot():
    tables=['models','model_versions','runs','train_execution_sessions','train_execution_records','assessment_identities','assessment_attempts','assessment_results','assessment_artifacts','artifacts','experimental_campaigns','run_configurations']
    return {t:json.loads(sql(f"SELECT json_build_object('count',count(*),'xmin_sum',coalesce(sum(xmin::text::numeric),0)) FROM {t}")) for t in tables}
if __name__=='__main__':
    write('database_before.json',snapshot())
    query=f"""WITH population AS (
      SELECT a.dataset_version_id,a.source_record_id AS sample_id,a.clinical_identity_id AS patient_id,
      a.split_name,r.class_name,r.source_filename,r.source_file_sha256 AS sha256,
      count(*) OVER(PARTITION BY a.split_name,r.class_name,r.source_filename) AS collisions,
      row_number() OVER(PARTITION BY a.split_name,r.class_name ORDER BY a.source_record_id) AS n
      FROM dataset_split_assignments a JOIN dataset_source_records r ON r.id=a.source_record_id
      WHERE a.dataset_version_id='{DATASET}' AND a.split_name IN ('train','val'))
      SELECT json_agg(p ORDER BY split_name,class_name,sample_id) FROM population p
      WHERE (split_name='train' AND n<=8) OR (split_name='val' AND n<=4)"""
    rows=json.loads(sql(query))
    root=ROOT/'malaria_dl_local_project/data/malaria_dataset_versions'/DATASET
    for r in rows:
        filename=(r['sample_id']+'__' if r['collisions']>1 else '')+r['source_filename']
        p=root/r['split_name']/r['class_name']/filename
        assert p.is_file() and not p.is_symlink(),p
        assert sha(p)==r['sha256'],p
        r['path']=str(p.relative_to(ROOT));r['label']=int(r['class_name']=='parasitized')
    assert not ({r['patient_id'] for r in rows if r['split_name']=='train'} & {r['patient_id'] for r in rows if r['split_name']=='val'})
    overlap=sql(f"SELECT count(*) FROM (SELECT clinical_identity_id FROM dataset_split_assignments WHERE dataset_version_id='{DATASET}' GROUP BY clinical_identity_id HAVING count(DISTINCT split_name)>1) x")
    assert overlap=='0',overlap
    write('samples.json',{'dataset_version_id':DATASET,'selection':'first UUID per class/split; train 8/class, val 4/class','patient_split_overlap':int(overlap),'samples':rows})
    from huggingface_hub import HfApi,hf_hub_download
    api=HfApi()
    assets=[]
    for role,repo,allowed in [
      ('biomedclip','microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224',['open_clip_config.json','open_clip_pytorch_model.bin']),
      ('text','microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract',['config.json','tokenizer_config.json','special_tokens_map.json','vocab.txt','tokenizer.json'])]:
        revision={'biomedclip':'9f341de24bfb00180f1b847274256e9b65a3a32e','text':'d673b8835373c6fa116d6d8006b33d48734e305d'}[role]
        info=api.model_info(repo,revision=revision,files_metadata=True)
        dest=WORK/'original'/role/info.sha
        files=[]
        for sibling in info.siblings:
            if sibling.rfilename not in allowed: continue
            p=Path(hf_hub_download(repo,sibling.rfilename,revision=info.sha,local_dir=dest))
            digest=sha(p)
            expected=getattr(sibling.lfs,'sha256',None) if sibling.lfs else None
            if expected: assert expected==digest
            files.append({'name':sibling.rfilename,'path':str(p),'bytes':p.stat().st_size,'sha256':digest,'upstream_lfs_sha256':expected})
        assets.append({'role':role,'repo_id':repo,'revision':info.sha,'directory':str(dest),'files':files})
        write('original_assets.json',assets)
        print(role,info.sha,len(files),flush=True)
