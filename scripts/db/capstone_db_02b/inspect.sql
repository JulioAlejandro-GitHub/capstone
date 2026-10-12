-- Manual read-only audit. Never called by application runtime.
BEGIN READ ONLY;
SELECT pg_get_functiondef('public.campaign_guard()'::regprocedure);
SELECT pg_get_triggerdef(oid) FROM pg_trigger
WHERE tgfoid='public.campaign_guard()'::regprocedure;
SELECT jsonb_build_object(
 'id',id, 'created_at',created_at, 'success',success, 'error_code',error_code,
 'consumer',after_state->>'consumer', 'dataset_version_id',after_state->>'dataset_version_id',
 'integrity_status',after_state->>'integrity_status',
 'required_splits',after_state->'required_splits',
 'physically_verified_splits',after_state->'physically_verified_splits',
 'snapshot_present',after_state ? 'snapshot')
FROM public.audit_events
WHERE event_type='ml.dataset_verification'
 AND after_state->>'dataset_version_id'='d8c0cab5-09dd-597f-9de7-7ca01aee2ec2'
ORDER BY created_at DESC LIMIT 10;
COMMIT;
