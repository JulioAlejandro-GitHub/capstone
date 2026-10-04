"""Verified SELECT catalogue for the historical B1 audit; no training imports."""
CAMPAIGN = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'
FILTER = f"r.campaign_id = '{CAMPAIGN}'::uuid"
QUERIES = []

def add(key: str, objective: str, tables: str, joins: str, validation: str, sql: str) -> None:
    QUERIES.append(dict(id=key, objective=objective, tables=tables, joins=joins,
                        validation=validation, sql=sql.strip().rstrip(';')))

add('Q01', 'Identificar campañas y universo de RUNS', 'experimental_campaigns, runs',
    'LEFT JOIN por runs.campaign_id; conserva campañas sin RUNS.',
    'Una campaña, expected_count=12 y 12 RUNS training/completed.', """
SELECT c.id,c.name,c.state,c.expected_count,c.dataset_version_id,c.created_at,
       r.run_type,r.status,count(r.id) AS run_count
FROM experimental_campaigns c LEFT JOIN runs r ON r.campaign_id=c.id
GROUP BY c.id,r.run_type,r.status ORDER BY c.created_at,r.run_type,r.status
""")
add('Q02','Verificar esquema real','information_schema.columns','Sin JOIN.',
    'Columnas consultadas existen; tipos JSONB, numeric y timestamptz conservados.', """
SELECT table_name,column_name,data_type FROM information_schema.columns
WHERE table_schema='public' AND table_name IN (
'experimental_campaigns','campaign_members','campaign_attempts','campaign_configurations',
'run_configurations','runs','training_history','run_metrics','run_clinical_metrics',
'artifacts','run_checkpoint_policy','models','evaluations','environment_packages',
'execution_logs','datasets','dataset_versions','experiments','train_execution_records',
 'train_execution_sessions','train_execution_revisions','experiment_execution_events','campaign_execution_events')
ORDER BY table_name,ordinal_position
""")
add('Q03','Campaña, protocolo y dataset','experimental_campaigns, dataset_versions, datasets, runs',
    'Versión por dataset_version_id; dataset de origen mediante los RUNS seleccionados.',
    'Una versión; distribución y objetivo recuperados del protocolo, sin acceder a TEST.',f"""
SELECT c.*,row_to_json(dv) AS dataset_version,
       (SELECT json_agg(d ORDER BY d.id) FROM datasets d WHERE d.id IN
        (SELECT r.dataset_id FROM runs r WHERE {FILTER})) AS source_datasets
FROM experimental_campaigns c LEFT JOIN dataset_versions dv ON dv.id=c.dataset_version_id
WHERE c.id='{CAMPAIGN}'::uuid
""")
add('Q04','Trazabilidad campaña → miembro → intento → RUN y configuración','campaign_members, campaign_attempts, campaign_configurations, runs, run_configurations, models',
    'LEFT JOIN conserva ausencias: intento.member_id=miembro.id; RUN.id=training_run_id; configuración de campaña por clave compuesta (campaign_id,configuration_hash); configuración de RUN por run_id; models por model_id.',
    '12 miembros, 12 intentos aceptados, 12 RUNS únicos; igualdad de arquitectura y optimizador en tres fuentes y de hashes miembro/configuración.',f"""
SELECT cm.id AS member_id,cm.campaign_id,cm.position,cm.seed,cm.state AS member_state,
 cm.exclusion_reason,cm.accepted_attempt_id,cm.configuration_hash AS member_configuration_hash,
 ca.id AS attempt_id,ca.ordinal,ca.state AS attempt_state,ca.cause,
 ca.started_at AS attempt_started_at,ca.finished_at AS attempt_finished_at,
 r.id AS run_id,r.campaign_id AS run_campaign_id,r.run_type,r.status,
 rc.architecture,rc.optimizer,rc.configuration_hash AS run_configuration_hash,
 cc.configuration->>'model_id' AS campaign_architecture,
 cc.configuration#>>'{{resolved,optimizer,name}}' AS campaign_optimizer,
 r.execution_parameters#>>'{{model_configuration_e2,configuration,model_id}}' AS execution_architecture,
 r.execution_parameters#>>'{{model_configuration_e2,configuration,resolved,optimizer,name}}' AS execution_optimizer,
 row_to_json(rc) AS run_configuration,cc.configuration AS campaign_configuration,
 cc.requests AS configuration_requests,m.name AS model_name,m.architecture AS model_architecture
FROM campaign_members cm LEFT JOIN campaign_attempts ca ON ca.member_id=cm.id
LEFT JOIN runs r ON r.id=ca.training_run_id
LEFT JOIN run_configurations rc ON rc.run_id=r.id
LEFT JOIN campaign_configurations cc ON cc.campaign_id=cm.campaign_id AND cc.configuration_hash=cm.configuration_hash
LEFT JOIN models m ON m.id=r.model_id
WHERE cm.campaign_id='{CAMPAIGN}'::uuid ORDER BY cm.position,ca.ordinal
""")
add('Q05','Entorno, inicio, término, duración y estado persistido','runs, train_execution_sessions',
    'LEFT JOIN sesión por run_id; mantiene RUNS sin sesión.',
    'Duración positiva y coincidencia exacta con finished_at-started_at; separar entorno declarado del runtime.',f"""
SELECT r.*,extract(epoch FROM (r.finished_at-r.started_at)) AS wall_seconds,
 r.duration_seconds-extract(epoch FROM (r.finished_at-r.started_at)) AS duration_difference_seconds,
 s.attempt_id AS session_attempt_id,s.state AS session_state,s.host AS session_host,
 s.started_at AS session_started_at,s.updated_at AS session_updated_at,
 s.environment AS session_environment,s.completion,s.verification
FROM runs r LEFT JOIN train_execution_sessions s ON s.run_id=r.id
WHERE {FILTER} ORDER BY r.started_at,r.id
""")
add('Q06','Épocas y métricas originales por fase','train_execution_records, runs',
    'JOIN RUN por run_id limita la campaña; sólo kind=epoch evita duplicar los eventos canónicos.',
    '396 filas, unicidad run/fase/clave y época global, secuencias contiguas; cotejo con phase y completion.',f"""
SELECT t.* FROM train_execution_records t JOIN runs r ON r.id=t.run_id
WHERE {FILTER} AND t.kind='epoch'
ORDER BY t.run_id,(t.payload->>'epoch')::integer
""")
add('Q07','Cierre por fase y EarlyStopping','train_execution_records, runs',
    'JOIN por run_id; kind=phase contiene los cierres.',
    '20 fases; comparar epochs con Q06 y stopped_epoch con índice local base cero.',f"""
SELECT t.* FROM train_execution_records t JOIN runs r ON r.id=t.run_id
WHERE {FILTER} AND t.kind='phase' ORDER BY t.run_id,t.phase
""")
add('Q08','Métricas finales de VALIDATION y checkpoint evaluado','run_clinical_metrics, evaluations, runs, artifacts',
    'JOIN evaluación por evaluation_id, RUN por training_run_id; LEFT JOIN artefacto por checkpoint_artifact_id. No se une sólo por run_id, que podría multiplicar evaluaciones.',
    '12 evaluaciones training_validation_final/val, misma versión y RUN, matrices de 2693; recalcular recall/specificity/F1/F2 y contrastar AUC con checkpoint.',f"""
SELECT m.*,e.training_run_id,e.run_id AS evaluation_run_id,e.split AS evaluation_split,
 e.evaluation_role,e.checkpoint_artifact_id,e.dataset_version_id AS evaluation_dataset_version_id,
 e.source_event_id,e.metric_definition,e.protocol_hash,e.population_hash,e.comparison_contract_hash,
 e.threshold_used AS evaluation_threshold,a.name AS checkpoint_name,a.path AS checkpoint_path,
 a.checksum AS checkpoint_sha256,a.metadata AS checkpoint_metadata
FROM run_clinical_metrics m JOIN evaluations e ON e.id=m.evaluation_id
JOIN runs r ON r.id=e.training_run_id LEFT JOIN artifacts a ON a.id=e.checkpoint_artifact_id
WHERE {FILTER} AND e.split='val' AND e.evaluation_role='training_validation_final'
ORDER BY m.run_id,m.evaluation_id
""")
add('Q09','Catálogo de artefactos seleccionados','artifacts, runs','JOIN por run_id.',
    '12 checkpoints; comprobar IDs, fase, época y checksum contra completion y evaluación. No se afirma existencia física actual.',f"""
SELECT a.* FROM artifacts a JOIN runs r ON r.id=a.run_id WHERE {FILTER} ORDER BY a.run_id,a.id
""")
add('Q10','Checkpoint por época y selección histórica','train_execution_records, runs','JOIN por run_id; sólo artifact y selection.',
    '396 artefactos y 396 selecciones; cada época tiene evidencia, hash y tamaño.',f"""
SELECT t.* FROM train_execution_records t JOIN runs r ON r.id=t.run_id
WHERE {FILTER} AND t.kind IN ('artifact','selection')
ORDER BY t.run_id,t.kind,(t.payload->>'epoch')::integer NULLS LAST,t.phase,t.record_key
""")
add('Q11','Tiempos de eventos canónicos y cobertura de instrumentación','train_execution_records, runs',
    'JOIN por run_id; LATERAL convierte canonical_event (cadena JSON dentro de JSONB) a objeto.',
    '2044 eventos; identidad y secuencia; marcas occurred_at de emisión, no cronómetros de cómputo.',f"""
SELECT t.run_id,t.record_key,t.event_id,t.event_sequence,t.created_at,
 ev.j->>'event_id' AS canonical_event_id,ev.j->>'event_type' AS event_type,
 ev.j->>'occurred_at' AS occurred_at,ev.j->>'sequence' AS sequence,
 ev.j#>>'{{payload,legacy_record,kind}}' AS legacy_kind,
 ev.j#>>'{{payload,legacy_record,phase}}' AS legacy_phase,
 ev.j#>>'{{payload,legacy_record,record_key}}' AS legacy_key,
 (ev.j->'payload') - 'result' AS payload_context
FROM train_execution_records t JOIN runs r ON r.id=t.run_id
CROSS JOIN LATERAL (SELECT (t.payload->>'canonical_event')::jsonb AS j) ev
WHERE {FILTER} AND t.kind='e10_event'
ORDER BY t.run_id,(ev.j->>'sequence')::numeric
""")
add('Q12','Configuración realmente compilada y callbacks por fase','train_execution_records, runs',
    'JOIN por run_id; excluye model_json y architecture (grafo serializado), conserva configuración operativa.',
    '20 runtimes; identificar arquitectura por input_contract y optimizador por optimizer_class/config.',f"""
SELECT t.run_id,t.phase,t.record_key,t.created_at,t.payload-'model_json'-'architecture' AS payload
FROM train_execution_records t JOIN runs r ON r.id=t.run_id
WHERE {FILTER} AND t.kind='runtime' ORDER BY t.run_id,t.phase
""")
add('Q13','Cobertura de fuentes alternativas y tipos de registros','runs y tablas de evidencia',
    'Cada subconsulta hace JOIN por run_id; UNION ALL etiqueta fuentes, sin mezclar métricas.',
    'Explicitar fuentes vacías; no sustituir ausencias por ceros de entrenamiento.', '\nUNION ALL\n'.join(
    f"SELECT '{table}' AS source,count(*) AS rows FROM {table} t JOIN runs r ON r.id=t.run_id WHERE {FILTER}"
    for table in ['training_history','run_metrics','run_checkpoint_policy','execution_logs','environment_packages']) + f"\nUNION ALL\nSELECT 'records:'||t.kind||':'||t.phase,count(*) FROM train_execution_records t JOIN runs r ON r.id=t.run_id WHERE {FILTER} GROUP BY t.kind,t.phase ORDER BY source")
