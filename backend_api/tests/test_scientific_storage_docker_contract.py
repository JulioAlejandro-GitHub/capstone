from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE_COMPOSE = ROOT / "docker-compose.yml"
OVERRIDE_COMPOSE = ROOT / "docker-compose.override.yml"


def _top_level_block(source: str, name: str) -> str:
    lines = source.splitlines()
    marker = f"{name}:"
    start = lines.index(marker)
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line and not line[0].isspace():
            break
        body.append(line)
    return "\n".join(body)


def _service_block(source: str, name: str) -> str:
    services = _top_level_block(source, "services")
    lines = services.splitlines()
    marker = f"  {name}:"
    start = lines.index(marker)
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("  ") and not line.startswith("    ") and line.strip():
            break
        body.append(line)
    return "\n".join(body)


def _service_child_block(service: str, name: str) -> str:
    lines = service.splitlines()
    marker = f"    {name}:"
    start = lines.index(marker)
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("    ") and not line.startswith("      ") and line.strip():
            break
        body.append(line)
    return "\n".join(body)


def _mounts(service: str) -> list[str]:
    try:
        volume_block = _service_child_block(service, "volumes")
    except ValueError:
        return []
    return [
        line.strip()[2:].split(" #", 1)[0].strip()
        for line in volume_block.splitlines()
        if line.strip().startswith("- ")
    ]


def _mount_parts(specification: str) -> tuple[str, str, tuple[str, ...]]:
    parts = specification.split(":")
    return parts[0], parts[1], tuple(parts[2:])


def test_compose_declares_one_private_read_write_scientific_volume_for_backend():
    base = BASE_COMPOSE.read_text(encoding="utf-8")
    override = OVERRIDE_COMPOSE.read_text(encoding="utf-8")
    declared_volumes = _top_level_block(base, "volumes")

    assert declared_volumes.count("  postgres_data:") == 1
    assert declared_volumes.count("  scientific_storage:") == 1
    assert "external:" not in declared_volumes
    assert "name:" not in declared_volumes
    assert "capstone-development_storage" not in base + override

    backend_base = _service_block(base, "backend")
    backend_override = _service_block(override, "backend")
    environment = _service_child_block(backend_base, "environment")
    assert environment.count("      STORAGE_PROVIDER: local") == 1
    assert environment.count("      STORAGE_ROOT: /app/var/storage") == 1
    assert "STORAGE_ROOT" not in backend_override
    assert "STORAGE_PROVIDER" not in backend_override

    mounts = _mounts(backend_base) + _mounts(backend_override)
    parsed = [_mount_parts(mount) for mount in mounts]
    storage_mounts = [mount for mount in parsed if mount[1] == "/app/var/storage"]
    assert storage_mounts == [
        ("scientific_storage", "/app/var/storage", ()),
    ]
    assert "ro" not in storage_mounts[0][2]
    destinations = [mount[1] for mount in parsed]
    assert len(destinations) == len(set(destinations))
    assert "/app" not in destinations
    assert not any(
        source.startswith(".") and "storage" in destination
        for source, destination, _ in parsed
    )

    for service_name in ("db", "frontend"):
        service_text = _service_block(base, service_name)
        if service_name in override:
            service_text += _service_block(override, service_name)
        assert "scientific_storage" not in service_text

    db_mounts = _mounts(_service_block(base, "db"))
    assert db_mounts == ["postgres_data:/var/lib/postgresql/data"]


def test_scientific_roots_are_excluded_from_build_context_and_future_git_adds():
    dockerignore = set((ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines())
    assert {
        "var/storage",
        "var/storage/**",
        "backend_api/var/storage",
        "backend_api/var/storage/**",
    } <= dockerignore

    gitignore = set((ROOT / ".gitignore").read_text(encoding="utf-8").splitlines())
    namespaces = {
        "microscopy-images",
        "cell-crops",
        "cell-explanations",
        "model-explanations",
        ".staging",
    }
    expected = {
        f"/{root}/{namespace}/"
        for root in ("var/storage", "backend_api/var/storage")
        for namespace in namespaces
    }
    assert expected <= gitignore


def test_dockerfile_prepares_empty_mountpoint_for_non_root_user():
    dockerfile = (ROOT / "backend_api" / "Dockerfile").read_text(encoding="utf-8")
    assert "mkdir -p /app/var/storage" in dockerfile
    assert "chown -R capstone:capstone /app" in dockerfile
    assert "USER capstone" in dockerfile
