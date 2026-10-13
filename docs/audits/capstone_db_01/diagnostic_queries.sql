\set ON_ERROR_STOP on
BEGIN READ ONLY;
SELECT jsonb_build_object('e10_capabilities',to_jsonb(x)) FROM (
SELECT
  (SELECT count(*) FROM pg_attribute
   WHERE attrelid=to_regclass('train_execution_records') AND NOT attisdropped
     AND NOT attnotnull AND atttypmod=-1 AND
     ((attname='event_id' AND atttypid='uuid'::regtype) OR
      (attname='event_sequence' AND atttypid='numeric'::regtype)))=2 AS event_columns,
  EXISTS(SELECT 1 FROM pg_constraint
   WHERE conrelid=to_regclass('train_execution_records')
     AND conname='train_event_metadata' AND contype='c' AND convalidated
     AND NOT connoinherit
     AND regexp_replace(pg_get_expr(conbin,conrelid), '[[:space:]]+', '', 'g')
       = regexp_replace('(((event_id IS NULL) AND (event_sequence IS NULL) AND
(kind <> ''e10_event''::text)) OR ((event_id IS NOT NULL) AND
(event_sequence IS NOT NULL) AND (event_sequence >= (1)::numeric) AND
(event_sequence = trunc(event_sequence)) AND
(event_sequence <> ALL (ARRAY[''NaN''::numeric, ''Infinity''::numeric, ''-Infinity''::numeric])) AND
(kind = ''e10_event''::text) AND (phase = ''run_event_v1''::text) AND
(record_key = (event_id)::text) AND
(NOT (jsonb_typeof((payload -> ''canonical_event''::text)) IS DISTINCT FROM ''string''::text)) AND
((payload - ''canonical_event''::text) = ''{}''::jsonb)))', '[[:space:]]+', '', 'g')) AS event_metadata_constraint,
  (SELECT count(*) FROM pg_index i
   WHERE indrelid=to_regclass('train_execution_records')
     AND indisunique AND indisvalid AND indisready AND indimmediate
     AND indexprs IS NULL AND indnatts=indnkeyatts AND
     ((indexrelid=to_regclass('train_event_id_unique')
       AND ARRAY(SELECT a.attname::text FROM unnest(i.indkey) WITH ORDINALITY k(n,pos)
         JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.n ORDER BY k.pos)
           = ARRAY['event_id']
       AND pg_get_expr(indpred,indrelid)='(event_id IS NOT NULL)') OR
      (indexrelid=to_regclass('train_event_sequence_unique')
       AND ARRAY(SELECT a.attname::text FROM unnest(i.indkey) WITH ORDINALITY k(n,pos)
         JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.n ORDER BY k.pos)
           = ARRAY['run_id','event_sequence']
       AND pg_get_expr(indpred,indrelid)='(event_sequence IS NOT NULL)')))=2 AS event_unique_indexes,
  EXISTS(SELECT 1 FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid
    JOIN pg_class r ON r.oid=t.tgrelid JOIN pg_namespace n ON n.oid=r.relnamespace
    JOIN pg_language l ON l.oid=p.prolang
   WHERE t.tgrelid=to_regclass('train_execution_records')
     AND t.tgname='a_train_event_guard' AND t.tgenabled IN ('O','A')
     AND NOT t.tgisinternal AND t.tgtype=7 AND t.tgqual IS NULL AND t.tgnargs=0
     AND p.proname='train_event_guard' AND p.pronamespace=r.relnamespace
     AND md5(p.prosrc)='d72ebe0d596f864bd42fcac85a91f9b1'
     AND p.prorettype='trigger'::regtype AND l.lanname='plpgsql'
     AND ('search_path=' || quote_ident(n.nspname) || ', pg_catalog')=ANY(p.proconfig)
  ) AS event_trigger_guard
) x;
SELECT jsonb_build_object('run_counts',jsonb_agg(to_jsonb(x))) FROM (SELECT run_type,status,count(*) FROM runs GROUP BY 1,2 ORDER BY 1,2) x;
SELECT jsonb_build_object('explain_counts',jsonb_build_object('explainability_results',(SELECT count(*) FROM explainability_results),'xai_evidence',(SELECT count(*) FROM xai_evidence),'xai_artifacts',(SELECT count(*) FROM xai_artifacts),'cell_explanations',(SELECT count(*) FROM cell_explanations),'explain_assessments',(SELECT count(*) FROM assessment_identities WHERE kind='explain')));
SELECT jsonb_build_object('explain_lineage',jsonb_agg(to_jsonb(x))) FROM (SELECT r.run_type,count(*) results,count(DISTINCT e.run_id) runs,count(*) FILTER (WHERE EXISTS(SELECT 1 FROM run_lineage l JOIN runs p ON p.id=l.parent_run_id WHERE l.child_run_id=e.run_id AND l.relationship_type='explains_checkpoint_from' AND p.run_type='training')) with_training_lineage FROM explainability_results e LEFT JOIN runs r ON r.id=e.run_id GROUP BY r.run_type) x;
SELECT jsonb_build_object('all_explain_run_links',jsonb_agg(to_jsonb(x))) FROM (SELECT r.status,l.relationship_type,l.confidence,p.run_type parent_type,count(*) FROM runs r LEFT JOIN run_lineage l ON l.child_run_id=r.id LEFT JOIN runs p ON p.id=l.parent_run_id WHERE r.run_type='explainability' GROUP BY 1,2,3,4) x;
SELECT jsonb_build_object('explain_unresolved_metadata',jsonb_agg(to_jsonb(x))) FROM (SELECT metadata->>'lineage_status' lineage_status,count(*) FROM runs WHERE run_type='explainability' GROUP BY 1) x;
SELECT jsonb_build_object('campaign_target',jsonb_agg(to_jsonb(x))) FROM (SELECT state,expected_count FROM experimental_campaigns WHERE id='2c1e1229-30e4-4815-81ec-9147a6816dfc') x;
SELECT jsonb_build_object('runtime_privileges',jsonb_agg(to_jsonb(x))) FROM (SELECT c.relname,has_table_privilege('capstone_v2_runtime',c.oid,'SELECT') can_select,has_table_privilege('capstone_v2_runtime',c.oid,'INSERT') can_insert,has_table_privilege('capstone_v2_runtime',c.oid,'UPDATE') can_update,has_table_privilege('capstone_v2_runtime',c.oid,'DELETE') can_delete FROM pg_class c WHERE c.relnamespace='public'::regnamespace AND c.relkind IN ('r','v','p') ORDER BY c.relname) x;
SELECT jsonb_build_object('v2_functions',jsonb_object_agg(p.proname,md5(pg_get_functiondef(p.oid)))) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND (p.proname LIKE 'v2_%' OR p.proname LIKE 'e04_%');
SELECT jsonb_build_object('v2_triggers',jsonb_agg(to_jsonb(x))) FROM (SELECT r.relname AS relation,t.tgname AS name,pg_get_triggerdef(t.oid) AS definition,t.tgenabled,t.tgdeferrable,t.tginitdeferred FROM pg_trigger t JOIN pg_class r ON r.oid=t.tgrelid JOIN pg_namespace n ON n.oid=r.relnamespace WHERE n.nspname='public' AND (t.tgname LIKE 'v2_%' OR t.tgname LIKE 'e04_%')) x;
SELECT jsonb_build_object('v2_evaluation_constraints',jsonb_agg(to_jsonb(x))) FROM (SELECT conname AS name,pg_get_constraintdef(oid) AS definition,condeferrable,condeferred,convalidated FROM pg_constraint WHERE conrelid='public.evaluations'::regclass) x;
SELECT jsonb_build_object('v2_calibration_indexes',jsonb_agg(to_jsonb(x))) FROM (SELECT c.relname AS name,pg_get_indexdef(i.indexrelid) AS definition,i.indisvalid,i.indisready,i.indisunique,i.indnullsnotdistinct FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid WHERE i.indrelid='public.evaluations'::regclass AND c.relname LIKE 'uq_e04_%') x;
COMMIT;
