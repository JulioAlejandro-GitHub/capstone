import json,os
from pathlib import Path
from dotenv import dotenv_values
from sqlalchemy import URL,create_engine,text
config=dotenv_values('.env')
url=URL.create('postgresql+psycopg',username=config['POSTGRES_USER'],password=config['POSTGRES_PASSWORD'],host='127.0.0.1',port=5432,database=config['POSTGRES_DB'])
with create_engine(url).connect() as c:
 records=[json.loads(x) for x in Path('docs/audits/model_contract_01a/historical_11.jsonl').read_text().splitlines()]
 for row in records:
  actual=c.execute(text("SELECT execution_parameters->'runtime_environment' FROM public.runs WHERE id=:id"),{'id':row['id']}).scalar_one()
  assert actual==row['runtime_environment']
  assert actual['tensorflow']==row['tensorflow']
  assert actual['packages']['keras']==row['keras']
 assert len(records)==11
 assert c.execute(text("SELECT md5(string_agg(to_jsonb(r)::text,'' ORDER BY id)) FROM public.runs r")).scalar_one()=='ea2086a62d8817b7d65cc2c31f6ba448'
 print('11/11 historical environments identical; all 23 RUN rows identical except removed columns.')
