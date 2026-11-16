"""Validate audit deliverables and write their manifest; no product mutations."""
from pathlib import Path
import json,csv,re,hashlib,subprocess,datetime
B=Path(__file__).resolve().parents[1];R=B.parents[2]
required=['CAPSTONE_P3_04_INFORME_GENERAL.md','CAPSTONE_P3_04_ARQUITECTURA_Y_FLUJOS.md','CAPSTONE_P3_04_CATALOGO_FUNCIONES.md','CAPSTONE_P3_04_DATOS_Y_ARTEFACTOS.md','CAPSTONE_P3_04_ANALISIS_POR_OPCION.md','CAPSTONE_P3_04_RUN_00b8d407.md','CAPSTONE_P3_04_COMPARACION_Y_COBERTURA.md','CAPSTONE_P3_04_HALLAZGOS.md','CAPSTONE_P3_04_EVIDENCIA_PARA_P3.md','README.md']
assert all((B/n).is_file() for n in required)
errors=[];links=0
for p in B.glob('*.md'):
 for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if target.startswith(('http:','https:','#')):continue
  target=target.split('#')[0];q=(p.parent/target).resolve();links+=1
  if not q.is_file() and str(q.relative_to(B)) not in ['evidence/audit_validation.json','evidence/manifest.json']:errors.append(dict(document=p.name,target=target))
assert not errors,errors[:10]
for p in (B/'sql').glob('*.sql'):
 sql=p.read_text();assert re.match(r'BEGIN.*READ ONLY;',sql.splitlines()[0]);assert not re.search(r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|CALL|COPY)\b',sql,re.I),p
metrics=json.loads((B/'evidence/metric_reproduction.json').read_text());assert metrics['max_abs_difference']==0
runtime=list(csv.DictReader((B/'csv/runtime_source_identity.csv').open()));assert all(r['equal']=='True' for r in runtime)
identity=json.loads((B/'evidence/principal_identity.json').read_text());assert identity['runs'] is None and len(identity['attempts'])==1 and identity['read_only']=='on'
for n in ['report_catalog','report_curves','report_metrics','report_consensus','report_representations','report_questions','preflight','architecture','catalog_response']:
 v=json.loads((B/'evidence'/f'{n}.json').read_text());assert 'error' not in v,(n,v.get('error'))
originals=json.loads((B/'evidence/original_verification.json').read_text());assert all(r['exists'] and r['sha256']==r['observed_sha256'] for r in originals)
assert '15 passed' in (B/'evidence/tests_python.txt').read_text()
assert '# pass 15' in (B/'evidence/tests_frontend.txt').read_text()
# Large snapshots are JSON compacted for storage; semantic contents unchanged.
for p in (B/'evidence').glob('*.json'):
 if p.stat().st_size>512*1024:
  v=json.loads(p.read_text());p.write_text(json.dumps(v,separators=(',',':'),ensure_ascii=False)+'\n')
status=subprocess.run(['git','status','--short'],cwd=R,capture_output=True,text=True,check=True).stdout
(B/'evidence/git_status_final.txt').write_text(status)
validation=dict(date_local='2026-11-16 America/Santiago',validated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),required_documents=len(required),sql_files=len(list((B/'sql').glob('*.sql'))),local_links_checked=links,broken_links=errors,source_pairs_equal=len(runtime),metric_difference=0,original_hash_matches=len(originals),tests_python=15,tests_frontend=15,git_head=subprocess.run(['git','rev-parse','HEAD'],cwd=R,capture_output=True,text=True,check=True).stdout.strip(),scope='documentation-only; no browser/HTTP replay; source matches do not certify rendered UI')
(B/'evidence/audit_validation.json').write_text(json.dumps(validation,indent=2)+'\n')
files=[]
for p in sorted(B.rglob('*')):
 if p.is_file() and p.name!='manifest.json':files.append(dict(path=str(p.relative_to(B)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(B/'evidence/manifest.json').write_text(json.dumps(dict(captured_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files),indent=2)+'\n')
print(json.dumps(dict(validation=validation,files=len(files),total_bytes=sum(f['bytes'] for f in files)),indent=2))
