"""Real commit failures, all pair insertion orders and nullable uniqueness."""
import itertools
import json
from dataclasses import replace
from uuid import uuid4
import psycopg
from probe_v2_e4_contract import E, RUNTIME, connect, guard, seed, canonical_event
from test_v2_route_a_server import insert, metric


def project(c, member, event):
    raw = event.to_dict()['payload']['result']['result'][
        'default_threshold_metrics' if member['evaluation_role']=='calibration_default' else 'selected_metrics']
    insert(c, 'evaluations', member)
    metric(c, member, **{k:raw[k] for k in ('tn','fp','fn','tp','roc_auc_parasitized','pr_auc_parasitized')},
           auc_unavailability_reason=None)


def main():
    t=guard(); results=[]
    def save():
        (E/'e04_edges.json').write_text(json.dumps(results,indent=2)+'\n')
    with connect(t, role=RUNTIME) as c:
        for order in itertools.permutations('cds'):
            c.execute('BEGIN')
            try:
                ids,ev,_,d,s,cal=seed(c)
                for item in order:
                    if item=='c': insert(c,'run_threshold_calibration',cal)
                    else: project(c,d if item=='d' else s,ev)
                c.execute('SET CONSTRAINTS ALL IMMEDIATE')
                results.append(dict(name='order_'+''.join(order),passed=True))
                save()
            finally: c.execute('ROLLBACK')
        cases={
            'commit_orphan_default':('P0001','E04_PAIR_REQUIRED'),
            'commit_orphan_selected':('23503','v2_evaluations_foreign_0baa7d166e2f'),
            'commit_calibration_without_members':('23503','foreign key'),
            'contract_duplicate_new_event':('23505','uq_e04_contract_role'),
            'contract_duplicate_null_model':('23505','uq_e04_contract_role'),
            'event_test_origin':('P0001','E04_EVENT_PROVENANCE'),
            'event_wrong_kind':('P0001','E04_EVENT_PROVENANCE'),
            'event_missing_calibration':('P0001','E04_EVENT_PROVENANCE'),
            'metric_payload_conflict':('P0001','E04_METRIC_PROVENANCE'),
            'context_missing':('P0001','E04_CONTEXT_PROVENANCE'),
        }
        for name,(state,marker) in cases.items():
            c.execute('BEGIN'); boundary=False
            try:
                ids,ev,_,d,s,cal=seed(c,ledger=False)
                payload=ev.to_dict()['payload']
                if name=='event_test_origin': payload['result']['result']['calibration_split']='test'
                if name=='event_missing_calibration': payload['result'].pop('result')
                if name=='metric_payload_conflict': payload['result']['result']['selected_metrics']['tn']+=1
                if name.startswith('event_') or name=='metric_payload_conflict':
                    from src.malaria_dl.execution.contracts import RunEventType
                    changed=replace(ev,payload=payload,event_type=RunEventType.HEARTBEAT if name=='event_wrong_kind' else ev.event_type)
                else: changed=ev
                insert(c,'train_execution_records',dict(run_id=ev.run_id,kind='e10_event',phase='run_event_v1',
                    record_key=str(ev.event_id),event_id=ev.event_id,event_sequence=1,
                    payload={'canonical_event':canonical_event(changed)}))
                if name=='context_missing':
                    c.execute("UPDATE runs SET execution_parameters=execution_parameters-'e10_v2_evaluation_context_v1' WHERE id=%s",(ev.run_id,))
                if name=='contract_duplicate_null_model':
                    d['model_version_id']=s['model_version_id']=cal['model_version_id']=None
                    c.execute("UPDATE runs SET execution_parameters=jsonb_set(execution_parameters,'{e10_v2_evaluation_context_v1}',(execution_parameters->'e10_v2_evaluation_context_v1')-'model_version_id') WHERE id=%s",(ev.run_id,))
                if name=='commit_orphan_default': project(c,d,ev)
                elif name=='commit_orphan_selected': project(c,s,ev)
                elif name=='commit_calibration_without_members': insert(c,'run_threshold_calibration',cal)
                else:
                    project(c,d,ev); project(c,s,ev); insert(c,'run_threshold_calibration',cal)
                    if name.startswith('contract_duplicate_'):
                        other=uuid4()
                        project(c,dict(s,id=uuid4(),source_event_id=other,event_key=str(other),
                                       source_record_key=str(other)+':calibration_selected',threshold_used=.7),ev)
                boundary=True
                c.execute('COMMIT')
            except psycopg.Error as exc:
                assert exc.sqlstate==state and marker in str(exc),(name,str(exc))
                c.execute('ROLLBACK')
                assert c.execute('SELECT count(*) n FROM runs WHERE id=%s',(ids['train'],)).fetchone()['n']==0
                results.append(dict(name=name,passed=True,sqlstate=exc.sqlstate,marker=marker,
                                    failed_at_commit=boundary,entire_fixture_rolled_back=True))
                save()
            else:
                raise AssertionError(name+' accepted')
        index=c.execute("SELECT indnullsnotdistinct FROM pg_index WHERE indexrelid='uq_e04_contract_role'::regclass").fetchone()
        assert index['indnullsnotdistinct']
        results.append(dict(name='native_nulls_not_distinct',passed=True)); save()
    print(str(len(results))+' edge checks passed')


if __name__=='__main__': main()
