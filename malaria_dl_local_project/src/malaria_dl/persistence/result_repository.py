"""Durable E10 adapter. Composition is external to the application service."""
from collections.abc import Callable, Iterator
from contextlib import contextmanager
import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from ..execution.contracts import ExecutionContext, RunEvent
from ..results.errors import ResultError, ResultPersistenceError, WriterNotAuthorized, FinalEvaluationConflict
from ..results.training import TrainingResultsV1
from ..results.identity import canonical_event
from ..results.models import AcceptanceState
from ..results.repository import EventAcceptanceScope, ResultRepository
from .database import get_engine


def _query(connection: Connection, statement: str, **params):
    return connection.execute(text(statement), params)


def _decode(row) -> RunEvent | None:
    if row is None:
        return None
    try:
        canonical = row['payload']['canonical_event']
        event = RunEvent.from_dict(json.loads(canonical))
        if (canonical_event(event) != canonical or event.event_id != row['event_id']
                or event.run_id != row['run_id'] or event.sequence != row['event_sequence']
                or row['kind'] != 'e10_event' or row['phase'] != event.schema_version
                or row['record_key'] != str(event.event_id)):
            raise ValueError("inconsistent stored envelope")
        return event
    except (KeyError, TypeError, ValueError):
        raise ResultPersistenceError() from None


class _PostgresScope(EventAcceptanceScope):
    def __init__(self, connection: Connection, event: RunEvent, state: AcceptanceState):
        self._connection = connection
        self._event = event
        self._state = state
        self.active = True
        self.appended = False

    @property
    def state(self) -> AcceptanceState:
        if not self.active:
            raise ResultPersistenceError()
        return self._state

    def append(self) -> None:
        if not self.active or self.appended:
            raise ResultPersistenceError()
        event = self._event
        _query(self._connection, """INSERT INTO train_execution_records
            (run_id,kind,phase,record_key,payload,event_id,event_sequence)
            VALUES(:run,'e10_event',:schema,:key,CAST(:payload AS jsonb),:id,:sequence)""",
            run=event.run_id, schema=event.schema_version, key=str(event.event_id),
            payload=json.dumps({'canonical_event': canonical_event(event)}, ensure_ascii=True),
            id=event.event_id, sequence=event.sequence)
        self.appended = True

    def project_training_result(self, result: TrainingResultsV1) -> None:
        if not self.active or not self.appended or type(result) is not TrainingResultsV1:
            raise ResultPersistenceError()
        # Same connection/root transaction as append; the authorized session row
        # remains exclusively locked. Guard namespace as well as run identity.
        result = TrainingResultsV1.from_dict(result.to_dict())
        updated = _query(self._connection, """UPDATE runs
            SET parameters = parameters || jsonb_build_object('training_results', CAST(:result AS jsonb))
            WHERE id=:run AND jsonb_typeof(parameters)='object'
              AND NOT (parameters ? 'training_results')
            RETURNING id""", run=self._event.run_id,
            result=json.dumps(result.to_dict(), allow_nan=False, sort_keys=True)).first()
        if updated is None:
            raise FinalEvaluationConflict()


