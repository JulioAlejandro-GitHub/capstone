import ast
from pathlib import Path
from test_http_reporter_architecture import imports
SOURCE=Path(__file__).resolve().parents[1]/'src/malaria_dl'


def test_local_dependencies_do_not_move_database_or_science():
    for name in ('local_execution/worker.py','local_execution/agent.py','execution/reporters/http.py',
                 'local_execution/event_runtime.py','local_execution/event_journal.py'):
        for dependency in imports(SOURCE/name):
            assert not any(x in dependency for x in ('sqlalchemy','psycopg','PostgresResultRepository','ResultService','fastapi'))
    for name in ('execution/emitter.py','execution/journal.py','execution/train.py','execution/worker.py','execution/composition.py'):
        for dependency in imports(SOURCE/name):
            assert not any(x in dependency for x in ('sqlite3','SQLiteEventJournal','local_execution.event_journal'))


def test_agent_native_launch_and_heartbeat_remain_separate():
    tree=ast.parse((SOURCE/'local_execution/agent.py').read_text())
    heartbeat=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='heartbeat')
    assert 'done.wait(15)' in ast.unparse(heartbeat)
    assert not any(s in ast.unparse(heartbeat) for s in ('emitter','journal','RunEvent'))
    source=ast.unparse(tree)
    assert "[sys.executable, '-B', '-m', 'src.malaria_dl.local_execution.worker']" in source
    assert 'docker' not in source.lower()
