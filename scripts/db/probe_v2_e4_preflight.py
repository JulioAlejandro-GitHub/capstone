"""Authenticated runtime rejects tampered E-04 objects in the restored test copy."""
import json
from probe_v2_e4_contract import E,connect,guard,RUNTIME
from sqlalchemy import create_engine
from src.malaria_dl.execution.schema import require_e10_schema,E10SchemaNotReady
from v2_catalog_probe import snapshot


def main():
    main_target=guard()
    t=json.loads((E/'restore_target.json').read_text())
    assert t['container_id']==main_target['container_id'] and t['database']!=main_target['database']
    expected=json.loads((E/'installed_catalog.json').read_text())
    url=f"postgresql+psycopg://{RUNTIME}@127.0.0.1:{t['host_port']}/{t['database']}"
    engine=create_engine(url);results=[]
    try:
        with connect(t) as admin:
            assert snapshot(admin)==expected
            fn=admin.execute("SELECT pg_get_functiondef('e04_legacy_admission()'::regprocedure) sql").fetchone()['sql']
            idx=admin.execute("SELECT pg_get_indexdef('uq_e04_event_role'::regclass) sql").fetchone()['sql']
            ck=admin.execute("SELECT pg_get_constraintdef(oid) sql FROM pg_constraint WHERE conrelid='evaluations'::regclass AND conname='ck_e04_selected_source'").fetchone()['sql']
            cases=[
                ('trigger','ALTER TABLE evaluations DISABLE TRIGGER e04_evaluation_complete',
                 'ALTER TABLE evaluations ENABLE TRIGGER e04_evaluation_complete','v2_trigger_contract'),
                ('unique_index','DROP INDEX uq_e04_event_role',idx,'v2_calibration_uniqueness_contract'),
                ('selected_check','ALTER TABLE evaluations DROP CONSTRAINT ck_e04_selected_source',
                 'ALTER TABLE evaluations ADD CONSTRAINT ck_e04_selected_source '+ck,'v2_evaluation_contract'),
                ('authority_function',"CREATE OR REPLACE FUNCTION e04_legacy_admission() RETURNS trigger LANGUAGE plpgsql SET search_path=public,pg_catalog AS $$ BEGIN RETURN NEW; END $$",fn,'v2_function_contract')]
            for name,mutation,restore,marker in cases:
                try:
                    admin.execute(mutation)
                    with engine.connect() as runtime:
                        try: require_e10_schema(runtime)
                        except E10SchemaNotReady as exc:
                            assert marker in exc.missing,(name,exc.missing)
                        else: raise AssertionError(name+' was accepted')
                    results.append(dict(name=name,passed=True,missing=marker))
                finally: admin.execute(restore)
                assert snapshot(admin)==expected
            with engine.connect() as runtime:
                assert require_e10_schema(runtime)['revision']=='pg_v2_baseline'
            results.append(dict(name='restored_contract_accepted',passed=True))
        (E/'e04_runtime_preflight.json').write_text(json.dumps(results,indent=2)+'\n')
    finally: engine.dispose()
    print('E-04 runtime tamper rejection and restoration passed')


if __name__=='__main__': main()
