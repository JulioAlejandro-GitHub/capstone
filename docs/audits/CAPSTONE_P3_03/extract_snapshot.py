"""Repeat the authorized audit extraction. SELECT-only PostgreSQL, outputs here.
Run from repository root: python3 docs/audits/CAPSTONE_P3_03/extract_snapshot.py
Requires the existing capstone_db / capstone_backend containers; never starts services.
"""
from pathlib import Path
import subprocess,json,datetime
B=Path(__file__).resolve().parent
PSQL=['docker','exec','-i','capstone_db','sh','-lc',
      'PGOPTIONS="-c default_transaction_read_only=on -c statement_timeout=60000" psql -X -qAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"']
for path in sorted(B.glob('*.sql')):
    r=subprocess.run(PSQL,input=path.read_text(),capture_output=True,text=True,check=True)
    # All delivered SQL files emit a single JSON result in a READ ONLY transaction.
    json.loads(r.stdout)
    path.with_suffix('.json').write_text(r.stdout)
code="from app.services.training_summaries import list_training_summaries; print(list_training_summaries('malaria',100).model_dump_json())"
r=subprocess.run(['docker','exec','-e','PYTHONDONTWRITEBYTECODE=1','-e','PGOPTIONS=-c default_transaction_read_only=on','-e','PYTHONPATH=/app:/app/malaria_dl_local_project','capstone_backend','python','-B','-c',code],capture_output=True,text=True,check=True)
json.loads(r.stdout);(B/'training_summaries_response.json').write_text(r.stdout)
print('Read-only extraction complete:',datetime.datetime.now(datetime.timezone.utc).isoformat())
