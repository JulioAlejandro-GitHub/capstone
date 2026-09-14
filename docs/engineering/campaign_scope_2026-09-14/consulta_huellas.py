import json,datetime
from sqlalchemy import text
from src.malaria_dl.data.governed_dataset import dataset_read_connection
out=[]
for observation in ('initial','closing'):
 with dataset_read_connection() as c:
  result={'observation':observation,'utc':str(c.execute(text('select transaction_timestamp()')).scalar_one()),'tables':{}}
  for table in ['runs','artifacts','run_metrics','training_history','classification_reports','confusion_matrices','run_image_predictions','explainability_results','model_versions','run_lineage']:
   ref={'runs':'id','model_versions':'training_run_id','run_lineage':'child_run_id'}.get(table,'run_id')
   # Only opaque row digests leave PostgreSQL. No performance values/predictions fetched.
   q=f"""SELECT count(*) count,encode(sha256(convert_to(coalesce(string_agg(h,'' order by h),''),'UTF8')),'hex') sha256 FROM (SELECT encode(sha256(convert_to(to_jsonb(t)::text,'UTF8')),'hex') h FROM public.{table} t JOIN runs r ON r.id=t.{ref} WHERE NOT EXISTS(SELECT 1 FROM campaign_attempts a WHERE a.training_run_id=r.id)) hashed"""
   result['tables'][table]=dict(c.execute(text(q)).mappings().one())
  out.append(result)
print(json.dumps({'observations':out,'unchanged':out[0]['tables']==out[1]['tables'],'scope':'database rows only; opaque fingerprints, no scientific values fetched; binary files not rehashed'},indent=2))
