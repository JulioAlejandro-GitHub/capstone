"""Client/server boundaries for the parallel E10 HTTP path."""
import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'src/malaria_dl'
ROOT = SOURCE.parents[2]


def imports(path):
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            yield (node.module or '') + '.' + '.'.join(alias.name for alias in node.names)


def test_clients_have_no_sql_or_server_imports():
    files = ['execution/reporters/http.py'] + ['local_execution/' + name + '.py' for name in
        ('agent', 'worker', 'transport', 'event_transport', 'event_client', 'storage', 'processes')]
    for name in files:
        for dependency in imports(SOURCE / name):
            assert not any(word in dependency for word in
                ('psycopg', 'sqlalchemy', 'ResultService', 'PostgresResultRepository',
                 'fastapi', 'event_backend', 'event_context', 'get_engine'))


def test_resolver_is_read_only_and_route_has_no_sql():
    tree = ast.parse((SOURCE / 'local_execution/event_context.py').read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert not any(word in node.value.upper() for word in
                ('INSERT INTO', 'UPDATE ', 'DELETE FROM', 'TRAIN_EXECUTION_RECORDS'))
    route = ROOT / 'backend_api/app/routes/local_execution.py'
    assert not any('psycopg' in name or 'sqlalchemy' in name for name in imports(route))


def test_domain_and_runtime_stay_disconnected():
    for path in (SOURCE / 'results').glob('*.py'):
        assert not any(word in name for name in imports(path) for word in ('fastapi', 'HttpRunReporter'))
    for name in ('execution/train.py', 'local_execution/worker.py', 'local_execution/agent.py'):
        assert not any(word in name for name in imports(SOURCE / name)
                       for word in ('reporters', 'event_client', 'event_backend', 'event_transport'))
