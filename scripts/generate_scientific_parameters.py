"""Generate the registry reference without DB, TensorFlow or dataset access."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'malaria_dl_local_project'))
from src.malaria_dl.models.scientific_parameters import (
    PARAMETERS, OPTIMIZER_DEFAULTS, consumer_map, defaults_by_model, flatten,
)


def link(reference: str) -> str:
    path, symbol = reference.split(':')
    return f'[{reference}](../malaria_dl_local_project/src/malaria_dl/{path})'


def render() -> str:
    lines = ['# Scientific Parameter Registry', '', 'Estado documental: `CURRENT_DOC`.', '',
             'Generado con `make scientific-parameters-doc`. No editar manualmente.', '',
             '## Auditoría y alcance', '',
             'Antes: TRAIN → find_threshold_for_target_recall. Después: TRAIN → CalibrationController → misma función. '
             'La selección, evaluación final y persistencia conservan sus funciones y payloads. '
             'Registro integrado en models/scientific_parameters.py; sólo metadatos y consultas puras, sin motor de dependencias.', '',
             'Incluye todos los campos model/execution/optimizer/recipe del contrato model_config_v1 y selection derivado. '
             'input_contract conserva el contrato de datos completo como evidencia adicional, sin convertir cada descriptor en un parámetro editable. '
             'Los resultados threshold_used/selected, warning, candidate_count y flags son salidas del calibrador, no configuraciones.', '',
             'Configuración determina ejecución; Dependencia condiciona aplicación; Cálculo afecta métricas; Selección elige checkpoint/umbral; '
             'Persistencia determina evidencia. Código significa conexión estática demostrada, no ejecución de una campaña. '
             'Los efectos cuantitativos sobre calidad del modelo son teóricos y pendientes de medición, sin dirección de mejora garantizada.', '',
             f'Cobertura: {len(PARAMETERS)} entradas gobernadas; defaults informativos, nunca sustitutos de evidencia histórica.', '',
             '## Diccionario de parámetros', '',
             '| Parámetro | Contrato y restricciones | Defaults por modelo/optimizador |', '| --- | --- | --- |']
    defaults = defaults_by_model()
    for p in PARAMETERS.values():
        values = {name: flatten(cfg).get(p.path, 'derivado/no aplica') for name, cfg in defaults.items()}
        if p.path.startswith('optimizer.parameters.'):
            key = p.path.split('.')[-1]
            values = {name: cfg[key] for name, cfg in OPTIMIZER_DEFAULTS.items() if key in cfg}
        lines.append(f'| `{p.path}` | {link(p.contract)}; {p.restriction} | `{json.dumps(values, ensure_ascii=False)}` |')
    lines += ['', 'Los perfiles batch se aplican antes de selected/overrides; no representan valores ejecutados:', '']
    for name, cfg in defaults.items():
        lines += [f'- {name}: `{json.dumps(cfg["batch"], sort_keys=True)}`']
    lines += ['', '## Matriz de dependencias y efectos científicos', '',
              '| Parámetro | Relaciones / relacionados | Consumidores | Activación / fase | Efecto y métricas | Evidencia | Persistencia efectiva |',
              '| --- | --- | --- | --- | --- | --- | --- |']
    for p in PARAMETERS.values():
        lines.append(f'| `{p.path}` | {", ".join(p.relations)}; {", ".join(p.related) or "Sin condición adicional"} | '
                     f'{"; ".join(map(link, p.consumers))} | {p.condition}; {p.phase} | {p.effect} | {p.evidence} | `{p.persistence}` |')
    lines += ['', '## Mapa de funciones consumidoras', '', '| Función | Parámetros |', '| --- | --- |']
    for consumer, paths in consumer_map().items():
        lines.append(f'| {link(consumer)} | {", ".join(paths)} |')
    lines += ['', '## Campañas, RUN y valores realmente ejecutados', '',
              'El protocolo de campaña traduce sensitivity_target a min_recall/target_recall, specificity_minimum a min_specificity, '
              'checkpoint a selección, early_stopping a sus controles y calibration.algorithm none/threshold_grid a calibrate_threshold. '
              'La matriz suministra arquitectura, optimizador y semilla. '
              + link('campaigns/contracts.py:expand_matrix') + ' conserva la precedencia y rechaza conflictos existentes. '
              'El catálogo público sigue fijando none; no se habilita calibración automáticamente.', '',
              'Persistencia: experimental_campaigns.requested/protocol/contract → campaign_configurations.configuration → '
              'runs.execution_parameters.model_configuration_e2.configuration → run_configurations.provenance_snapshot y extension_configuration. '
              + link('persistence/v2_projection.py:project_configuration') + ' conserva solicitado, efectivo y hash; '
              + link('execution/repository.py:bind_evaluation_context') + ' vincula checkpoint, dataset y protocolo.', '',
              'Consultar `effective_values(snapshot["resolved"])` o `effective_values(extension_configuration)`. '
              'Comparar con `compare_runs({run_id: extension_configuration, ...})`: incluye valores presentes, ausentes y desconocidos históricos, '
              'sin resolver defaults ni modificar snapshots. Las claves RUN identifican qué experimentos registran cada parámetro. '
              'La presencia de un valor no demuestra que su rama condicional se ejecutó; contrastar con runtime/phase/calibration y estado del RUN.', '',
              'Para obtener snapshots e identidad, consulta de sólo lectura propuesta (no ejecutada):', '',
              '```sql', 'SELECT r.id AS run_id, r.campaign_id, rc.configuration_hash,',
              '       rc.extension_configuration, rc.provenance_snapshot',
              'FROM runs r JOIN run_configurations rc ON rc.run_id = r.id',
              'WHERE r.campaign_id = :campaign_id;', '```', '',
              'Los registros runtime guardan el optimizador efectivo por fase (incluidos extras Keras), learning_rate por época, '
              'callbacks y entorno. La tasa configurada inicial no sustituye esa trayectoria. '
              'train_execution_records calibration/val/selected conserva resultado, checkpoint_epoch y scores VAL; '
              'los eventos conservan advertencias. project_calibration crea evaluaciones default/selected y run_threshold_calibration; '
              'evaluations registra threshold_used/source y checkpoint; run_clinical_metrics contiene resultados. '
              'No se añaden tablas ni escrituras retrospectivas. Idempotencia sigue en ResultService.accept_event.', '',
              '## Umbrales y resultados derivados', '',
              '| Campo | Definición / consumo | Persistencia |', '| --- | --- | --- |',
              '| threshold_selected / threshold_used | Resultado de find_threshold_for_target_recall; CalibrationController.threshold lo entrega a evaluate_validation_predictions. Decisión score >= t; cambia matriz, recall, especificidad, precision, F2 y BA; AUC/AP dependen de scores, no de t. | Evento/registro completo; run_threshold_calibration.threshold_selected y evaluations.threshold_used |',
              '| default_threshold / threshold_source | .5 / default si calibración desactivada; validation_calibration si activada. ThresholdResult verifica el contrato. | evaluations; pareja default/selected cuando corresponde |',
              '| target_recall_satisfied / min_specificity_satisfied | Factibilidad por filtros del calibrador; min_specificity_satisfied puede ser null. No implica cumplimiento de completion. | Evento y registro completos; proyección resumida incompleta H04 |',
              '| warning / candidate_count | Advertencias y número de candidatos de la búsqueda existente; no configuran política nueva. | Evento y registro completos; proyección resumida incompleta H04 |',
              '| selected_metrics / default_threshold_metrics | compute_clinical_metrics sobre el mismo checkpoint VAL y dos umbrales. | Evento/registro; evaluaciones calibration_selected/calibration_default y run_clinical_metrics |',
              '| clinical_objective_met | TRAIN compara métricas del checkpoint a .5 con min_recall/min_specificity. | completion y evento de cierre |', '',
              '## Políticas preservadas y límites', '',
              'H01: se conserva fallback relajando especificidad. H02: TRAIN usa >=; E7 conserva > y su propio selector. '
              'H03: completion sigue usando selección a .5, no métricas recalibradas. H04: columnas resumen omiten flags/warning; consultar evento completo. '
              'H05: se conserva validación numérica histórica del buscador. Ninguno se corrige silenciosamente.', '',
              'CalibrationController.from_request delega validación a resolve_config. El constructor de snapshots consume configuración ya validada '
              'por los contratos de campaña; no reinterpreta históricos con defaults actuales. El controlador valida split mediante el helper existente, '
              'no carga datos, no selecciona checkpoints y no consulta PostgreSQL. Las rutas legacy trainer/calibration_cli permanecen directas; '
              'EVALUATE/EXPLAIN consumen decisiones y linaje existentes, sin buscar umbrales nuevos.', '',
              '## Verificación', '',
              '`make test-scientific-parameters` ejecuta pruebas sintéticas de consistencia, equivalencia del controlador, fallbacks, '
              'contratos, selección y evaluación. No ejecuta campañas ni el conjunto TEST. '
              'Igualdad científica excluye únicamente created_at de dos llamadas independientes; resultados, warnings y flags deben coincidir. '
              'La integración PostgreSQL y una campaña real no quedan acreditadas por estas pruebas unitarias. B1 permanece intacto.', '',
              'Referencia de auditoría previa: [C1](audits/clinical_threshold_c1/DOCUMENTO_C1_THRESHOLDING_CLINICO.md).', '']
    return '\n'.join(lines)


if __name__ == '__main__':
    destination = ROOT / 'docs/scientific_parameters.md'
    content = render()
    if '--check' in sys.argv:
        if destination.read_text() != content:
            raise SystemExit('Scientific parameter documentation is stale')
    else:
        destination.write_text(content)
