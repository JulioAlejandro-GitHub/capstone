"""Producer preflight: real resolver/TRAIN writer vs the fixed v2 target.

No training, campaign or dataset change. All synthetic rows roll back. This is
an incompatibility diagnostic, not completion of the context producer.
"""
import json
import os
import shutil
import sys
from pathlib import Path
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'malaria_dl_local_project')]
E=ROOT/'docs/audits/e10_10_5e4_evidence/integration'
E.mkdir(parents=True,exist_ok=True)
for name in ('target.json','private_paths.json'):
    if not (E/name).exists(): shutil.copy2(E.parent/'route_a'/name,E/name)
os.environ['PGV2_EVIDENCE_DIR']=str(E)
os.environ['PGPASSFILE']=json.loads((E/'private_paths.json').read_text())['pgpass']
from verify_v2_route_a import guard
from test_v2_route_a_server import fixture,insert
from psycopg.rows import dict_row
import psycopg
from sqlalchemy import create_engine,text
from sqlalchemy.exc import IntegrityError
from src.malaria_dl.models.configuration import resolve_config
from src.malaria_dl.evaluation.threshold_calibration import find_threshold_for_target_recall
from src.malaria_dl.execution.repository import ExecutionRepository


def main():
    t=guard(); rows=[]
    url=f"postgresql+psycopg://capstone_v2_runtime@127.0.0.1:{t['host_port']}/{t['database']}"
    engine=create_engine(url)
    try:
        for target in (.98,.8,.99):
            configuration=resolve_config('custom_cnn',overrides={'execution':{'target_recall':target}})
            science=find_threshold_for_target_recall([0,0,1,1],[.1,.4,.6,.9],
                target_recall=configuration['resolved']['execution']['target_recall'])
            with engine.connect() as c:
                transaction=c.begin()
                try:
                    assert c.execute(text('SELECT session_user')).scalar_one()=='capstone_v2_runtime'
                    class FixtureSQL:
                        def execute(self,query,params=None):
                            cursor=c.connection.driver_connection.cursor(row_factory=dict_row)
                            cursor.execute(query,params)
                            return cursor
                    sql=FixtureSQL()
                    ids=fixture(sql)
                    insert(sql,'models',dict(id=uuid4(),name='custom_cnn',model_type='custom_cnn'))
                    run=uuid4()
                    # Invoke the actual TRAIN writer; the SQL check can reject before calibration.
                    try:
                        ExecutionRepository._create_run(c,str(run),configuration,
                            {'dataset_version_id':str(ids['version'])},{'synthetic_preflight':True})
                    except IntegrityError as exc:
                        assert target != .98
                        assert exc.orig.sqlstate == '23514'
                        assert exc.orig.diag.constraint_name == 'v2_run_configurations_check_d6094850fee4'
                        rows.append(dict(requested_target=target,resolver_accepted=True,
                            calibration_producer_target=science['target_recall'],
                            train_writer_accepted=False,sqlstate=exc.orig.sqlstate,
                            constraint=exc.orig.diag.constraint_name,
                            calibration_insert_attempted=False))
                        continue
                    configured=c.execute(text('SELECT clinical_target_recall FROM run_configurations WHERE run_id=:id'),{'id':run}).scalar_one()
                    assert float(configured)==target==science['target_recall']
                    result=dict(requested_target=target,resolver_accepted=True,train_writer_accepted=True,
                        typed_configuration_target=float(configured),calibration_producer_target=science['target_recall'],
                        threshold_selected=science['threshold_selected'],calibration_split=science['calibration_split'])
                    try:
                        insert(sql,'run_threshold_calibration',dict(run_id=run,
                            threshold_selected=science['threshold_selected'],default_threshold=science['default_threshold'],
                            target_recall=science['target_recall'],calibration_split=science['calibration_split'],
                            default_evaluation_id=uuid4(),selected_evaluation_id=uuid4()))
                    except psycopg.Error as exc:
                        assert target!=.98 and exc.sqlstate=='23514' and exc.diag.constraint_name=='ck_v2_calibration_val'
                        result.update(calibration_insert_accepted=False,sqlstate=exc.sqlstate,constraint=exc.diag.constraint_name)
                    else:
                        assert target==.98
                        result.update(calibration_insert_accepted=True,
                            control_scope='INSERT-only control with deferred member FKs; rolled back, not a complete pair')
                    rows.append(result)
                finally: transaction.rollback()
        report=dict(status='BLOCKED_E05',scope='Real configuration resolver + TRAIN snapshot writer + calibration calculator, no training',
            all_probe_rows_rolled_back=True,results=rows,
            cause="Both typed TRAIN configuration and calibration require target_recall=0.98; the real resolver and calibration calculator accept other explicit targets",
            context_producer_completed=False,gate_e='BLOCKED_NOT_REQUESTED')
        (E/'e05_target_contract.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
    finally: engine.dispose()


if __name__=='__main__':main()
