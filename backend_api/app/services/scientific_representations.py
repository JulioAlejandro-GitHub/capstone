"""Representaciones: persisted REPRESENT matrices of each selected EVALUATE, and linear CKA between them.

No model runs here. PCA/UMAP were fitted by the executor; CKA depends on which attempts are compared,
so it is computed on read over the common samples, from embeddings whose content hash is checked first.
"""
from src.malaria_dl.assessment.representation import ROLES, linear_cka, representation_spec
from src.malaria_dl.campaigns.contracts import CampaignError
from src.malaria_dl.execution.artifacts import file_identity
from src.malaria_dl.execution.storage_paths import local_scientific_path

DEFINITIONS = {
    'representation': 'Salida de la única capa GlobalAveragePooling2D del modelo (vector por célula), sobre la población exacta de la EVALUATE seleccionada.',
    'pca': 'PCA centrado en la media de la población; se muestran las dos primeras componentes y la varianza explicada acumulada (hasta 50 componentes).',
    'umap': 'UMAP 2D (15 vecinos, min_dist 0,1, euclídea, semilla del TRAIN). Preserva vecindarios locales; las distancias globales y el tamaño de los grupos no son interpretables.',
    'cka': 'CKA lineal (Kornblith et al., 2019) entre embeddings de dos RUN sobre las muestras comunes: 1 indica geometría equivalente salvo rotación y escala isotrópica; no acredita igual desempeño.',
}


def _round(values, digits=4):
    return [[round(float(v), digits) for v in row] for row in values]


def _load(artifact, length):
    import numpy as np

    if file_identity(artifact['path']) != {k: artifact[k] for k in ('sha256', 'bytes')}:
        raise CampaignError('ASSESSMENT_ARTIFACT_CHANGED')
    array = np.load(local_scientific_path(artifact['path']), allow_pickle=False)
    if list(array.shape) != artifact['shape'] or (artifact['role'] != 'pca_variance' and array.shape[0] != length):
        raise CampaignError('REPRESENTATION_SHAPE_CONFLICT')
    return array


def representation_evidence(repo, connection, selection):
    """One RUN: its REPRESENT for the selected EVALUATE, or why there is none. Returns (dto, embeddings)."""
    result = {'training_run_id': selection.training_run_id, 'state': 'missing', 'issues': [], 'source_attempt_id': None}
    evaluation = selection.evaluation
    if not evaluation or evaluation.source != 'assessment':
        result['issues'].append('Las representaciones se calculan sobre una EVALUATE independiente (VAL o TEST); '
                                'selecciónala en la tarjeta del RUN.')
        return result, None
    result['source_attempt_id'] = evaluation.attempt_id
    attempt = repo.comparison_representation(connection, selection.training_run_id, evaluation.attempt_id, representation_spec())
    if not attempt:
        result['issues'].append('Sin representaciones generadas para esta evaluación.')
        return result, None
    rows = repo.comparison_representation_rows(connection, attempt['attempt_id'])
    artifacts = {a['role']: a for a in repo.comparison_representation_artifacts(connection, attempt['attempt_id'])}
    result.update(attempt_id=attempt['attempt_id'], identity_id=attempt['identity_id'], split=attempt['split'],
                  finished_at=attempt['finished_at'])
    if (len(rows) != attempt['sample_count'] or set(artifacts) != set(ROLES)
            or [r['result']['row'] for r in rows] != list(range(len(rows)))):
        result.update(state='incompatible', issues=['Representación incompleta o con filas desordenadas.'])
        return result, None
    try:
        arrays = {role: _load(artifacts[role], len(rows)) for role in ROLES}
    except (CampaignError, OSError, ValueError):
        result.update(state='incompatible', issues=['Artefacto de representación ausente o modificado.'])
        return result, None
    variance = [float(v) for v in arrays['pca_variance']]
    result.update(state='available', count=len(rows), dimension=int(arrays['embeddings'].shape[1]),
                  layer=rows[0]['result'].get('layer'),
                  samples=[r['sample_id'] for r in rows], labels=[r['label'] for r in rows],
                  predicted=[r['result']['predicted'] for r in rows],
                  scores=[round(r['result']['raw_score'], 4) for r in rows],
                  pca=_round(arrays['pca']), umap=_round(arrays['umap']),
                  variance=variance, cumulative_variance=[sum(variance[:i + 1]) for i in range(len(variance))])
    return result, {'samples': result['samples'], 'embeddings': arrays['embeddings']}


def cka_matrix(matrices):
    """Pairwise linear CKA over the samples each pair has in common (ordered by sample id)."""
    size = len(matrices)
    values = [[None] * size for _ in range(size)]
    common = [[0] * size for _ in range(size)]
    for i, left in enumerate(matrices):
        for j, right in enumerate(matrices):
            if j < i or left is None or right is None:
                continue
            index_left = {s: k for k, s in enumerate(left['samples'])}
            index_right = {s: k for k, s in enumerate(right['samples'])}
            shared = sorted(set(index_left) & set(index_right))
            common[i][j] = common[j][i] = len(shared)
            if len(shared) > 1:
                score = linear_cka(left['embeddings'][[index_left[s] for s in shared]],
                                   right['embeddings'][[index_right[s] for s in shared]])
                values[i][j] = values[j][i] = None if score is None else round(score, 6)
    return {'values': values, 'common': common}


def representations(repo, connection, selections):
    runs, matrices = [], []
    for selection in selections:
        dto, matrix = representation_evidence(repo, connection, selection)
        runs.append(dto)
        matrices.append(matrix)
    warnings = []
    splits = {r['split'] for r in runs if r['state'] == 'available'}
    if len(splits) > 1:
        warnings.append('Representaciones VAL/TEST mixtas: CKA solo usa las muestras comunes, que pueden no existir.')
    return {'runs': runs, 'cka': cka_matrix(matrices), 'definitions': DEFINITIONS}, warnings
