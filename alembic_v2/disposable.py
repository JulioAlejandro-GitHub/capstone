"""C2.12-only provisioning checks. No scientific or SQL authorization overrides."""
from __future__ import annotations

import json
import os
import re
import subprocess
from urllib.parse import unquote, urlsplit
from uuid import UUID

from alembic_v2.safety import MIGRATOR, require


def validate_target(target: dict) -> None:
    nonce = str(UUID(target['isolation_id']))
    require(target['authorized_stage'] == 'C2.12.2', 'C212_STAGE')
    require(target['database'] == 'capstone_c212_' + UUID(nonce).hex, 'C212_NAME')
    require(target['protected_database'] == 'malaria_experiments', 'C212_PROTECTED_DATABASE')
    require(target['database'] != target['protected_database'], 'C212_PROTECTED_TARGET')
    require(target['created_by_run'] == nonce, 'C212_CREATOR')
    require(target['database_owner'] == MIGRATOR, 'C212_OWNER')
    require(target['provision_admin'] == 'julio', 'C212_ADMIN')
    require(type(target['database_oid']) is int and target['database_oid'] > 0,
            'C212_OID')
    require(type(target['protected_database_oid']) is int
            and target['protected_database_oid'] != target['database_oid'], 'C212_PROTECTED_OID')
    require(re.fullmatch('[0-9a-f]{64}', target['container_id']), 'C212_CONTAINER')
    require(target['postgres_system_identifier'] == '7691366089693499436', 'C212_INSTANCE')
    require(target['host_port'] == 5432, 'C212_PORT')
    require(type(target['runner_pid']) is int and target['runner_pid'] > 1, 'C212_RUNNER')
    os.kill(target['runner_pid'], 0)


def validate_authorization(target: dict, url: str) -> None:
    validate_target(target)
    parsed = urlsplit(url)
    require(parsed.scheme == 'postgresql+psycopg' and parsed.hostname == '127.0.0.1'
            and parsed.port == target['host_port'] and unquote(parsed.username or '') == target['provision_admin']
            and unquote(parsed.path) == '/' + target['database']
            and not parsed.query and not parsed.fragment, 'C212_CONNECTION_TARGET')


def assume_migration_identity(connection: object, target: dict) -> None:
    """Existing admin authenticates, then relinquishes authority for the migration.

    SET SESSION AUTHORIZATION changes both current_user and session_user. The
    unchanged downstream role checks still require the non-superuser migrator.
    No role, password, membership or database privilege is created or altered.
    """
    verify_created_database(target)
    row = connection.exec_driver_sql("""SELECT current_database() AS database,
        session_user AS role, (SELECT rolsuper FROM pg_roles WHERE rolname=session_user) AS admin,
        (SELECT oid::bigint FROM pg_database WHERE datname=current_database()) AS oid""").mappings().one()
    require(row['database'] == target['database'] and row['oid'] == target['database_oid']
            and row['role'] == target['provision_admin'] and row['admin'], 'C212_ADMIN_SESSION')
    connection.exec_driver_sql('SET SESSION AUTHORIZATION capstone_v2_migrator')


def validate_container(target: dict, container: dict, volume: dict, others: list) -> None:
    validate_target(target)
    require(container['Id'] == target['container_id'] and container['State']['Running'],
            'C212_CONTAINER_IDENTITY')
    labels = container['Config']['Labels']
    require(labels.get('com.docker.compose.project') == 'capstone-malaria'
            and labels.get('com.docker.compose.service') == 'db', 'C212_COMPOSE_IDENTITY')
    require(not container['HostConfig'].get('Privileged')
            and not container['HostConfig'].get('VolumesFrom'), 'C212_CONTAINER_MODE')
    require(container['NetworkSettings']['Ports'] == {
        '5432/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '5432'}]}, 'C212_PORT_BINDING')
    mounts = container['Mounts']
    require(len(mounts) == 1 and mounts[0]['Name'] == target['volume']
            and mounts[0]['Destination'] == '/var/lib/postgresql/data'
            and mounts[0]['Type'] == 'volume' and mounts[0]['RW'], 'C212_VOLUME')
    require(volume['Name'] == target['volume']
            and volume['Mountpoint'] == mounts[0]['Source'], 'C212_VOLUME_IDENTITY')
    require(all(not any(m.get('Name') == target['volume']
                        or m.get('Source') == mounts[0]['Source'] for m in c.get('Mounts', []))
                for c in others if c['Id'] != container['Id']), 'C212_SHARED_VOLUME')


def verify_created_database(target: dict) -> None:
    validate_target(target)
    # Only validated UUID-derived names reach this SQL; all other values are
    # compared outside SQL. Administrator credentials stay inside the container.
    query = """BEGIN READ ONLY;
    SELECT json_build_object('system_identifier', (SELECT system_identifier::text FROM pg_control_system()),
      'oid',d.oid::bigint,'owner',pg_get_userbyid(d.datdba),
      'marker',shobj_description(d.oid,'pg_database'),
      'protected_oid',(SELECT oid::bigint FROM pg_database WHERE datname='malaria_experiments'))
    FROM pg_database d WHERE datname='%s'; ROLLBACK;""" % target['database']
    result = subprocess.run(['docker', 'exec', '-i', target['container_id'], 'sh', '-c',
        'psql -X -qAt -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1'],
        input=query, text=True, capture_output=True, timeout=15)
    require(result.returncode == 0, 'C212_ADMIN_IDENTITY_UNAVAILABLE')
    row = json.loads(result.stdout)
    require(row == dict(system_identifier=target['postgres_system_identifier'],
                        oid=target['database_oid'], owner=MIGRATOR,
                        marker='C2.12.2:' + target['created_by_run'],
                        protected_oid=target['protected_database_oid']), 'C212_CREATED_IDENTITY')
