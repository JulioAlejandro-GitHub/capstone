"""Application EXPLAIN operations shared by HTTP and its isolated executor."""
import re
import socket
from typing import Any
from app.repositories.explain_queries import ExplainQueries
from app.schemas.explain_generation import ExplainRequest
from app.services.scientific_public import assessment_projection, public_evidence
from src.malaria_dl.assessment.contracts import require
from src.malaria_dl.assessment.service import explanation_spec, prepare, verify
from src.malaria_dl.data.governed_dataset import governed_relative_root

METHODS = ('gradcam', 'lime', 'shap')


def owner_absent(row: dict[str, Any]) -> bool:
    if row.get('host') != socket.gethostname():
        return False
    from src.malaria_dl.execution.global_gate import local_process_terminated
    return local_process_terminated(row['pid'])


def scientific_context(value: dict[str, Any]) -> dict[str, Any]:
    context = {key: value.get(key) for key in ('model', 'dataset', 'split', 'purpose', 'protocol', 'decision')}
    # Locations differ between Docker (/app/...) and the host checkout (GPU agent); the governed location under
    # <project>/data and the checkpoint content (sha256, bytes) identify them, as in TRAIN snapshots.
    if isinstance(context['dataset'], dict) and context['dataset'].get('dataset_root'):
        context['dataset'] = {**context['dataset'], 'dataset_root': list(governed_relative_root(context['dataset']['dataset_root']))}
    if isinstance(context['model'], dict):
        context['model'] = {key: item for key, item in context['model'].items() if key != 'path'}
    return context


