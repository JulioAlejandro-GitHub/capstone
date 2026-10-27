"""Read-only row fingerprints for auditing the authorized test clone against its source."""
import argparse
from datetime import datetime, timezone
import json
import subprocess
from pathlib import Path

TABLES = ('models','runs','artifacts','model_versions','run_configurations','train_execution_sessions',
          'train_execution_records','training_history','assessment_identities','assessment_attempts',
          'assessment_results','assessment_artifacts')
parser = argparse.ArgumentParser()
parser.add_argument('--container', required=True)
parser.add_argument('--database')
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
query = '\nUNION ALL\n'.join(
    f"SELECT '{table}',count(*)::text,coalesce(md5(string_agg(md5(to_jsonb(t)::text),'' ORDER BY md5(to_jsonb(t)::text))),'empty') FROM public.{table} t"
    for table in TABLES
) + ';'
if args.database:
    command = ['docker','exec','-i','-e','PGOPTIONS=-c default_transaction_read_only=on',args.container,
               'psql','-X','-At','-v','ON_ERROR_STOP=1','-U','postgres','-d',args.database]
else:
    command = ['docker','exec','-i',args.container,'sh','-c',
               'PGOPTIONS="-c default_transaction_read_only=on" psql -X -At -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"']
result = subprocess.run(command,input=query,text=True,capture_output=True,check=True)
rows = [line.split('|') for line in result.stdout.splitlines()]
args.output.write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'container':args.container,
 'database':args.database or 'configured_source',
 'tables':{name:{'count':int(count),'row_fingerprint_md5':fingerprint} for name,count,fingerprint in rows}},indent=2)+'\n')
