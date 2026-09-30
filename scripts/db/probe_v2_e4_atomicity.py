"""Seven real SQL failure boundaries, authenticated runtime, synthetic science."""
import json
from uuid import uuid4, uuid5
from probe_v2_e4_contract import E, RUNTIME, connect, guard, seed
from sqlalchemy import create_engine, event as sql_event
from src.malaria_dl.execution.contracts import ExecutionContext, ExecutionMode
from src.malaria_dl.persistence.result_repository import PostgresResultRepository
from src.malaria_dl.results import ResultService
from src.malaria_dl.results.errors import ResultPersistenceError


def counts(c, run):
    return c.execute('''SELECT
        (SELECT count(*) FROM train_execution_records WHERE run_id=%s) ledger,
        (SELECT count(*) FROM run_threshold_calibration WHERE run_id=%s) calibration,
        (SELECT count(*) FROM evaluations WHERE run_id=%s) evaluations,
        (SELECT count(*) FROM run_clinical_metrics WHERE run_id=%s) metrics''', (run,)*4).fetchone()


def main():
    target = guard()
    results = []
    url = f"postgresql+psycopg://{RUNTIME}@127.0.0.1:{target['host_port']}/{target['database']}"
    with connect(target, role=RUNTIME) as lock:
        lock.execute('SELECT pg_advisory_lock(120994,1)')
        recovery_owner = uuid4()
        lock.execute('UPDATE experiment_execution_gate SET owner=%s,db_pid=pg_backend_pid()', (recovery_owner,))
        lock.execute("SELECT set_config('capstone.execution_token',%s,false)", (str(recovery_owner),))
        for stale in lock.execute("SELECT run_id,owner FROM train_execution_sessions WHERE host='E4-synthetic' AND state='active'").fetchall():
            with lock.transaction():
                lock.execute("SELECT set_config('capstone.train_owner',%s,true)", (str(stale['owner']),))
                lock.execute("UPDATE train_execution_sessions SET state='interrupted' WHERE run_id=%s", (stale['run_id'],))
        for point in ('after_ledger','after_default','create_calibration','create_selected',
                      'metrics_default','metrics_selected','before_commit'):
            with lock.transaction():
                ids, ev, canonical, _, _, _ = seed(lock, ledger=False)
            enabled = [True]
            injected = []
            failures = []
            statements = []
            default_id = uuid5(ev.event_id, 'calibration_default')
            selected_id = uuid5(ev.event_id, 'calibration_selected')

            def factory():
                engine = create_engine(url)

                @sql_event.listens_for(engine, 'before_cursor_execute', retval=True)
                def before(conn, cursor, statement, parameters, context, many):
                    statements.append(statement)
                    if enabled[0]:
                        compiled = getattr(context, 'compiled_parameters', None)
                        params = compiled[0] if compiled else {}
                        hit = ((point == 'create_calibration' and statement.startswith('INSERT INTO run_threshold_calibration'))
                            or (point == 'create_selected' and statement.startswith('INSERT INTO evaluations') and params.get('evaluation_role') == 'calibration_selected')
                            or (point == 'metrics_default' and statement.startswith('INSERT INTO run_clinical_metrics') and params.get('evaluation_id') == default_id)
                            or (point == 'metrics_selected' and statement.startswith('INSERT INTO run_clinical_metrics') and params.get('evaluation_id') == selected_id))
                        if hit:
                            injected.append(point)
                            return 'SELECT 1/0', ()
                    return statement, parameters

                @sql_event.listens_for(engine, 'after_cursor_execute')
                def after(conn, cursor, statement, parameters, context, many):
                    if not enabled[0]: return
                    compiled = getattr(context, 'compiled_parameters', None)
                    params = compiled[0] if compiled else {}
                    hit = ((point == 'after_ledger' and statement.startswith('INSERT INTO train_execution_records'))
                        or (point == 'after_default' and statement.startswith('INSERT INTO evaluations') and params.get('evaluation_role') == 'calibration_default'))
                    if hit:
                        injected.append(point)
                        conn.exec_driver_sql('SELECT 1/0')

                @sql_event.listens_for(engine, 'commit')
                def commit(conn):
                    if enabled[0] and point == 'before_commit':
                        injected.append(point)
                        conn.exec_driver_sql('SELECT 1/0')

                @sql_event.listens_for(engine, 'handle_error')
                def error(ctx):
                    failures.append(dict(sqlstate=getattr(ctx.original_exception, 'sqlstate', None),
                                         message=str(ctx.original_exception)))
                return engine

            context = ExecutionContext(run_id=ids['train'], owner=ids['owner'],
                execution_mode=ExecutionMode.LOCAL_PYTHON, dataset_version_id=ids['version'],
                model_id='custom_cnn', adapter_version='fixture-v1')
            service = ResultService(PostgresResultRepository(execution_token=ids['owner'], engine_factory=factory))
            try:
                service.accept_event(context, ev)
            except ResultPersistenceError:
                pass
            else:
                raise AssertionError('ACCEPTED before successful commit')
            assert injected == [point], (point, injected, failures)
            assert any(f['sqlstate'] == '22012' for f in failures), failures
            assert all(f['sqlstate'] in (None, '22012') for f in failures), failures
            rolled_back = counts(lock, ids['train'])
            assert rolled_back == dict(ledger=0, calibration=0, evaluations=0, metrics=0)
            enabled[0] = False
            assert service.accept_event(context, ev).status.value == 'accepted'
            recovered = ResultService(PostgresResultRepository(execution_token=ids['owner'], engine_factory=factory))
            assert recovered.accept_event(context, ev).status.value == 'duplicate_accepted'
            persisted = counts(lock, ids['train'])
            assert persisted == dict(ledger=1, calibration=1, evaluations=2, metrics=2)
            assert lock.execute("SELECT payload->>'canonical_event' value FROM train_execution_records WHERE event_id=%s", (ev.event_id,)).fetchone()['value'] == canonical
            projected = lock.execute('SELECT id,source_event_id,source_record_key,evaluation_role FROM evaluations WHERE run_id=%s', (ids['train'],)).fetchall()
            assert {r['id'] for r in projected} == {default_id, selected_id}
            assert all(r['source_event_id'] == ev.event_id and r['source_record_key'] == f"{ev.event_id}:{r['evaluation_role']}" for r in projected)
            assert not any('UPDATE runs' in q and 'training_results' in q for q in statements)
            with lock.transaction():
                lock.execute("SELECT set_config('capstone.execution_token',%s,true)", (str(ids['owner']),))
                lock.execute("SELECT set_config('capstone.train_owner',%s,true)", (str(ids['owner']),))
                lock.execute("UPDATE train_execution_sessions SET state='interrupted' WHERE run_id=%s", (ids['train'],))
            results.append(dict(name=point, passed=True, fault_sqlstate='22012', rollback=rolled_back,
                retry=persisted, duplicate_accepted=True, canonical_event_unchanged=True,
                deterministic_role_ids=True, no_legacy_results_update=True))
            (E/'e04_atomicity.json').write_text(json.dumps(results,indent=2)+'\n')
            print(point + ' passed')


if __name__ == '__main__':
    main()
