"""Common scientific success contract; consumes durable snapshots without IO."""
from dataclasses import asdict, dataclass, fields
import hashlib
import math
import re
from uuid import UUID

from ..campaigns.contracts import CampaignError, canonical, digest
from ..results.identity import canonical_event
from ..results.training import TrainingResultsV1, ValidationEvaluationV1, METRIC_TOLERANCE
from .contracts import RunEventType as E


class CompletionError(CampaignError):
    code = 'COMPLETION_EVIDENCE_MISMATCH'

    def __init__(self):
        super().__init__(self.code)


class MissingTrainingEvaluation(CompletionError):
    code = 'MISSING_TRAINING_EVALUATION'


class TrainingResultsMismatch(CompletionError):
    code = 'TRAINING_RESULTS_MISMATCH'


class ValidationPopulationMismatch(CompletionError):
    code = 'VALIDATION_POPULATION_MISMATCH'


class ThresholdMismatch(CompletionError):
    code = 'TRAINING_THRESHOLD_MISMATCH'


class MissingTerminalEvent(CompletionError):
    code = 'MISSING_TRAINING_TERMINAL_EVENT'


class InvalidEventStream(CompletionError):
    code = 'INVALID_TRAINING_EVENT_STREAM'


class SelectedCheckpointMismatch(CompletionError):
    code = 'SELECTED_CHECKPOINT_MISMATCH'


class DatasetSnapshotMismatch(CompletionError):
    code = 'TRAINING_DATASET_SNAPSHOT_MISMATCH'


def event_fingerprint(event):
    return hashlib.sha256(canonical_event(event).encode('utf-8')).hexdigest()


@dataclass(frozen=True, slots=True)
class TrainingCompletionContractV1:
    run_id: str
    attempt_id: str | None
    dataset_version_id: str
    validation_split: str
    validation_n_samples: int
    evaluation_event_id: str
    evaluation_sequence: int
    evaluation_fingerprint: str
    training_results_hash: str
    terminal_event_id: str
    terminal_sequence: int
    terminal_fingerprint: str
    checkpoint_epoch: int
    checkpoint_version_id: str
    checkpoint_sha256: str
    checkpoint_bytes: int
    checkpoint_identity_hash: str
    dataset_snapshot_hash: str
    configuration_hash: str
    validation_predictions_hash: str
    records_hash: str
    schema_version: str = 'training_completion_v1'

    def __post_init__(self):
        if self.schema_version != 'training_completion_v1' or self.validation_split != 'val':
            raise CompletionError()
        for name in ('run_id','dataset_version_id','evaluation_event_id','terminal_event_id','checkpoint_version_id'):
            value = getattr(self, name)
            if type(value) is not str or str(UUID(value)) != value:
                raise CompletionError()
        if self.attempt_id is not None and (type(self.attempt_id) is not str or str(UUID(self.attempt_id)) != self.attempt_id):
            raise CompletionError()
        for name in ('validation_n_samples','evaluation_sequence','terminal_sequence','checkpoint_epoch','checkpoint_bytes'):
            if type(getattr(self,name)) is not int or getattr(self,name) <= 0:
                raise CompletionError()
        if self.evaluation_sequence >= self.terminal_sequence:
            raise CompletionError()
        for name in ('evaluation_fingerprint','training_results_hash','terminal_fingerprint',
                     'checkpoint_sha256','checkpoint_identity_hash','dataset_snapshot_hash',
                     'configuration_hash','validation_predictions_hash','records_hash'):
            if not isinstance(getattr(self,name),str) or not re.fullmatch('[a-f0-9]{64}',getattr(self,name)):
                raise CompletionError()

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, value):
        if type(value) is not dict or set(value) != {f.name for f in fields(cls)}:
            raise CompletionError()
        try:
            return cls(**value)
        except (ValueError, TypeError, AttributeError):
            raise CompletionError() from None


@dataclass(frozen=True)
class CompletionEvidence:
    session: dict
    run: dict
    records: list
    events: list
    campaign_dataset: dict | None = None


