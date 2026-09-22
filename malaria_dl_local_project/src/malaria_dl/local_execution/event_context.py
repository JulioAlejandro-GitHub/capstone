"""Backend-only, read-only resolution of persisted Local execution identity."""
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..execution.contracts import ExecutionContext, ExecutionMode
from ..persistence.database import get_engine
from ..results.errors import ResultPersistenceError, WriterNotAuthorized
from .event_transport import RemoteExecutionIdentity


@dataclass(frozen=True, slots=True)
class ResolvedLocalExecution:
    context: ExecutionContext
    execution_token: UUID


class LocalExecutionContextResolver:
    def __init__(self, engine_factory=get_engine):
        self.engine_factory = engine_factory

    def resolve(self, identity: RemoteExecutionIdentity, principal: str) -> ResolvedLocalExecution:
        engine = None
        try:
            engine = self.engine_factory()
            with engine.connect() as connection, connection.begin():
                connection.execute(text('SET TRANSACTION READ ONLY'))
                return self.resolve_on_connection(connection, identity, principal)
        except SQLAlchemyError:
            raise ResultPersistenceError() from None
        finally:
            if engine is not None:
                engine.dispose()

    def resolve_on_connection(self, connection, identity, principal, *, lock_job=False):
        # At acceptance the E10 repository already holds gate/session/lineage
        # locks. Lock the job too, preventing identity edits through commit.
        job = connection.execute(text('SELECT * FROM local_execution_jobs WHERE id=:id'
            + (' FOR SHARE NOWAIT' if lock_job else '')), {'id': identity.job_id}).mappings().one_or_none()
        if (job is None or job['principal'] != principal or job['agent_id'] != identity.agent_id
                or job['state'] not in ('held', 'calculation_reported') or job['run_id'] is None):
            raise WriterNotAuthorized()
        row = connection.execute(text('''SELECT s.*, r.dataset_version_id AS run_dataset,
            a.training_run_id, m.id AS member_id, m.campaign_id, m.configuration_hash,
            c.contract_hash FROM train_execution_sessions s
            JOIN runs r ON r.id=s.run_id
            JOIN campaign_attempts a ON a.id=s.attempt_id
            JOIN campaign_members m ON m.id=a.member_id
            JOIN experimental_campaigns c ON c.id=m.campaign_id
            WHERE s.run_id=:run'''), {'run': job['run_id']}).mappings().one_or_none()
        try:
            snapshot = job['session']
            if (row is None or row['state'] != 'active'
                    or row['training_run_id'] != job['run_id']
                    or row['campaign_id'] != job['campaign_id']
                    or snapshot['run_id'] != str(row['run_id'])
                    or snapshot['attempt_id'] != str(row['attempt_id'])
                    or snapshot['owner'] != str(row['owner'])
                    or snapshot['configuration'] != row['configuration']
                    or snapshot['dataset'] != row['dataset']
                    or row['dataset']['dataset_version_id'] != str(row['run_dataset'])):
                raise WriterNotAuthorized()
            context = ExecutionContext(
                run_id=row['run_id'], attempt_id=row['attempt_id'], owner=row['owner'],
                execution_mode=ExecutionMode.LOCAL_PYTHON,
                dataset_version_id=row['run_dataset'], model_id=row['configuration']['model_id'],
                adapter_version=row['configuration']['adapter_version'],
                campaign_id=row['campaign_id'], member_id=row['member_id'],
                configuration_hash=row['configuration_hash'], contract_hash=row['contract_hash'])
            return ResolvedLocalExecution(context, job['owner'])
        except (KeyError, TypeError, ValueError):
            raise WriterNotAuthorized() from None
