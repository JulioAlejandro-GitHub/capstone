"""E10.9 science goldens, strict contracts and transactional application decisions."""
from copy import deepcopy
from dataclasses import replace
from uuid import uuid4

import pytest
from sklearn.metrics import fbeta_score
from src.malaria_dl.evaluation.validation import evaluate_validation_predictions
from src.malaria_dl.evaluation.binary_counts import metrics_from_counts
from src.malaria_dl.evaluation.threshold_calibration import find_threshold_for_target_recall
from src.malaria_dl.results.training import ThresholdResult, TrainingResultsV1, ValidationEvaluationV1
from src.malaria_dl.results import ResultService
from src.malaria_dl.results.errors import (InvalidScientificResult, FinalEvaluationConflict,
    EventIdConflict, SequenceGap, SequenceConflict, WriterNotAuthorized, ResultPersistenceError)
from src.malaria_dl.execution.contracts import RunEventType as E
from test_result_service import context, event
from result_repository_fake import FakeResultRepository


def evaluation():
    # TN=1 FP=1 FN=0 TP=2; ROC=3/4; average precision=(1 + 2/3)/2.
    return evaluate_validation_predictions([0, 0, 1, 1], [.1, .8, .6, .9], ThresholdResult(.5, 'default'))


def payload():
    return evaluation().to_dict()


def test_manual_scientific_golden():
    result = evaluation()
    assert result.n_samples == 4
    assert result.to_dict()['confusion_matrix'] == dict(tn=1, fp=1, fn=0, tp=2)
    assert result.to_dict()['metrics'] == pytest.approx(dict(recall=1, specificity=.5, precision=2/3,
        f1=.8, f2=10/11, balanced_accuracy=.75, roc_auc=.75, pr_auc=5/6))
    assert TrainingResultsV1.from_dict(TrainingResultsV1(result).to_dict()) == TrainingResultsV1(result)


@pytest.mark.parametrize('labels,scores,counts', [
    ([0,1],[.1,.2],dict(tn=1,fp=0,fn=1,tp=0)),
    ([0,0],[.1,.9],dict(tn=1,fp=1,fn=0,tp=0)),
    ([1,1],[.1,.9],dict(tn=0,fp=0,fn=1,tp=1)),
])
def test_zero_division_and_single_class(labels,scores,counts):
    result=evaluate_validation_predictions(labels,scores,ThresholdResult(.5,'default'))
    assert result.to_dict()['confusion_matrix']==counts
    for name,value in metrics_from_counts(**counts).items():
        assert getattr(result.metrics,name)==pytest.approx(value)
    if len(set(labels))==1:assert result.metrics.roc_auc is result.metrics.pr_auc is None


@pytest.mark.parametrize('tn,fp,fn,tp', [(3,1,2,4),(1,0,0,0),(2,0,3,0),(0,1,0,2),(1,100,1,2)])
def test_f2_matches_existing_sklearn_definition(tn,fp,fn,tp):
    y=[0]*(tn+fp)+[1]*(fn+tp); predicted=[0]*tn+[1]*fp+[0]*fn+[1]*tp
    assert metrics_from_counts(tn,fp,fn,tp)['f2']==pytest.approx(fbeta_score(y,predicted,beta=2,zero_division=0),abs=1e-12)


@pytest.mark.parametrize('enabled',[False,True])
def test_threshold_policy_preserved(enabled):
    labels=[0,0,1,1];scores=[.1,.8,.6,.9]
    calibration=find_threshold_for_target_recall(labels,scores)
    t=ThresholdResult(calibration['threshold_used'],'validation_calibration') if enabled else ThresholdResult(.5,'default')
    result=evaluate_validation_predictions(labels,scores,t)
    assert result.threshold==t
    if enabled:
        assert result.metrics.f2==calibration['selected_metrics']['f2_parasitized']
        assert result.to_dict()['confusion_matrix']=={k:calibration['selected_metrics'][k] for k in ('tn','fp','fn','tp')}