def is_e10_governed(evidence):
    seal = (evidence.session.get('completion') or {}).get('training_completion')
    # Previously sealed E10 cannot downgrade if its stream is removed illegally.
    return bool(evidence.events) or (isinstance(seal,dict) and seal.get('schema_version') == 'training_completion_v1')


def _same(a, b):
    return canonical(a) == canonical(b)


def _close(a, b):
    return (type(a) in (int,float) and type(b) in (int,float) and math.isfinite(a) and math.isfinite(b)
            and math.isclose(a,b,rel_tol=METRIC_TOLERANCE,abs_tol=METRIC_TOLERANCE))


class TrainingCompletionValidator:
    def validate(self, evidence: CompletionEvidence, completion: dict, *, sealed=False):
        if not is_e10_governed(evidence):
            return None
        try:
            result = self._validate(evidence,completion)
            if sealed and TrainingCompletionContractV1.from_dict(completion.get('training_completion')) != result:
                raise CompletionError()
            return result
        except CompletionError:
            raise
        except (KeyError,TypeError,ValueError,AttributeError,IndexError,OverflowError):
            raise CompletionError() from None

    def _validate(self, evidence, completion):
        s, run, records, events = evidence.session, evidence.run, evidence.records, evidence.events
        rid, attempt = str(s['run_id']), str(s['attempt_id']) if s['attempt_id'] else None
        if (not events or any(e.sequence != i or str(e.run_id) != rid
                or (str(e.attempt_id) if e.attempt_id else None) != attempt for i,e in enumerate(events,1))
                or len({e.event_id for e in events}) != len(events)):
            raise InvalidEventStream()
        evaluations = [e for e in events if e.event_type is E.EVALUATION_COMPLETED]
        if len(evaluations) != 1:
            raise MissingTrainingEvaluation()
        ev = evaluations[0]
        terminals = [e for e in events if e.event_type in (E.TRAINING_COMPLETED,E.TRAINING_FAILED)]
        if not terminals:
            raise MissingTerminalEvent()
        if (len(terminals) != 1 or terminals[0].event_type is not E.TRAINING_COMPLETED
                or terminals[0] != events[-1] or ev.sequence >= terminals[0].sequence):
            raise InvalidEventStream()
        terminal = terminals[0]
        try:
            results = TrainingResultsV1.from_dict(run['parameters']['training_results'])
            evaluation = ValidationEvaluationV1.from_dict(ev.to_dict()['payload'])
            if not _same(results.validation.to_dict(),evaluation.to_dict()):
                raise TrainingResultsMismatch()
        except (KeyError,ValueError,TypeError,OverflowError):
            raise TrainingResultsMismatch() from None
        if (str(run['id']) != rid or run['run_type'] != 'training'
                or str(run['dataset_version_id']) != s['dataset']['dataset_version_id']):
            raise DatasetSnapshotMismatch()
        origin = run['execution_parameters']['model_configuration_e2']
        if (not _same(origin['dataset'],s['dataset']) or not _same(origin['configuration'],s['configuration'])
                or (evidence.campaign_dataset is not None and not _same(evidence.campaign_dataset,s['dataset']))):
            raise DatasetSnapshotMismatch()
        population = s['dataset']['counts']['val']
        if type(population) is not int or population != evaluation.n_samples:
            raise ValidationPopulationMismatch()
        raw = {k:v for k,v in completion.items() if k != 'training_completion'}
        if not _same(raw,terminal.to_dict()['payload']) or completion['records_hash'] != digest(records):
            raise CompletionError()
        rows = {(r['kind'],r['phase'],r['record_key']):r['payload'] for r in records}
        if len(rows) != len(records):
            raise CompletionError()
        epoch = completion['selection']['selected_epoch']
        artifacts = [r for r in records if r['kind']=='artifact' and r['payload']['epoch']==epoch]
        if len(artifacts) != 1:
            raise SelectedCheckpointMismatch()
        row = artifacts[0]; artifact = row['payload']; phase, key = row['phase'],row['record_key']
        if artifact['run_id'] != rid or artifact['phase'] != phase:
            raise SelectedCheckpointMismatch()
        prepared = rows['artifact_prepared',phase,key]
        if any(prepared[k] != artifact[k] for k in ('epoch','run_id','path')):
            raise SelectedCheckpointMismatch()
        epochs = [r for r in records if r['kind']=='epoch']
        if len(epochs) != completion['epochs']:
            raise CompletionError()
        last = max(epochs,key=lambda r:r['payload']['epoch'])
        if not _same(rows['selection',last['phase'],last['record_key']],completion['selection']):
            raise SelectedCheckpointMismatch()
        final = rows.get(('calibration','val','selected'))
        if not final or final.get('checkpoint_epoch') != epoch:
            raise SelectedCheckpointMismatch()
        predictions = rows['predictions',phase,key]; samples = final['samples']
        if (predictions['epoch'] != epoch or predictions['role'] != 'val' or len(samples) != population
                or len(predictions['samples']) != population or len({x['sample'] for x in samples}) != population
                or any(not isinstance(x['sample'],str) or not x['sample'].startswith('val/')
                       or '..' in x['sample'].split('/') for x in samples)):
            raise SelectedCheckpointMismatch()
        if {x['sample']:x['label'] for x in samples} != {x['sample']:x['label'] for x in predictions['samples']}:
            raise SelectedCheckpointMismatch()
        from ..evaluation.threshold_calibration import DEFAULT_THRESHOLD
        from ..evaluation.validation import evaluate_validation_predictions
        calibrated = s['configuration']['resolved']['execution']['calibrate_threshold']
        calibration = final['result']
        calibration_events = [e for e in events if e.event_type is E.CALIBRATION_COMPLETED]
        if calibrated is True:
            if (evaluation.threshold.source != 'validation_calibration'
                    or calibration.get('threshold_source') != evaluation.threshold.source
                    or not _close(evaluation.threshold.value,calibration.get('threshold_used'))
                    or not _close(evaluation.threshold.value,calibration.get('threshold_selected'))
                    or len(calibration_events) != 1):
                raise ThresholdMismatch()
            ce = calibration_events[0]
            if ce.sequence >= ev.sequence or not _same(ce.to_dict()['payload'],{
                    'legacy_record':{'kind':'calibration','phase':'val','record_key':'selected'},
                    'result':{'split':'val','checkpoint_epoch':epoch,'result':calibration}}):
                raise ThresholdMismatch()
        elif calibrated is False:
            if evaluation.threshold.source != 'default' or not _close(evaluation.threshold.value,DEFAULT_THRESHOLD) or calibration_events:
                raise ThresholdMismatch()
        else:
            raise ThresholdMismatch()
        expected = evaluate_validation_predictions([x['label'] for x in samples],[x['score'] for x in samples],evaluation.threshold)
        if expected.confusion_matrix != evaluation.confusion_matrix:
            raise TrainingResultsMismatch()
        for name,value in asdict(expected.metrics).items():
            actual = getattr(evaluation.metrics,name)
            if (value is None and actual is not None) or (value is not None and not _close(value,actual)):
                raise TrainingResultsMismatch()
        return TrainingCompletionContractV1(
            run_id=rid,attempt_id=attempt,dataset_version_id=s['dataset']['dataset_version_id'],
            validation_split='val',validation_n_samples=population,evaluation_event_id=str(ev.event_id),
            evaluation_sequence=ev.sequence,evaluation_fingerprint=event_fingerprint(ev),
            training_results_hash=digest(results.to_dict()),terminal_event_id=str(terminal.event_id),
            terminal_sequence=terminal.sequence,terminal_fingerprint=event_fingerprint(terminal),
            checkpoint_epoch=epoch,checkpoint_version_id=artifact['version_id'],checkpoint_sha256=artifact['sha256'],
            checkpoint_bytes=artifact['bytes'],checkpoint_identity_hash=digest(artifact),
            dataset_snapshot_hash=digest(s['dataset']),configuration_hash=digest(s['configuration']),
            validation_predictions_hash=digest(samples),records_hash=digest(records))
