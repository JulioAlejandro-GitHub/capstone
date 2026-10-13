"""Synthetic C2.12 integration, invoked only inside the existing backend image.

No TRAIN entrypoint, model inference, dataset loader or TEST population is used.
All services and PostgreSQL projections are real, using fresh root transactions.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import traceback
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import create_engine, text, event as sqlalchemy_event
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from src.malaria_dl.campaigns.contracts import canonical, digest, expand_matrix, CampaignError
from src.malaria_dl.campaigns.repository import CampaignRepository
from src.malaria_dl.execution.repository import ExecutionRepository
from src.malaria_dl.execution.schema import require_e10_schema
from src.malaria_dl.execution.contracts import ExecutionContext, ExecutionMode, RunEventType as E
from src.malaria_dl.execution.emitter import RunEventEmitter
from src.malaria_dl.execution.reporters.docker import DockerRunReporter
from src.malaria_dl.persistence.result_repository import PostgresResultRepository
from src.malaria_dl.results.service import ResultService
from src.malaria_dl.results.errors import EventIdConflict, SequenceGap, SequenceConflict, ResultPersistenceError
from src.malaria_dl.evaluation.calibration_controller import CalibrationController
from src.malaria_dl.evaluation.validation import evaluate_validation_predictions
from src.malaria_dl.evaluation.threshold_calibration import find_threshold_for_target_recall
from src.malaria_dl.models.scientific_parameters import compare_runs, effective_values
from test_campaigns_e4 import dataset, protocol, request


def main() -> None:
    name = os.environ['C212_DATABASE']
    nonce = UUID(os.environ['C212_RUN_ID'])
    assert name == 'capstone_c212_' + nonce.hex and name != 'malaria_experiments'
    base = make_url(os.environ['DATABASE_URL'])
    assert base.host == 'db' and base.username == 'capstone_v2_runtime'
    url = base.set(database=name)
    def factory():
        created = create_engine(url, hide_parameters=True,
                                connect_args={'application_name': 'C212_' + nonce.hex})
        def error_evidence(context) -> None:
            original = context.original_exception
            print(json.dumps({'sql_error': getattr(original, 'sqlstate', None),
                'message': getattr(getattr(original, 'diag', None), 'message_primary', None)}))
        sqlalchemy_event.listen(created, 'handle_error', error_evidence)
        def calibration_evidence(connection) -> None:
            differences = connection.execute(text("""SELECT e.evaluation_role,k,
                to_jsonb(m)->k AS stored,
                (t.payload->>'canonical_event')::jsonb #> ARRAY['payload','result','result',
                 CASE WHEN e.evaluation_role='calibration_default' THEN 'default_threshold_metrics' ELSE 'selected_metrics' END,k] AS emitted
                FROM evaluations e JOIN run_clinical_metrics m ON m.evaluation_id=e.id
                JOIN train_execution_records t ON t.event_id=e.source_event_id
                CROSS JOIN unnest(ARRAY['roc_auc_parasitized','pr_auc_parasitized']) k
                WHERE e.evaluation_role IN ('calibration_default','calibration_selected')
                AND to_jsonb(m)->k IS DISTINCT FROM
                (t.payload->>'canonical_event')::jsonb #> ARRAY['payload','result','result',
                 CASE WHEN e.evaluation_role='calibration_default' THEN 'default_threshold_metrics' ELSE 'selected_metrics' END,k]
            """)).mappings().all()
            if differences:
                print(json.dumps({'metric_provenance_differences': [dict(r) for r in differences]},default=str))
        sqlalchemy_event.listen(created, 'commit', calibration_evidence)
        return created
    engine = factory()
    cases: list[str] = []
    evidence: dict = {'database': name, 'cases': cases, 'runs': []}
    token = uuid4()
    @contextmanager
    def scope(readonly: bool = False):
        with engine.begin() as c:
            if readonly:
                c.execute(text('SET TRANSACTION READ ONLY'))
            c.execute(text("SELECT set_config('capstone.execution_token',:token,true)"), {'token': str(token)})
            yield c
    with engine.connect() as keeper:
        assert keeper.execute(text('SELECT current_database()')).scalar_one() == name
        identity = keeper.execute(text("SELECT oid,pg_get_userbyid(datdba) AS owner,shobj_description(oid,'pg_database') AS marker FROM pg_database WHERE datname=current_database()")).mappings().one()
        assert identity['oid'] == int(os.environ['C212_DATABASE_OID'])
        assert identity['owner'] == 'capstone_v2_migrator' and identity['marker'] == 'C2.12.2:' + str(nonce)
        evidence['schema'] = require_e10_schema(keeper)
        assert keeper.execute(text('SELECT count(*) FROM runs')).scalar_one() == 0
        keeper.execute(text('SELECT pg_advisory_lock(120994,1)'))
        keeper.execute(text('UPDATE experiment_execution_gate SET owner=:token,db_pid=pg_backend_pid()'), {'token': token})
        keeper.commit()
        cases.append('isolated_identity_empty_v2_real_guards')
        d = dataset()
        # The existing planning contract requires all three declared roles.
        # This is synthetic metadata only: no TEST rows/files/scores are created.
        d['counts'] = {'train': 4, 'val': 4, 'test': 1}
        evidence_id = uuid4()
        with scope() as c:
            c.execute(text("""INSERT INTO dataset_versions(id,name,semantic_version,grouping_strategy,grouping_field,
                stratification_strategy,split_algorithm,split_algorithm_version,random_seed,
                target_train_ratio,target_val_ratio,target_test_ratio,positive_class)
                VALUES(:id,'C212 synthetic','0.0.0','synthetic','patient','synthetic','synthetic','1',11,.5,.5,0,'parasitized')"""), {'id': d['dataset_version_id']})
            c.execute(text("""INSERT INTO audit_events(id,event_type,action,resource_type,resource_id,request_method,
                request_path,correlation_id,after_state,metadata,success)
                VALUES(:id,'ml.dataset_verification','verify','dataset_version',:dataset,'TEST','synthetic',:correlation,
                CAST(:payload AS jsonb),'{}',true)"""), dict(id=evidence_id, dataset=d['dataset_version_id'],
                    correlation=str(evidence_id), payload=canonical({'dataset_version_id': d['dataset_version_id'],
                        'snapshot': d, 'integrity_status': 'verified'})))
        snapshots = {}
        with tempfile.TemporaryDirectory(prefix='c212_synthetic_') as directory:
            for label, enabled, labels, scores, specificity in (
                ('A', False, [0,0,1,1], [.1,.2,.3,.4], .5),
                ('B', True, [0,0,1,1], [.1,.2,.3,.4], .5),
                ('C', True, [0,0,1,1], [.8,.8,.2,.2], 1.0),
            ):
                p = protocol()
                p['calibration']['algorithm'] = 'threshold_grid' if enabled else 'none'
                p['sensitivity_target'] = 1.0
                p['specificity_minimum'] = specificity
                req = request([11])
                req.update(models=['custom_cnn'], optimizers=['adam'])
                matrix = expand_matrix(req, p, frozen=True, dataset=d)
                contract = dict(version='campaign_contract_v1', name='C212 '+label, purpose='synthetic verification',
                    experiment_id=None, dataset=d, dataset_evidence_id=str(evidence_id), requested=req, protocol=p,
                    environment={'source_sha256': 'e'*64, 'tensorflow': 'not-executed',
                        'determinism_environment': {}, 'python': 'synthetic', 'packages': {'synthetic': '1'}}, matrix=matrix)
                campaign = CampaignRepository(scope).create_frozen(uuid4(), contract, 'C212 synthetic')
                repo = ExecutionRepository(scope)
                session = repo.claim(campaign['id'], uuid4(), 'synthetic', os.getpid(), Path(directory))
                run, owner = UUID(str(session['run_id'])), UUID(str(session['owner']))
                config = session['configuration']
                assert config['resolved']['execution']['calibrate_threshold'] is enabled
                assert config['resolved']['execution']['target_recall'] == 1.0
                assert config['resolved']['execution']['seed'] == 11
                assert config['resolved']['selection']['threshold'] == .5
                with scope(True) as c:
                    row = c.execute(text('SELECT * FROM run_configurations WHERE run_id=:run'), {'run': run}).mappings().one()
                    assert row['provenance_snapshot'] == config
                    assert row['extension_configuration'] == config['resolved']
                    assert row['configuration_hash'] == digest(config['resolved'])
                    assert c.execute(text('SELECT campaign_id FROM runs WHERE id=:run'), {'run': run}).scalar_one() == campaign['id']
                snapshots[str(run)] = row['extension_configuration']
                artifact = Path(directory) / (label + '.synthetic')
                artifact.write_bytes(b'synthetic checkpoint identity only; never loaded as a model')
                samples = [{'sample': f'val/synthetic_{i}', 'label': y, 'score': v}
                           for i, (y, v) in enumerate(zip(labels, scores, strict=True))]
                repo.put(run, owner, 'epoch', 'base', '1', {'epoch': 1})
                repo.put(run, owner, 'selection', 'base', '1', {'selected_epoch': 1, 'threshold': .5})
                repo.put(run, owner, 'artifact', 'base', '1', dict(epoch=1, phase='base', version_id=str(uuid4()),
                    path=str(artifact), sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(), bytes=artifact.stat().st_size))
                repo.put(run, owner, 'predictions', 'base', '1', {'epoch': 1, 'role': 'val', 'samples': samples})
                bound = repo.bind_evaluation_context(run, owner, 1)
                member = campaign['members'][0]
                ctx = ExecutionContext(run_id=run, owner=owner, attempt_id=UUID(str(session['attempt_id'])),
                    execution_mode=ExecutionMode.DOCKER, dataset_version_id=UUID(d['dataset_version_id']),
                    model_id=config['model_id'], adapter_version=config['adapter_version'],
                    campaign_id=campaign['id'], member_id=member['id'],
                    configuration_hash=member['configuration_hash'], contract_hash=campaign['contract_hash'])
                service = ResultService(PostgresResultRepository(execution_token=token, engine_factory=factory))
                emitter = RunEventEmitter(DockerRunReporter(ctx, service), run_id=run, attempt_id=ctx.attempt_id)
                first = emitter.emit(E.EPOCH_COMPLETED, {'epoch': 1, 'synthetic': True})
                assert service.accept_event(ctx, first).status.value == 'duplicate_accepted'
                for event, error in ((replace(first,payload={'conflict': True}),EventIdConflict),
                                     (replace(first,event_id=uuid4()),SequenceConflict),
                                     (replace(first,event_id=uuid4(),sequence=4),SequenceGap)):
                    try:
                        service.accept_event(ctx,event)
                    except error:
                        pass
                    else:
                        raise AssertionError('Event conflict accepted')
                controller = CalibrationController(config)
                calibration = controller.calibrate(labels, scores)
                if enabled:
                    direct = find_threshold_for_target_recall(labels, scores, target_recall=1., min_specificity=specificity,beta=2)
                    assert {k:v for k,v in calibration.items() if k!='created_at'} == {k:v for k,v in direct.items() if k!='created_at'}
                else:
                    assert calibration == {'enabled': False, 'threshold': .5}
                if label == 'C':
                    assert calibration['warning'] and calibration['min_specificity_satisfied'] is False
                payload = {'result': calibration, 'checkpoint_epoch': 1, 'samples': samples}
                repo.put(run, owner, 'calibration', 'val', 'selected', payload)
                if enabled:
                    event = emitter.emit(E.CALIBRATION_COMPLETED, {'result': {'split':'val',
                        'checkpoint_epoch':1,'result':calibration},
                        'record': {'kind':'calibration','phase':'val','record_key':'selected'}})
                    assert service.accept_event(ctx, event).status.value == 'duplicate_accepted'
                evaluation = evaluate_validation_predictions(labels, scores, controller.threshold(calibration))
                final = emitter.emit(E.EVALUATION_COMPLETED, evaluation.to_dict())
                assert service.accept_event(ctx, final).status.value == 'duplicate_accepted'
                with scope(True) as c:
                    rows = c.execute(text("SELECT e.*,m.tn,m.fp,m.fn,m.tp FROM evaluations e JOIN run_clinical_metrics m ON m.evaluation_id=e.id WHERE e.training_run_id=:run ORDER BY e.evaluation_role"), {'run':run}).mappings().all()
                    assert len(rows) == (3 if enabled else 1)
                    saved = next(r for r in rows if r['evaluation_role']=='training_validation_final')
                    # numeric column returns Decimal; compare as float to avoid the
                    # Decimal('0.3') != 0.3 binary-representation gotcha.
                    assert float(saved['threshold_used']) == evaluation.threshold.value
                    assert saved['threshold_source'] == evaluation.threshold.source
                    assert str(saved['checkpoint_artifact_id']) == bound['checkpoint_artifact_id']
                    assert [saved[k] for k in ('tn','fp','fn','tp')] == [getattr(evaluation.confusion_matrix,k) for k in ('tn','fp','fn','tp')]
                    ledger = c.execute(text("SELECT payload->>'canonical_event' FROM train_execution_records WHERE run_id=:run AND event_id IS NOT NULL ORDER BY event_sequence"), {'run':run}).scalars().all()
                    assert len(ledger) == (3 if enabled else 2)
                    assert [json.loads(x)['sequence'] for x in ledger] == list(range(1,len(ledger)+1))
                    calibration_row = c.execute(text('SELECT * FROM run_threshold_calibration WHERE run_id=:run'), {'run':run}).mappings().one_or_none()
                    assert (calibration_row is not None) is enabled
                # Real SQL failure after append: another final evaluation violates
                # the real uniqueness constraint. Root rollback must remove its event.
                bad = replace(final,event_id=uuid4(),sequence=final.sequence+1)
                try:
                    service.accept_event(ctx,bad)
                except ResultPersistenceError:
                    pass
                else:
                    raise AssertionError('SQL projection failure returned success')
                with scope(True) as c:
                    assert c.execute(text('SELECT count(*) FROM train_execution_records WHERE event_id=:id'), {'id':bad.event_id}).scalar_one() == 0
                    assert c.execute(text('SELECT count(*) FROM evaluations WHERE training_run_id=:run'), {'run':run}).scalar_one() == len(rows)
                recovered = emitter.emit(E.PHASE_COMPLETED, {'synthetic_verification': 'finished'})
                assert recovered.sequence == bad.sequence
                evidence['runs'].append(dict(scenario=label, run_id=str(run), campaign_id=str(campaign['id']),
                    configuration_hash=row['configuration_hash'], configuration=config, calibration=calibration,
                    evaluations=[dict(r) for r in rows], events=[json.loads(x) for x in ledger],
                    calibration_summary=dict(calibration_row) if calibration_row else None,
                    sql_failure_event_absent=str(bad.event_id), recovered_sequence=recovered.sequence))
                cases.extend([label+'_campaign_snapshot_hash', label+'_controller_projection',
                              label+'_duplicate_conflicts_sequences',label+'_sql_failure_atomicity_recovery'])
                # No TRAIN occurred: close the synthetic reservation as failed,
                # never claim technical training completion or clinical success.
                repo.finish(run, owner, 'failed', cause='SYNTHETIC_VERIFICATION_ONLY')
        comparison = compare_runs(snapshots)
        a,b = list(snapshots)[:2]
        assert comparison['execution.calibrate_threshold'][a]['value'] is False
        assert comparison['execution.calibrate_threshold'][b]['value'] is True
        assert comparison['execution.seed'][a]['value'] == comparison['execution.seed'][b]['value'] == 11
        old = {'legacy': {'unknown':7}}
        prior = deepcopy(old)
        history = compare_runs({a:snapshots[a], 'synthetic_historical':old})
        assert not history['execution.target_recall']['synthetic_historical']['present']
        assert history['legacy.unknown']['synthetic_historical']['governed'] is False
        assert old == prior and not effective_values({})['execution.seed']['present']
        evidence['comparison'] = comparison
        cases.append('compare_effective_equal_different_missing_unknown_no_defaults')
        bad_req = request([11]); bad_req.update(models=['custom_cnn'],optimizers=['adam'])
        bad_req['variants'][0]['selected'] = {'execution': {'calibrate_threshold': False}}
        try:
            expand_matrix(bad_req, protocol(), frozen=True, dataset=d)
        except CampaignError:
            cases.append('invalid_protocol_override_rejected')
        else:
            raise AssertionError('Invalid scientific override accepted')
        with scope(True) as c:
            assert c.execute(text("SELECT count(*) FROM evaluations WHERE split <> 'val'")).scalar_one()==0
            assert c.execute(text("SELECT count(*) FROM pg_trigger WHERE tgrelid IN (SELECT oid FROM pg_class WHERE relnamespace='public'::regnamespace) AND tgenabled='D'")).scalar_one()==0
            evidence['committed_reader_pid'] = c.execute(text('SELECT pg_backend_pid()')).scalar_one()
        cases.append('validation_only_triggers_enabled')
        keeper.execute(text('UPDATE experiment_execution_gate SET owner=NULL,db_pid=NULL'))
        keeper.execute(text('SELECT pg_advisory_unlock(120994,1)'))
        keeper.commit()
    engine.dispose()
    evidence['passed'] = len(cases)
    print(json.dumps(evidence,indent=2,default=str))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
