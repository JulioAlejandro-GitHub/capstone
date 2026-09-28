"""Read-only, fail-closed E10 reservation capability check. Never runs migrations."""
from sqlalchemy.exc import SQLAlchemyError

from ..campaigns.contracts import CampaignError
from ..campaigns.repository import execute

E10_REVISION = '20260922_01'


class E10SchemaNotReady(CampaignError):
    """Stable public error with non-sensitive, actionable missing capabilities."""
    def __init__(self, missing):
        self.missing = tuple(missing)
        super().__init__('E10_SCHEMA_NOT_READY: ' + ', '.join(self.missing))


# Canonical expression from 20260922_01; a validated CHECK(true) is not enough.
EVENT_METADATA = """(((event_id IS NULL) AND (event_sequence IS NULL) AND
(kind <> 'e10_event'::text)) OR ((event_id IS NOT NULL) AND
(event_sequence IS NOT NULL) AND (event_sequence >= (1)::numeric) AND
(event_sequence = trunc(event_sequence)) AND
(event_sequence <> ALL (ARRAY['NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric])) AND
(kind = 'e10_event'::text) AND (phase = 'run_event_v1'::text) AND
(record_key = (event_id)::text) AND
(NOT (jsonb_typeof((payload -> 'canonical_event'::text)) IS DISTINCT FROM 'string'::text)) AND
((payload - 'canonical_event'::text) = '{}'::jsonb)))"""
# Fingerprint of the immutable migration's function body (pg_proc.prosrc).
# This checks the ownership/active-session/contiguous-sequence implementation,
# not just the presence of a function named train_event_guard. A replacement
# implementation, even at the same Alembic stamp, requires explicit review.
EVENT_GUARD_BODY_MD5 = 'd72ebe0d596f864bd42fcac85a91f9b1'

# Resolve through the connection's search_path, exactly as reservation SQL does.
# Objects in public cannot satisfy a missing object in a selected isolated schema.
CAPABILITIES = """
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
       = regexp_replace(:metadata, '[[:space:]]+', '', 'g')) AS event_metadata_constraint,
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
     AND md5(p.prosrc)=:guard_body
     AND p.prorettype='trigger'::regtype AND l.lanname='plpgsql'
     AND ('search_path=' || quote_ident(n.nspname) || ', pg_catalog')=ANY(p.proconfig)
  ) AS event_trigger_guard
"""


def require_e10_schema(connection):
    """Only SELECTs; also safe inside the caller's reservation transaction.

    This code supports the current Alembic head. Unknown/newer revisions fail
    closed until explicitly reviewed; a stamp alone is insufficient.
    """
    try:
        missing = []
        version_table = execute(connection, """SELECT EXISTS(
            SELECT 1 FROM pg_class v JOIN pg_class r ON r.relnamespace=v.relnamespace
            WHERE v.oid=to_regclass('alembic_version')
              AND r.oid=to_regclass('train_execution_records')
              AND v.relnamespace=(SELECT oid FROM pg_namespace WHERE nspname=current_schema()))""").scalar_one()
        versions = execute(connection, 'SELECT version_num FROM alembic_version').scalars().all() if version_table else []
        if versions != [E10_REVISION]:
            missing.append('alembic_revision_' + E10_REVISION)
        capabilities = dict(execute(connection, CAPABILITIES, metadata=EVENT_METADATA, guard_body=EVENT_GUARD_BODY_MD5).mappings().one())
        missing.extend(name for name, ready in capabilities.items() if not ready)
    except SQLAlchemyError:
        raise E10SchemaNotReady(['schema_inspection_failed']) from None
    if missing:
        raise E10SchemaNotReady(missing)
    return {'revision': E10_REVISION, **capabilities}
