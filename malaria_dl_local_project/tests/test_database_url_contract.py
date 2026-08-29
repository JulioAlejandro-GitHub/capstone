import pytest

from src.malaria_dl.persistence import database


PASSWORD = "fictional-password"


@pytest.fixture(autouse=True)
def _do_not_load_project_dotenv(monkeypatch):
    monkeypatch.setattr(database, "load_environment", lambda: None)


@pytest.mark.parametrize("database_url", [None, "", "   "])
def test_database_url_is_required(monkeypatch, database_url):
    if database_url is None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("DATABASE_URL", database_url)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        database.get_database_url()


def test_plain_postgresql_url_is_normalized_and_query_is_preserved(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        f"postgresql://user:{PASSWORD}@db:5432/capstone?sslmode=require&application_name=unit",
    )
    assert database.get_database_url() == (
        f"postgresql+psycopg://user:{PASSWORD}@db:5432/capstone"
        "?sslmode=require&application_name=unit"
    )


def test_psycopg_url_is_accepted_unchanged(monkeypatch):
    database_url = f"postgresql+psycopg://user:{PASSWORD}@db:5432/capstone"
    monkeypatch.setenv("DATABASE_URL", database_url)
    assert database.get_database_url() == database_url


@pytest.mark.parametrize(
    "database_url",
    [
        f"postgresql://user:{PASSWORD}@localhost:5432/capstone",
        f"postgresql://user:{PASSWORD}@127.0.0.1:5432/capstone",
        f"postgresql://user:{PASSWORD}@[::1]:5432/capstone",
        f"postgresql://user:{PASSWORD}@host.docker.internal:5432/capstone",
        f"postgresql://user:{PASSWORD}@other:5432/capstone",
        "postgresql:///capstone",
        f"postgresql://user:{PASSWORD}@db:55432/capstone",
    ],
)
def test_non_docker_database_targets_are_rejected(monkeypatch, database_url):
    monkeypatch.setenv("DATABASE_URL", database_url)
    with pytest.raises(RuntimeError) as error:
        database.get_database_url()
    assert PASSWORD not in str(error.value)


@pytest.mark.parametrize(
    "variables",
    [
        {
            "DB_HOST": "db",
            "DB_PORT": "5432",
            "DB_NAME": "capstone",
            "DB_USER": "user",
            "DB_PASSWORD": PASSWORD,
        },
        {
            "DATABASE_HOST": "db",
            "DATABASE_PORT": "5432",
            "DATABASE_NAME": "capstone",
            "DATABASE_USER": "user",
            "DATABASE_PASSWORD": PASSWORD,
        },
    ],
)
def test_partial_variables_do_not_create_a_fallback(monkeypatch, variables):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    for name, value in variables.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        database.get_database_url()
