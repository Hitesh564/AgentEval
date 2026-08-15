import pytest

import pytest

from agenteval.sdk.database import build_engine_options, database_backend_name, resolve_database_url


def test_resolve_database_url_defaults_to_local_sqlite(monkeypatch):
    monkeypatch.delenv("AGENTEVAL_DATABASE_URL", raising=False)
    assert resolve_database_url(None, allow_sqlite_fallback=True) == "sqlite:///./agenteval.db"


def test_resolve_database_url_normalizes_postgres_scheme():
    url = resolve_database_url("postgres://user:pass@localhost:5432/agenteval", allow_sqlite_fallback=False)
    assert url == "postgresql://user:pass@localhost:5432/agenteval"


def test_resolve_database_url_rejects_missing_production_url(monkeypatch):
    monkeypatch.delenv("AGENTEVAL_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError):
        resolve_database_url(None, allow_sqlite_fallback=False)


def test_build_engine_options_match_backend():
    sqlite_options = build_engine_options("sqlite:///./agenteval.db")
    assert sqlite_options["connect_args"]["check_same_thread"] is False
    assert database_backend_name("sqlite:///./agenteval.db") == "sqlite"

    postgres_options = build_engine_options("postgresql+psycopg2://user:pass@localhost:5432/agenteval")
    assert postgres_options["pool_pre_ping"] is True
    assert postgres_options["pool_size"] >= 1
    assert database_backend_name("postgresql+psycopg2://user:pass@localhost:5432/agenteval") == "postgresql"
