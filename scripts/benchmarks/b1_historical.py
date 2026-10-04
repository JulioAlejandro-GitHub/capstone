"""Read-only B1 export. Python standard library only; never imports ML code."""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any

from b1_queries import QUERIES
from b1_discovery import DIAGNOSTICS

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/benchmarks/cpu_historical'
getcontext().prec = 50

def dumps(value: Any) -> str:
    """JSON serializer preserving PostgreSQL decimal values as numeric literals."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return '{' + ','.join(json.dumps(k, ensure_ascii=False) + ':' + dumps(v) for k, v in value.items()) + '}'
    if isinstance(value, list):
        return '[' + ','.join(dumps(v) for v in value) + ']'
    return json.dumps(value, ensure_ascii=False)

def extract() -> dict[str, list[dict[str, Any]]]:
    sql = ['BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;', "SET LOCAL TIME ZONE 'UTC';", "SET LOCAL statement_timeout='120s';"]
    for q in QUERIES:
        sql.append("SELECT json_build_object('id','" + q['id'] + "','rows',coalesce(json_agg(q),'[]'::json)) FROM (" + q['sql'] + ') q;')
    for q in DIAGNOSTICS:
        sql.append("SELECT json_build_object('id','" + q['id'] + "','rows',json_build_array(json_build_object('result_rows',count(*)))) FROM (" + q['sql'] + ') q;')
    sql.append('ROLLBACK;')
    command = ['docker', 'compose', 'exec', '-T', 'db', 'sh', '-c',
               'PGOPTIONS="-c default_transaction_read_only=on" psql -X -qAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"']
    result = subprocess.run(command, input='\n'.join(sql), text=True, capture_output=True, cwd=ROOT, check=True)
    decoder = json.JSONDecoder(parse_float=Decimal)
    remaining = result.stdout.strip()
    rows = []
    while remaining:
        row, end = decoder.raw_decode(remaining)
        rows.append(row)
        remaining = remaining[end:].lstrip()
    assert len(rows) == len(QUERIES) + len(DIAGNOSTICS)
    return {row['id']: row['rows'] for row in rows}

def write_csv(name: str, rows: list[dict[str, Any]]) -> None:
    assert rows, name
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with (OUT / name).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: dumps(v) if isinstance(v, (dict, list)) else v for k,v in row.items()})

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', type=Path, help='Guardar copia temporal de SELECT para inspección/reporte offline')
    parser.add_argument('--from-snapshot', type=Path, help='Regenerar documentos desde SELECT ya capturados, sin DB')
    args = parser.parse_args()
    data = json.loads(args.from_snapshot.read_text(), parse_float=Decimal) if args.from_snapshot else extract()
    if args.snapshot:
        args.snapshot.write_text(dumps(data))
    print(dumps({k: len(v) for k,v in data.items()}))
    from b1_report import generate
    generate(data)

if __name__ == '__main__':
    main()
