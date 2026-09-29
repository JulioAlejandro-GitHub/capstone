"""Read-only diagnostics after D preflight block; no adoption or repairs."""
import hashlib
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from adoption_v2.core import contract,table_digest,digest
from adoption_v2.preflight import preflight, schema_signature
from adoption_v2.execute import catalog_snapshot,certified_catalog
import psycopg
from psycopg.rows import dict_row
from psycopg.types.string import TextLoader
E=ROOT/'docs/audits/e10_10_5d_evidence'
t=json.loads((E/'target.json').read_text());private=Path(json.loads((E/'private_location.json').read_text())['directory'])
secret=(private/'container.env').read_text().splitlines()[0].split('=',1)[1]
with psycopg.connect(host='127.0.0.1',port=t['host_port'],user=t['migration_role'],password=secret,dbname=t['database'],row_factory=dict_row) as c:
 c.adapters.register_loader('uuid',TextLoader)
 c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
 native=catalog_snapshot(c);expected=certified_catalog()
 snapshot={'catalog':{k:c.execute(q).fetchall() for k,q in contract()['queries'].items()},'rows':{k:c.execute('SELECT * FROM public."'+k+'"').fetchall() for k in contract()['tables']}}
 inventory={k:{"count":len(v),"sha256":table_digest(v)} for k,v in snapshot["rows"].items()}
 observed=schema_signature(snapshot["catalog"]); wanted=contract()["expected_schema"]
 diff={k:{"observed_only":[r for r in observed[k] if r not in wanted[k]],"expected_only":[r for r in wanted[k] if r not in observed[k]]} for k in observed if observed[k]!=wanted[k]}
 (E/"restored_schema_diff.json").write_text(json.dumps(diff,indent=2)+"\n")
 identity=c.execute("SELECT current_database() database,(SELECT system_identifier::text FROM pg_control_system()) system_identifier,current_setting('server_version_num') version,current_setting('transaction_read_only') read_only").fetchone()
 sequences={s['name']:c.execute('SELECT last_value,is_called FROM public."'+s['name']+'"').fetchone() for s in native['sequences']}
 c.rollback()
for name,value in [('restored_legacy_catalog.json',native),('reference_inventory.json',inventory),('isolated_identity.json',identity),('sequence_difference.json',{'observed':native['sequences'],'route_a':expected['sequences'],'values':sequences}),('preflight_result.json',{'legacy_data_preflight':'BLOCKED: LEGACY_SCHEMA_DRIFT','legacy_schema_diff':'restored_schema_diff.json','inventory_sha256':digest(inventory),'adoption_guard':'BLOCKED: LEGACY_SEQUENCE_DRIFT','adapter_applied':False,'revision':snapshot['rows']['alembic_version'],'other_requirements':'not certified'})]:
 (E/name).write_text(json.dumps(value,indent=2,default=str)+'\n')
(E/'isolated_backup.json').write_text(json.dumps({'path':str(private/'isolated.dump'),'sha256':hashlib.sha256((private/'isolated.dump').read_bytes()).hexdigest(),'bytes':(private/'isolated.dump').stat().st_size},indent=2)+'\n')
print(json.dumps({'identity':identity,'sequence_difference':native['sequences']!=expected['sequences'],'preflight':'BLOCKED','adapter_applied':False}))
