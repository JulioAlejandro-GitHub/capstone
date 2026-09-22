"""Client composition shared by Local TRAIN and explicit transport recovery."""
from ..execution.reporters.http import HttpRunReporter
from .event_transport import RemoteExecutionIdentity
from .transport import Api


def build_http_run_reporter(url: str, bearer: str, identity: RemoteExecutionIdentity,
                            *, timeout=15) -> HttpRunReporter:
    return HttpRunReporter(Api(url, bearer, timeout=timeout), identity)
