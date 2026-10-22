-- EXPLAIN from the report on the host GPU (docs/planning/explain_host_gpu_executor_design.md).
-- Applied as capstone_v2_migrator; the runtime role only reads and writes rows.
SET ROLE capstone_v2_migrator;

CREATE TABLE public.explain_requests (
 id uuid DEFAULT gen_random_uuid() NOT NULL,
 request jsonb NOT NULL,
 request_key text NOT NULL,
 actor text NOT NULL,
 executor text NOT NULL,
 state text DEFAULT 'queued' NOT NULL,
 claimed_by jsonb,
 operations jsonb DEFAULT '[]'::jsonb NOT NULL,
 cause text,
 created_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL,
 claimed_at timestamp with time zone,
 finished_at timestamp with time zone,
 CONSTRAINT explain_requests_pkey PRIMARY KEY (id),
 CONSTRAINT explain_requests_executor_check CHECK (executor = 'host_gpu'),
 CONSTRAINT explain_requests_state_check CHECK (state = ANY (ARRAY['queued', 'claimed', 'completed', 'failed', 'cancelled'])),
 CONSTRAINT explain_requests_key_check CHECK (request_key ~ '^[a-f0-9]{64}$'),
 CONSTRAINT explain_requests_claim_check CHECK ((state = 'queued') = (claimed_by IS NULL AND claimed_at IS NULL) OR state = 'cancelled'),
 CONSTRAINT explain_requests_finished_check CHECK ((state = ANY (ARRAY['completed', 'failed', 'cancelled'])) = (finished_at IS NOT NULL)),
 CONSTRAINT explain_requests_operations_check CHECK (jsonb_typeof(operations) = 'array')
);
-- A double click or a second tab never queues the same request twice while it is pending.
CREATE UNIQUE INDEX explain_requests_one_pending ON public.explain_requests (request_key) WHERE state = ANY (ARRAY['queued', 'claimed']);
CREATE INDEX explain_requests_queue ON public.explain_requests (created_at) WHERE state = 'queued';

CREATE TABLE public.executor_heartbeats (
 executor text NOT NULL,
 host text NOT NULL,
 process jsonb NOT NULL,
 device jsonb NOT NULL,
 started_at timestamp with time zone NOT NULL,
 last_seen timestamp with time zone DEFAULT clock_timestamp() NOT NULL,
 CONSTRAINT executor_heartbeats_pkey PRIMARY KEY (executor, host),
 CONSTRAINT executor_heartbeats_executor_check CHECK (executor = 'host_gpu'),
 CONSTRAINT executor_heartbeats_seen_check CHECK (last_seen >= started_at)
);

GRANT SELECT, INSERT, UPDATE ON TABLE public.explain_requests TO capstone_v2_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.executor_heartbeats TO capstone_v2_runtime;

RESET ROLE;
