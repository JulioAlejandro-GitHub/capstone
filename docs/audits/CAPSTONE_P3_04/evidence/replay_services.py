"""Invoke only inspected read services in the running backend; no HTTP login, no executor."""
import json,subprocess,pathlib,hashlib
B=pathlib.Path(__file__).resolve().parents[1];ROOT=B.parents[2]
t='87b3eff7-e09a-41c8-945d-bf31b3541adb';u='00b8d407-c672-4b68-9814-53c092d034ba';i='a981125c-a9b6-4bec-9fb7-2fa52b907147'
def run(code,name):
 p=subprocess.run(['docker','exec','-e','PYTHONDONTWRITEBYTECODE=1','-e','PGOPTIONS=-c default_transaction_read_only=on','-e','PYTHONPATH=/app:/app/malaria_dl_local_project','capstone_backend','python','-B','-c',code],capture_output=True,text=True)
 try:v=json.loads(p.stdout) if p.returncode==0 else {'error':p.stderr[-2000:]}
 except ValueError:v={'error':p.stderr[-2000:],'stdout':p.stdout[-1000:]}
 (B/'evidence'/f'{name}.json').write_text(json.dumps(v,indent=2))
sel={'training_run_id':t,'split':'test','evaluation':{'source':'assessment','attempt_id':u,'identity_id':i},'checkpoint_artifact_id':'3bbb3405-1db1-5811-b4b5-f208f9e64503'}
for module in ['catalog','curves','metrics','consensus','representations','questions']:
 req=json.dumps({'module':module,'selections':[sel]})
 run('from app.services.scientific_report import ScientificReportService; from app.schemas.scientific_report import ScientificReportRequest; print(ScientificReportService().read(ScientificReportRequest.model_validate_json('+repr(req)+'),"malaria").model_dump_json())','report_'+module)
run('from app.services.scientific_preflight import ScientificPreflightService; from app.schemas.scientific_preflight import PreflightRequest; print(ScientificPreflightService().read(PreflightRequest.model_validate_json('+repr(json.dumps({'selections':[sel]}))+'),"malaria","CAPSTONE_P3_04").model_dump_json())','preflight')
run('import json;from app.services.model_architecture import ModelArchitectureService;from app.repositories.model_architecture import ModelArchitectureRepository;from fastapi.encoders import jsonable_encoder;print(json.dumps(jsonable_encoder(ModelArchitectureService(ModelArchitectureRepository()).read('+repr(t)+',"malaria"))))','architecture')
print('read service replay complete')

run('from app.services.catalog import CatalogService;from app.repositories.catalog import CatalogRepository;from app.config import get_settings;from fastapi.encoders import jsonable_encoder;import json;print(json.dumps(jsonable_encoder(CatalogService(CatalogRepository(),get_settings()).models("malaria",True,True))))',"catalog_response")
