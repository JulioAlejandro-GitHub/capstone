"""Run the changed read services with PostgreSQL enforcing read-only transactions."""
import json
import os
import sys
os.environ['PGOPTIONS'] = '-c default_transaction_read_only=on'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path[:0] = ['/tmp/capstone-db02a/backend_api', '/tmp/capstone-db02a/malaria_dl_local_project']
from sqlalchemy import text
from app.db import read_only_transaction
from app.services.training_summaries import list_training_summaries
from app.services.lineage_children import get_training_lineage_children
try:
    with read_only_transaction('malaria') as c:
        assert c.execute(text('SELECT current_database()')).scalar_one() == 'malaria_experiments'
        assert c.execute(text('SHOW transaction_read_only')).scalar_one() == 'on'
    summary = list_training_summaries('malaria', 100)
    counts = []
    for row in summary.items:
        children = get_training_lineage_children(row.run_id, 'malaria', 100)
        assert row.evaluation_count == children.evaluation_count == len(children.evaluations)
        assert row.explainability_count == children.explainability_count == len(children.explainabilities)
        assert not children.truncated
        assert all(x.source_kind == 'assessment_explain_e6' and x.state == 'verified' and x.method for x in children.explainabilities)
        counts.append({'evaluate': children.evaluation_count, 'explain': children.explainability_count})
    assert len(counts) == 14
    assert counts.count({'evaluate': 1, 'explain': 2}) == 1
    assert counts.count({'evaluate': 0, 'explain': 0}) == 13
    print(json.dumps({'status': 'PASS', 'trainings': len(counts), 'counts': counts, 'read_only': True, 'services': ['list_training_summaries', 'get_training_lineage_children']}))
except Exception as exc:
    print(json.dumps({'status': 'FAIL', 'exception_class': type(exc).__name__, 'sqlstate': getattr(getattr(exc, 'orig', exc), 'sqlstate', None)}))
    raise SystemExit(1)
