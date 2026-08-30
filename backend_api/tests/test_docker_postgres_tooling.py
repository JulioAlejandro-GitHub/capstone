from __future__ import annotations

import os
import re
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DB_SCRIPTS = ROOT / "scripts" / "db"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _compose_service(source: str, name: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(name)}:\n(?P<body>.*?)(?=^  [a-zA-Z0-9_-]+:|\Z)",
        source,
    )
    assert match is not None
    return match.group("body")


def _fake_docker(tmp_path: Path) -> Path:
    docker = tmp_path / "docker"
    docker.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf '%s|%s\\n' \"$PWD\" \"$*\" >> \"$DOCKER_LOG\"\n"
        "if [[ \"$*\" == *'exec -T backend python -'* ]]; then\n"
        "  cat >/dev/null\n"
        "  printf 'canonical_user\\ncanonical_database\\n'\n"
        "elif [[ \"$*\" == *psql* ]]; then\n"
        "  printf 'canonical_user|canonical_database\\n'\n"
        "elif [[ \"$*\" == *pg_dump* ]]; then\n"
        "  [[ \"${FAKE_DUMP_FAIL:-0}\" != 1 ]] || exit 9\n"
        "  [[ \"${FAKE_EMPTY:-0}\" == 1 ]] || printf 'fake-custom-dump'\n"
        "elif [[ \"$*\" == *pg_restore* ]]; then\n"
        "  cat >/dev/null\n"
        "  [[ \"${FAKE_RESTORE_FAIL:-0}\" != 1 ]] || exit 8\n"
        "  for table in alembic_version runs run_lineage model_versions stage2_model_publications deployed_model_versions; do\n"
        "    printf '1; 0 0 TABLE public %s owner\\n' \"$table\"\n"
        "    printf '2; 0 0 TABLE DATA public %s owner\\n' \"$table\"\n"
        "  done\n"
        "  printf '3; 0 0 INDEX public example owner\\n'\n"
        "fi\n",
        encoding="utf-8",
    )
    docker.chmod(docker.stat().st_mode | stat.S_IXUSR)
    return docker


def test_common_resolves_repository_root_from_another_directory(tmp_path):
    result = subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"; cd "$2"; printf "%s" "$CAPSTONE_ROOT"',
            "bash",
            str(DB_SCRIPTS / "common.sh"),
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout == str(ROOT)


