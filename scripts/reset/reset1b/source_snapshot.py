"""Operational connection is always READ ONLY; no service mutations or DDL."""
import json
from sqlalchemy import text
from src.malaria_dl.persistence.database import get_engine
from common import fingerprint,catalog,require
with get_engine().connect().execution_options(postgresql_readonly=True,isolation_level='REPEATABLE READ') as c:
    with c.begin():
        require(c.execute(text('SELECT current_database(),current_schema(),session_user')).one()==('malaria_experiments','public','julio'),'CANONICAL_SOURCE_MISMATCH')
        schemas=c.execute(text("SELECT nspname FROM pg_namespace WHERE nspname='public' OR nspname LIKE 'capstone_test_%' ORDER BY nspname")).scalars().all()
        out={'at':str(c.execute(text('SELECT clock_timestamp()')).scalar_one()),'readonly':c.execute(text("SELECT current_setting('transaction_read_only')")).scalar_one(),'schemas':{s:fingerprint(c,s) for s in schemas},'catalog':catalog(c,'public')}
print(json.dumps(out,default=str))
