"""Exact successful preliminary SELECTs, retained for the SQL audit trail."""
from __future__ import annotations

DIAGNOSTICS: list[dict[str,str]] = []

def add(objective: str, tables: str, fields: str, validation: str, sql: str, joins: str = 'Sin JOIN; lectura directa de la fuente indicada.') -> None:
    DIAGNOSTICS.append(dict(id=f'D{len(DIAGNOSTICS)+1:02d}',objective=objective,tables=tables,
                            fields=fields,validation=validation,sql=sql,joins=joins))

add('Inventario inicial de tablas y vistas','information_schema.tables','table_name','Nombres contrastados con Q02.',
    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
add('Esquema inicial de entidades científicas','information_schema.columns','table_name, column_name, data_type','Columnas reales; ampliación en Q02.',
    "SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_schema='public' AND table_name IN ('experimental_campaigns','campaign_members','campaign_attempts','campaign_configurations','run_configurations','runs','training_history','run_metrics','run_clinical_metrics','artifacts','run_checkpoint_policy','models','evaluations','environment_packages','execution_logs','datasets','dataset_versions','experiments') ORDER BY table_name,ordinal_position")
add('Identificar campaña y entorno declarado','experimental_campaigns','id,name,state,expected_count,dataset_version_id,created_at,environment','Una campaña de 12 miembros esperados.',
    'SELECT id,name,state,expected_count,dataset_version_id,created_at,environment FROM experimental_campaigns ORDER BY created_at')
add('Inventario inicial de RUNS','runs','run_type,status,count','12 training/completed; sin filtros de rendimiento.',
    'SELECT run_type,status,count(*) FROM runs GROUP BY run_type,status')
add('Inspección inicial de identidades de configuración','runs,run_configurations,campaign_attempts,campaign_members,campaign_configurations',
    'id,run_name,architecture,optimizer,configuration,execution_parameters','Muestra LIMIT 2, posteriormente validada para 12/12 por Q04/Q12.',
    'SELECT r.id,r.run_name,rc.architecture,rc.optimizer,cc.configuration,r.execution_parameters FROM runs r LEFT JOIN run_configurations rc ON rc.run_id=r.id LEFT JOIN campaign_attempts ca ON ca.training_run_id=r.id LEFT JOIN campaign_members cm ON cm.id=ca.member_id LEFT JOIN campaign_configurations cc ON cc.campaign_id=cm.campaign_id AND cc.configuration_hash=cm.configuration_hash ORDER BY cm.position LIMIT 2',
    'RUN→configuración por run_id; RUN→intento por training_run_id; intento→miembro por member_id; configuración por campaign_id y configuration_hash. LEFT JOIN preserva ausencias.')
add('Muestra completa del primer RUN','runs','row_to_json(r), todos los campos de runs','Detectó campos planos nulos y completed_epochs=0; auditoría completa Q05.',
    'SELECT row_to_json(r) FROM runs r ORDER BY started_at LIMIT 1')
add('Inspección de historia de entrenamiento','training_history','row_to_json(h), todos los campos','Resultado vacío, no se interpreta como cero épocas.',
    'SELECT row_to_json(h) FROM training_history h ORDER BY created_at LIMIT 2')
add('Inspección inicial de métricas clínicas','run_clinical_metrics','row_to_json(m), todos los campos','Muestra LIMIT 1 sin orden; no se usa para seleccionar ganador. Q08 recupera todas.',
    'SELECT row_to_json(m) FROM run_clinical_metrics m LIMIT 1')
add('Inspección de proyección de políticas','run_checkpoint_policy','row_to_json(p), todos los campos','Vacía; selección recuperada de sesiones/artefactos.',
    'SELECT row_to_json(p) FROM run_checkpoint_policy p LIMIT 1')
add('Inspección inicial de evaluación','evaluations','row_to_json(e), todos los campos','Muestra LIMIT 1 sin orden; Q08 restringe rol y split explícitamente.',
    'SELECT row_to_json(e) FROM evaluations e LIMIT 1')
add('Tipos de artefactos catalogados','artifacts','artifact_type,count','model_checkpoint: 12.',
    'SELECT artifact_type,count(*) FROM artifacts GROUP BY artifact_type')
add('Localizar tablas de eventos y sesiones','information_schema.columns','table_name,column_name,data_type','Confirmó JSONB payload y campos de claves de registros.',
    "SELECT table_name,column_name,data_type FROM information_schema.columns WHERE table_schema='public' AND table_name IN ('experiment_execution_events','campaign_execution_events','train_execution_records','train_execution_sessions','train_execution_revisions') ORDER BY table_name,ordinal_position")
add('Cobertura de run_metrics','run_metrics','count','Valor count=0; la consulta devuelve una fila agregada.',
    'SELECT count(*) FROM run_metrics')
add('Cobertura de logs','execution_logs','count','Valor count=0; la consulta devuelve una fila agregada.',
    'SELECT count(*) FROM execution_logs')
add('Inspección de checkpoint catalogado','artifacts','row_to_json(a), todos los campos','Muestra LIMIT 1 sin orden; Q09 verifica todo el catálogo de campaña.',
    'SELECT row_to_json(a) FROM artifacts a LIMIT 1')
add('Inventario de tipos/fases de evidencia','train_execution_records','kind,phase,count','Localizó 263 épocas base y 133 fine_tuning; Q13 verifica cobertura.',
    'SELECT kind,phase,count(*) FROM train_execution_records GROUP BY kind,phase ORDER BY kind,phase')
add('Inspección de payload por tipo/fase','train_execution_records','kind,phase,record_key,payload','DISTINCT ON: sólo muestra inicial por tipo/fase. Incluía payloads voluminosos; se acotaron proyecciones posteriores.',
    'SELECT DISTINCT ON (kind,phase) kind,phase,record_key,payload FROM train_execution_records ORDER BY kind,phase,created_at')
add('Inspección de completion y verificación','train_execution_sessions','run_id,state,completion,verification,environment','Primera sesión por started_at; cotejo completo Q05.',
    'SELECT run_id,state,completion,verification,environment FROM train_execution_sessions ORDER BY started_at LIMIT 1')
add('Inspección acotada de épocas y cierres','train_execution_records','kind,phase,record_key,payload','Identificó epochs y early_stopping por fase; muestra inicial, ampliada en Q06/Q07.',
    "SELECT DISTINCT ON (kind,phase) kind,phase,record_key,payload FROM train_execution_records WHERE kind IN ('epoch','phase') ORDER BY kind,phase,created_at")
add('Inspección de claves del contenedor de eventos','train_execution_records','event_type,key','event_type nulo en este nivel: el evento está en la cadena canonical_event; no se interpreta como tipo desconocido.',
    "SELECT payload->>'event_type' AS event_type, jsonb_object_keys(payload) AS key FROM train_execution_records WHERE kind='e10_event' LIMIT 25")
add('Inspección de runtime compilado','train_execution_records','run_id,phase,runtime','Muestra LIMIT 1 sin orden; Q12 recupera las 20 fases.',
    "SELECT run_id,phase,payload - 'model_json' - 'model_configuration' - 'architecture' AS runtime FROM train_execution_records WHERE kind='runtime' LIMIT 1")
add('Verificar representación de canonical_event','train_execution_records','payload','Confirma que canonical_event es texto JSON; Q11 usa ->> y cast a jsonb.',
    "SELECT payload FROM train_execution_records WHERE kind='e10_event' ORDER BY created_at LIMIT 1")