def test_backup_uses_canonical_backend_identity_and_atomic_validated_output(tmp_path):
    _fake_docker(tmp_path)
    log = tmp_path / "docker.log"
    backup_dir = tmp_path / "backups"
    environment = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "DOCKER_LOG": str(log),
        "CAPSTONE_BACKUP_DIR": str(backup_dir),
        "DATABASE_URL": "postgresql+psycopg://canonical_user:must-not-appear@db:5432/canonical_database",
        "POSTGRES_USER": "stale_postgres_user",
        "POSTGRES_DB": "stale_postgres_database",
    }
    success = subprocess.run(
        ["bash", str(DB_SCRIPTS / "backup.sh")],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert success.returncode == 0, success.stderr
    assert "must-not-appear" not in success.stdout + success.stderr
    assert "stale_postgres_user" not in success.stdout + success.stderr
    assert "stale_postgres_database" not in success.stdout + success.stderr
    log_text = log.read_text(encoding="utf-8")
    assert "exec -T backend python -" in log_text
    assert f"{ROOT}|compose exec -T db" in log_text
    assert "pg_dump" in log_text and "pg_restore --list" in log_text
    assert "--username=\"$1\"" in log_text
    assert "--dbname=\"$2\"" in log_text
    assert "--no-password" in log_text
    assert "stale_postgres_user" not in log_text
    assert "stale_postgres_database" not in log_text
    backup = next(backup_dir.glob("*.dump"))
    assert backup.stat().st_size > 0
    assert stat.S_IMODE(backup.stat().st_mode) == 0o600

    empty_environment = {
        **environment,
        "CAPSTONE_BACKUP_DIR": str(tmp_path / "empty-backups"),
        "FAKE_EMPTY": "1",
    }
    empty = subprocess.run(
        ["bash", str(DB_SCRIPTS / "backup.sh")],
        cwd=tmp_path,
        env=empty_environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert empty.returncode != 0
    assert not list((tmp_path / "empty-backups").glob("*.dump"))

    previous_dir = tmp_path / "failed-backups"
    previous_dir.mkdir()
    previous = previous_dir / "previous.dump"
    previous.write_bytes(b"previous-valid-backup")
    failed_environment = {
        **environment,
        "CAPSTONE_BACKUP_DIR": str(previous_dir),
        "FAKE_DUMP_FAIL": "1",
    }
    failed = subprocess.run(
        ["bash", str(DB_SCRIPTS / "backup.sh")],
        cwd=tmp_path,
        env=failed_environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert failed.returncode != 0
    assert previous.read_bytes() == b"previous-valid-backup"
    assert list(previous_dir.glob(".capstone_*.tmp")) == []
    assert list(previous_dir.glob("capstone_*.dump")) == []

    restore_dir = tmp_path / "restore-failure"
    restore_environment = {
        **environment,
        "CAPSTONE_BACKUP_DIR": str(restore_dir),
        "FAKE_RESTORE_FAIL": "1",
    }
    restore_failure = subprocess.run(
        ["bash", str(DB_SCRIPTS / "backup.sh")],
        cwd=tmp_path,
        env=restore_environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert restore_failure.returncode != 0
    assert not list(restore_dir.glob("*.dump"))
    assert not list(restore_dir.glob(".*.tmp"))


def test_backup_source_has_no_legacy_identity_or_host_postgres_fallbacks():
    backup = _source(DB_SCRIPTS / "backup.sh")
    makefile = _source(ROOT / "Makefile")

    assert "get_settings" in backup
    assert "get_primary_engine" in backup
    assert "current_user" in backup and "current_database()" in backup
    assert "configured_user" in backup and "configured_database" in backup
    assert "$POSTGRES_USER" not in backup
    assert "$POSTGRES_DB" not in backup
    assert "--no-password" in backup
    assert "pg_dump" in backup and "compose exec -T db" in backup
    assert "pg_restore --list" in backup
    assert "localhost" not in backup and "127.0.0.1" not in backup
    assert "julio" not in backup and "malaria_experiments" not in backup
    assert "db-backup:\n\t./scripts/db/backup.sh" in makefile


def test_status_migration_and_cleanup_are_backend_docker_only():
    status = _source(DB_SCRIPTS / "status.sh")
    migration = _source(DB_SCRIPTS / "migrate.sh")
    cleanup = _source(DB_SCRIPTS / "test_schema_clean.sh")

    assert "compose exec -T backend python" in status
    assert not any(
        keyword in status.upper()
        for keyword in ("INSERT ", "UPDATE ", "DELETE ", "TRUNCATE ", "DROP ", "CREATE ")
    )
    assert "compose exec -T backend python -m alembic current" in migration
    assert "compose exec -T backend python -m alembic heads" in migration
    assert "python_bin" not in migration
    assert "TEST_EXECUTION=true" in cleanup
    assert "assert_safe_temporary_schema" in cleanup
    assert "assert_capstone_database" in cleanup

    purge = _source(DB_SCRIPTS / "purge.sh")
    assert '"$CAPSTONE_ROOT/scripts/db/backup.sh"' in purge
    assert "compose \"${compose_arguments[@]}\" backend" in purge


def test_makefile_and_ci_do_not_select_local_postgres():
    makefile = _source(ROOT / "Makefile")
    workflow = _source(ROOT / ".github" / "workflows" / "ci.yml")
    retired_marker = "requires_" + "local_postgres"

    assert "docker compose exec -T backend" in makefile
    assert "requires_docker_postgres" in makefile
    assert retired_marker not in makefile
    assert retired_marker not in workflow
    assert "@db:5432/" in workflow
    assert "127.0.0.1" not in workflow
    assert "createdb" not in makefile and "dropdb" not in makefile


def test_development_compose_uses_granular_backend_mounts():
    override = _source(ROOT / "docker-compose.override.yml")
    backend = _compose_service(override, "backend")
    base = _source(ROOT / "docker-compose.yml")
    db = _compose_service(base, "db")

    expected_mounts = {
        "./backend_api/app:/app/app",
        "./backend_api/tests:/app/tests",
        "./alembic:/app/alembic:ro",
        "./alembic.ini:/app/alembic.ini:ro",
        "./pytest.ini:/app/pytest.ini:ro",
        "./malaria_dl_local_project:/app/malaria_dl_local_project:ro",
        "./malaria_dl_local_project/releases:/app/malaria_dl_local_project/releases",
        "./malaria_dataset_split_project/src:/app/malaria_dataset_split_project/src:ro",
    }
    declared_mounts = {
        match.group(1)
        for match in re.finditer(r"(?m)^\s*-\s+(\./[^\s#]+)\s*$", backend)
    }
    assert expected_mounts <= declared_mounts
    assert not any(mount.split(":", 1)[1] == "/app" for mount in declared_mounts)
    destinations = [mount.split(":", 2)[1] for mount in declared_mounts]
    assert len(destinations) == len(set(destinations))
    assert "configs:" not in backend
    assert not re.search(r"(?m)^configs:\s*$", override)
    assert not re.search(r"(?m)^\s+ports:\s*$", db)
    assert "/var/lib/postgresql/data" in db
    assert not (ROOT / "backend_api" / "alembic.ini").exists()
    duplicate_tree = ROOT / "backend_api" / "alembic"
    assert not duplicate_tree.exists() or not any(
        path.is_file() for path in duplicate_tree.rglob("*")
    )


def test_obsolete_database_lifecycle_scripts_are_absent():
    for name in (
        "test_db_up.sh",
        "test_db_down.sh",
        "test_db_wait.sh",
        "test_db_reset.sh",
        "test_db_bootstrap.sh",
        "test_db_status.sh",
    ):
        assert not (ROOT / "scripts" / name).exists()

    legacy_scripts = ROOT / "malaria_dl_local_project" / "scripts"
    assert not (legacy_scripts / "test_db.py").exists()
    init_source = _source(legacy_scripts / "init_db.py")
    assert "Comando retirado" in init_source
    assert "createdb" not in init_source
