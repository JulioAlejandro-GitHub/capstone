-- DBV2.2 + approved R1. Install exclusively via guarded Alembic v2.
INSERT INTO public.experiment_execution_gate (singleton, owner, db_pid, process_evidence, blocked_reason) VALUES (TRUE, NULL, NULL, CAST('{}' AS jsonb), NULL);