@pytest.mark.parametrize('path,value', [
    (('n_samples',),5),(('n_samples',),True),(('split',),'test'),(('schema_version',),'v2'),
    (('evaluation_role',),'other'),(('confusion_matrix','tn'),-1),(('confusion_matrix','tp'),True),
    (('confusion_matrix','tn'),1.0),(('metrics','recall'),.99),(('metrics','f2'),.5),
    (('metrics','roc_auc'),None),(('metrics','pr_auc'),2),(('metrics','precision'),float('nan')),
    (('metrics','recall'),float('inf')),(('threshold','source'),'configured'),
    (('threshold','value'),.7),(('threshold','value'),-1),(('threshold','value'),True),
])
def test_invalid_science_rejected(path,value):
    wire=payload();target=wire
    for key in path[:-1]:target=target[key]
    target[path[-1]]=value
    with pytest.raises(ValueError):ValidationEvaluationV1.from_dict(wire)


@pytest.mark.parametrize('labels,scores',[([],[]),([0],[.2,.4]),([2],[.2]),([.5],[.2]),([1],[float('nan')]),([0],[1.1]),([[1]],[[.1]])])
def test_invalid_predictions_rejected(labels,scores):
    with pytest.raises(ValueError):evaluate_validation_predictions(labels,scores,ThresholdResult(.5,'default'))


def test_exact_keys_no_arbitrary_json():
    for wire in (payload()|{'extra':1}, {k:v for k,v in payload().items() if k!='metrics'}, {}):
        with pytest.raises(ValueError):ValidationEvaluationV1.from_dict(wire)


@pytest.fixture
def service():
    repo=FakeResultRepository();ctx=context();repo.authorize(ctx)
    repo.parameters[ctx.run_id]={'legacy':{'keep':[1,True]}}
    return repo,ctx,ResultService(repo),event(event_type=E.EVALUATION_COMPLETED,payload=payload())


def test_projection_retry_and_immutable_final(service):
    repo,ctx,svc,ev=service
    svc.accept_event(ctx,ev);before=deepcopy(repo.parameters)
    assert svc.accept_event(ctx,ev).status.value=='duplicate_accepted'
    assert len(repo.events)==1 and repo.parameters==before
    assert before[ctx.run_id]=={'legacy':{'keep':[1,True]},'training_results':TrainingResultsV1(evaluation()).to_dict()}
    with pytest.raises(FinalEvaluationConflict):svc.accept_event(ctx,replace(ev,event_id=uuid4(),sequence=2))
    assert len(repo.events)==1 and repo.parameters==before


@pytest.mark.parametrize('case',['malformed','gap','writer','projection','commit','conflict','sequence'])
def test_rejection_never_changes_projection(service,case):
    repo,ctx,svc,ev=service
    if case in ('conflict','sequence'):svc.accept_event(ctx,ev)
    before=deepcopy(repo.parameters);events=repo.events
    error=InvalidScientificResult
    if case=='malformed':ev=replace(ev,payload={})
    if case=='gap':ev=replace(ev,sequence=2);error=SequenceGap
    if case=='writer':ctx=replace(ctx,owner=uuid4());error=WriterNotAuthorized
    if case in ('projection','commit'):repo.failure=case;error=ResultPersistenceError
    if case=='conflict':ev=replace(ev,payload={});error=EventIdConflict
    if case=='sequence':ev=replace(ev,event_id=uuid4());error=SequenceConflict
    with pytest.raises(error):svc.accept_event(ctx,ev)
    assert repo.parameters==before and repo.events==events


def test_lost_ack_retries_atomic_result(service):
    repo,ctx,svc,ev=service;repo.failure='ack'
    with pytest.raises(ResultPersistenceError):svc.accept_event(ctx,ev)
    before=deepcopy(repo.parameters);repo.failure=None
    assert svc.accept_event(ctx,ev).status.value=='duplicate_accepted'
    assert repo.parameters==before and len(repo.events)==1