class ExplainService:
    def __init__(self, repository: ExplainQueries) -> None:
        self.repository = repository

    def submit(self, request: ExplainRequest, launcher: Any, actor: str) -> dict[str, Any]:
        source = self.context(request)
        operations = []
        for method in dict.fromkeys(request.methods):
            try:
                existing = self.reusable(request, source, method)
            except ValueError:
                # The executor reports preparation errors per method and retains
                # valid methods from the same requested batch.
                continue
            if existing:
                operations.append({'method': method, 'attempt_id': str(existing['id'])})
        if len(operations) == len(set(request.methods)):
            return {'operations': operations}
        return launcher.launch(request, actor)

    def preview(self, request: ExplainRequest) -> dict[str, Any]:
        source = self.context(request)
        prepared = []
        for method in dict.fromkeys(request.methods):
            value = self.prepare(request, source, method, inspection=True)
            prepared.append({'method': method, 'sample_ids': [s['sample_id'] for s in value['samples']],
                             'specification': public_evidence(value['explanation'])})
        return {'sample_id': str(request.sample_id), 'training_run_id': source['model']['training_run_id'],
                'methods': prepared}

    def context(self, request: ExplainRequest) -> dict[str, Any]:
        source = self.repository.source(str(request.source_attempt_id))
        require(source is not None, 'EXPLAIN_SOURCE_NOT_FOUND')
        value = source['identity']
        require(value.get('split') == 'val' and value.get('purpose') == 'development', 'EXPLAIN_CONTEXT_UNSUPPORTED')
        sample = str(request.sample_id)
        require(any(row['sample_id'] == sample for row in value['samples']), 'EXPLANATION_SAMPLE_NOT_IN_CONTEXT')
        dataset = value['dataset']['dataset_version_id']
        require(self.repository.samples(dataset, sample, 1) == [sample], 'EXPLANATION_SAMPLE_SELECTION_EMPTY')
        return value

    def specification(self, request: ExplainRequest, value: dict[str, Any], method: str) -> dict[str, Any]:
        background: list[str] = []
        if method == 'shap':
            background = ([str(request.background_sample_id)] if request.background_sample_id
                          else self.repository.samples(value['dataset']['dataset_version_id'], limit=1))
            require(bool(background), 'BACKGROUND_CONTRACT_REQUIRED')
            require(self.repository.samples(value['dataset']['dataset_version_id'], background[0], 1) == background,
                    'BACKGROUND_NOT_ACCREDITED')
        return explanation_spec(method, None, request.class_id,
                                request.num_samples if method != 'gradcam' else None, background)

    def compatible(self, row: dict[str, Any], source: dict[str, Any], request: ExplainRequest,
                   specification: dict[str, Any]) -> bool:
        identity = row['identity']
        if scientific_context(identity) != scientific_context(source):
            return False
        target = next((sample for sample in source['samples'] if sample['sample_id'] == str(request.sample_id)), None)
        if target not in identity['samples']:
            return False
        recorded = identity.get('explanation') or {}
        for key, value in specification.items():
            actual = recorded.get(key)
            if key == 'background':
                actual = [sample['sample_id'] for sample in actual or []]
            if actual != value:
                return False
        return True

    def matching(self, request: ExplainRequest, source: dict[str, Any], method: str) -> list[dict[str, Any]]:
        specification = self.specification(request, source, method)
        return [row for row in self.repository.candidates(source['model']['training_run_id'], str(request.sample_id))
                if self.compatible(row, source, request, specification)]

    def reusable(self, request: ExplainRequest, source: dict[str, Any], method: str) -> dict[str, Any] | None:
        for row in self.matching(request, source, method):
            if row['state'] == 'active' and not owner_absent(row):
                return row
            if row['state'] == 'verified':
                try:
                    verify(self.repository, row, row['identity'])
                except (ValueError, OSError):
                    continue
                return row
        return None

    def prepare(self, request: ExplainRequest, source: dict[str, Any], method: str, inspection: bool = False) -> dict[str, Any]:
        value = prepare(self.repository, training_run_id=source['model']['training_run_id'],
                        split=source['split'], purpose=source['purpose'], protocol=source['protocol'],
                        requested_threshold=source['decision']['requested'], seed=source['seed'],
                        batch_size=source['batch_size'], explanation=self.specification(request, source, method),
                        sample_id=str(request.sample_id), inspection=inspection)
        require(scientific_context(value) == scientific_context(source), 'EXPLAIN_SOURCE_CONTEXT_CHANGED')
        require(len(value['samples']) == 1, 'EXPLANATION_SAMPLE_SELECTION_CONFLICT')
        return value

    def state(self, request: ExplainRequest, authorized: bool) -> dict[str, Any]:
        source = self.context(request)
        states = []
        batches = [row for row in self.repository.candidates(source['model']['training_run_id'], str(request.sample_id))
                   if scientific_context(row['identity']) == scientific_context(source)
                   and row['identity'].get('http_request', {}).get('request', {}).get('class_id') == request.class_id
                   and row['identity'].get('http_request', {}).get('request', {}).get('num_samples') == request.num_samples
                   and row['identity'].get('http_request', {}).get('request', {}).get('background_sample_id')
                       == (str(request.background_sample_id) if request.background_sample_id else None)]
        same = lambda queued: (queued.get('class_id', 1) == request.class_id and queued.get('num_samples', 1000) == request.num_samples
                               and queued.get('background_sample_id') == (str(request.background_sample_id) if request.background_sample_id else None))
        queued = [row for row in self.repository.requests_for(str(request.source_attempt_id), str(request.sample_id))
                  if same(row['request'])]
        for method in METHODS:
            try:
                rows = self.matching(request, source, method)
                reused = self.reusable(request, source, method)
                row = reused or next(iter(rows), None)
                state: dict[str, Any] = {'method': method, 'state': 'not_executed'}
                if row:
                    state.update(attempt_id=str(row['id']), identity_id=str(row['identity_id']),
                                 state={'active': 'running', 'verified': 'completed'}.get(row['state'], 'failed'))
                    if row['state'] == 'verified':
                        # reusable() already verified it; a second full-population pass doubles the cost.
                        if row is not reused:
                            verify(self.repository, row, row['identity'])
                        state['detail'] = assessment_projection({**row, 'kind': 'explain',
                            'training_run_id': source['model']['training_run_id'], 'attempt_id': row['id']})
                        state['artifacts'] = [{**public_evidence(a), 'attempt_id': str(row['id']),
                            'identity_id': str(row['identity_id']), 'training_run_id': source['model']['training_run_id']}
                            for a in self.repository.artifacts(row['id']) if a['sample_id'] == str(request.sample_id)]
                    elif row['state'] == 'active' and owner_absent(row):
                        state.update(state='failed', error='ASSESSMENT_OWNER_PROCESS_ABSENT')
                    elif row['state'] != 'active':
                        cause = row.get('cause')
                        state['error'] = cause if isinstance(cause, str) and re.fullmatch('[A-Z][A-Z0-9_]+', cause) else 'ASSESSMENT_EXECUTION_FAILED'
                latest = next((row for row in queued if method in row['request'].get('methods', [])), None)
                if state['state'] == 'not_executed' and latest and latest['state'] in ('queued', 'claimed'):
                    state.update(state='pending', operation_id=str(latest['id']))
                elif state['state'] == 'not_executed' and latest and latest['state'] == 'failed':
                    cause = latest.get('cause')
                    state.update(state='failed', operation_id=str(latest['id']),
                                 error=cause if isinstance(cause, str) and re.fullmatch('[A-Z][A-Z0-9_]+', cause) else 'EXPLAIN_HOST_EXECUTION_FAILED')
                if state['state'] == 'not_executed':
                    batch = next((batch for batch in batches if method in batch['identity']['http_request']['request']['methods']), None)
                    if batch:
                        preparation_error = batch['identity']['http_request'].get('preparation_errors', {}).get(method)
                        live = any(item['state'] == 'active' and not owner_absent(item) for item in batches
                                   if item['identity']['http_request'] == batch['identity']['http_request'])
                        state.update(state='pending' if live and not preparation_error else 'failed',
                                     operation_id=str(batch['id']),
                                     error=preparation_error or (None if live else 'EXPLAIN_BATCH_NOT_COMPLETED'))
                states.append(state)
            except (ValueError, OSError):
                states.append({'method': method, 'state': 'failed', 'error': 'EXPLAIN_EVIDENCE_OR_REFERENCE_INVALID'})
        return {'training_run_id': source['model']['training_run_id'],
                'dataset_version_id': source['dataset']['dataset_version_id'], 'sample_id': str(request.sample_id),
                'authorized': authorized, 'methods': states}