add('Q14','Integridad relacional y cardinalidades','campaign_members, campaign_attempts, runs, run_configurations, campaign_configurations, train_execution_sessions, evaluations, artifacts, run_clinical_metrics',
    'Subconsultas correlacionadas conservan cardinalidad; LEFT JOIN detecta huérfanos.',
    'Contadores de anomalías deben ser cero; 12 pares arquitectura/optimizador.',f"""
SELECT
 (SELECT count(*) FROM campaign_members WHERE campaign_id='{CAMPAIGN}') AS members,
 (SELECT count(*) FROM runs r WHERE {FILTER}) AS runs,
 (SELECT count(DISTINCT (rc.architecture,rc.optimizer)) FROM runs r JOIN run_configurations rc ON rc.run_id=r.id WHERE {FILTER}) AS unique_pairs,
 (SELECT count(*) FROM campaign_members cm LEFT JOIN campaign_attempts ca ON ca.id=cm.accepted_attempt_id
  WHERE cm.campaign_id='{CAMPAIGN}' AND (ca.id IS NULL OR ca.member_id<>cm.id)) AS invalid_accepted_attempts,
 (SELECT count(*) FROM campaign_attempts ca JOIN campaign_members cm ON cm.id=ca.member_id LEFT JOIN runs r ON r.id=ca.training_run_id
  WHERE cm.campaign_id='{CAMPAIGN}' AND (r.id IS NULL OR r.campaign_id<>cm.campaign_id)) AS invalid_run_links,
 (SELECT count(*) FROM runs r LEFT JOIN run_configurations rc ON rc.run_id=r.id WHERE {FILTER} AND rc.run_id IS NULL) AS missing_run_configurations,
 (SELECT count(*) FROM campaign_members cm LEFT JOIN campaign_configurations cc ON cc.campaign_id=cm.campaign_id AND cc.configuration_hash=cm.configuration_hash
  WHERE cm.campaign_id='{CAMPAIGN}' AND cc.campaign_id IS NULL) AS missing_campaign_configurations,
 (SELECT count(*) FROM runs r LEFT JOIN train_execution_sessions s ON s.run_id=r.id WHERE {FILTER} AND s.run_id IS NULL) AS missing_sessions,
 (SELECT count(*) FROM runs r WHERE {FILTER} AND NOT EXISTS
   (SELECT 1 FROM campaign_attempts ca JOIN campaign_members cm ON cm.id=ca.member_id WHERE ca.training_run_id=r.id AND cm.campaign_id=r.campaign_id)) AS unlinked_runs,
 (SELECT count(*) FROM evaluations e JOIN runs r ON r.id=e.training_run_id LEFT JOIN artifacts a ON a.id=e.checkpoint_artifact_id
  WHERE {FILTER} AND e.split='val' AND (a.id IS NULL OR a.run_id<>r.id OR e.dataset_version_id<>r.dataset_version_id)) AS invalid_evaluation_links,
 (SELECT count(*) FROM run_clinical_metrics m JOIN runs r ON r.id=m.run_id LEFT JOIN evaluations e ON e.id=m.evaluation_id
  WHERE {FILTER} AND (e.id IS NULL OR e.training_run_id<>r.id OR e.split<>m.split_name)) AS invalid_metric_links
""")
add('Q15','Inventario de evaluaciones existentes sin ejecutar ninguna','evaluations, runs','JOIN por training_run_id.',
    'Sólo VALIDATION histórica; esta consulta no ejecuta TEST ni EXPLAIN.',f"""
SELECT e.split,e.evaluation_role,count(*) AS rows FROM evaluations e JOIN runs r ON r.id=e.training_run_id
WHERE {FILTER} GROUP BY e.split,e.evaluation_role ORDER BY e.split,e.evaluation_role
""")
add('Q16','Metadatos del snapshot de lectura','PostgreSQL','Sin JOIN.',
    'Transacción REPEATABLE READ READ ONLY; versión de servidor y timestamp explícitos.',"""
SELECT current_database() AS database,version() AS server_version,
 current_setting('transaction_read_only') AS read_only,
 current_setting('transaction_isolation') AS isolation,transaction_timestamp() AS snapshot_at
""")

add('Q17','Validar métricas usando scores VALIDATION históricos del checkpoint','train_execution_records, runs, evaluations, artifacts',
    'JOIN evaluación final y su artefacto; predictions.payload.epoch=artifacts.metadata.epoch. Sólo scores ya persistidos de val.',
    '12 poblaciones de 2693; reconstruir matriz, ROC-AUC por rangos y AP por umbrales; sin cargar modelos ni ejecutar inferencia.',f"""
SELECT t.run_id,t.phase,t.record_key,t.created_at,e.id AS evaluation_id,
 a.id AS artifact_id,t.payload->>'epoch' AS epoch,t.payload->>'role' AS role,
 t.payload->'samples' AS samples
FROM train_execution_records t JOIN runs r ON r.id=t.run_id
JOIN evaluations e ON e.training_run_id=r.id AND e.split='val' AND e.evaluation_role='training_validation_final'
JOIN artifacts a ON a.id=e.checkpoint_artifact_id
WHERE {FILTER} AND t.kind='predictions' AND t.payload->>'role'='val'
AND (t.payload->>'epoch')::integer=(a.metadata->>'epoch')::integer ORDER BY t.run_id
""")