class PostgresResultRepository(ResultRepository):
    """Own a fresh top-level transaction per acceptance, never a caller savepoint.

    execution_token is the already trusted global fencing token supplied by the
    composition layer. context.owner must be the session owner, independently of
    runtime. The adapter performs no remote/internal owner translation.
    engine_factory must return an owned Engine; it is disposed after each scope.
    """
    def __init__(self, *, execution_token: UUID,
                 engine_factory: Callable[[], Engine] = get_engine) -> None:
        if not isinstance(execution_token, UUID):
            raise TypeError("execution_token must be UUID")
        self._execution_token = execution_token
        self._engine_factory = engine_factory

    @contextmanager
    def acceptance_scope(self, context: ExecutionContext, event: RunEvent) -> Iterator[EventAcceptanceScope]:
        engine = None
        scope = None
        try:
            engine = self._engine_factory()
            with engine.connect() as connection:
                if connection.in_transaction():
                    raise ResultPersistenceError()
                connection = connection.execution_options(isolation_level="READ COMMITTED")
                with connection.begin():
                    _query(connection, "SELECT set_config('capstone.execution_token',:token,true)", token=str(self._execution_token))
                    _query(connection, "SELECT set_config('capstone.train_owner',:owner,true)", owner=str(context.owner))
                    _query(connection, "SELECT experiment_require_owner()")
                    self._authorize(connection, context, event)
                    old = _query(connection, "SELECT * FROM train_execution_records WHERE event_id=:id", id=event.event_id).mappings().one_or_none()
                    at_sequence = _query(connection, "SELECT * FROM train_execution_records WHERE run_id=:run AND event_sequence=:sequence",
                                         run=context.run_id, sequence=event.sequence).mappings().one_or_none()
                    last = _query(connection, "SELECT coalesce(max(event_sequence),0) FROM train_execution_records WHERE run_id=:run",
                                  run=context.run_id).scalar_one()
                    scope = _PostgresScope(connection, event, AcceptanceState(
                        existing_event=_decode(old), sequence_event=_decode(at_sequence), last_sequence=int(last)))
                    try:
                        yield scope
                    finally:
                        scope.active = False
                # The root transaction is committed before the generator exits.
        except ResultError:
            raise
        except DBAPIError as exc:
            message = getattr(getattr(exc.orig, 'diag', None), 'message_primary', '')
            if message in {'TRAIN_OWNER_FENCED', 'GLOBAL_EXECUTION_OWNER_REQUIRED'}:
                raise WriterNotAuthorized() from None
            raise ResultPersistenceError() from None
        except SQLAlchemyError:
            raise ResultPersistenceError() from None
        finally:
            if engine is not None:
                engine.dispose()

    @staticmethod
    def _authorize(c: Connection, context: ExecutionContext, event: RunEvent) -> None:
        if context.run_id != event.run_id or context.attempt_id != event.attempt_id:
            raise WriterNotAuthorized()
        # Global gate first. NOWAIT avoids waiting in an inverted legacy lock order.
        initial = _query(c, "SELECT attempt_id FROM train_execution_sessions WHERE run_id=:run", run=context.run_id).first()
        if initial is None or initial.attempt_id != context.attempt_id:
            raise WriterNotAuthorized()
        member = campaign = attempt = None
        if initial.attempt_id is not None:
            lineage = _query(c, """SELECT a.member_id,m.campaign_id FROM campaign_attempts a
                JOIN campaign_members m ON m.id=a.member_id WHERE a.id=:id""", id=initial.attempt_id).first()
            if lineage is None:
                raise WriterNotAuthorized()
            campaign = _query(c, "SELECT * FROM experimental_campaigns WHERE id=:id FOR SHARE NOWAIT", id=lineage.campaign_id).mappings().one()
            member = _query(c, "SELECT * FROM campaign_members WHERE id=:id FOR SHARE NOWAIT", id=lineage.member_id).mappings().one()
            attempt = _query(c, "SELECT * FROM campaign_attempts WHERE id=:id FOR SHARE NOWAIT", id=initial.attempt_id).mappings().one()
        session = _query(c, "SELECT * FROM train_execution_sessions WHERE run_id=:run FOR UPDATE NOWAIT", run=context.run_id).mappings().one()
        run = _query(c, "SELECT * FROM runs WHERE id=:run FOR SHARE NOWAIT", run=context.run_id).mappings().one()
        config = session['configuration']
        if (session['owner'] != context.owner or session['state'] != 'active'
                or session['attempt_id'] != context.attempt_id
                or run['run_type'] != 'training' or run['status'] != 'running'
                or run['dataset_version_id'] != context.dataset_version_id
                or session['dataset']['dataset_version_id'] != str(context.dataset_version_id)
                or config['model_id'] != context.model_id or config['adapter_version'] != context.adapter_version):
            raise WriterNotAuthorized()
        if attempt is not None and (attempt['state'] != 'active' or attempt['training_run_id'] != context.run_id
                                    or member['state'] != 'active' or campaign['state'] not in ('active','paused')):
            raise WriterNotAuthorized()
        expected = {
            'campaign_id': campaign['id'] if campaign else None,
            'member_id': member['id'] if member else None,
            'configuration_hash': member['configuration_hash'] if member else None,
            'contract_hash': campaign['contract_hash'] if campaign else None,
        }
        if any(getattr(context, key) is not None and getattr(context, key) != value for key, value in expected.items()):
            raise WriterNotAuthorized()
