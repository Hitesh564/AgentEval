from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from sqlalchemy.pool import NullPool

DEFAULT_SQLITE_URL = "sqlite:///./agenteval.db"
DATABASE_URL_ENV = "AGENTEVAL_DATABASE_URL"


def normalize_database_url(value: str) -> str:
    text = str(value).strip().strip('"').strip("'")
    if text.startswith("postgres://"):
        return "postgresql://" + text[len("postgres://") :]
    return text


def _path_to_sqlite_url(value: str) -> str:
    path = Path(value).expanduser()
    if path.is_absolute():
        return f"sqlite:///{path.as_posix()}"
    return f"sqlite:///{path.as_posix()}"


def resolve_database_url(
    database_url: Optional[str] = None,
    *,
    allow_sqlite_fallback: bool = True,
    env_var: str = DATABASE_URL_ENV,
) -> str:
    raw = database_url or os.environ.get(env_var)
    if raw:
        normalized = normalize_database_url(raw)
        if "://" not in normalized:
            return _path_to_sqlite_url(normalized)
        return normalized

    if allow_sqlite_fallback:
        return DEFAULT_SQLITE_URL

    raise RuntimeError(
        f"{env_var} is required for production. Set it to a PostgreSQL URL such as "
        "postgresql+psycopg2://user:password@host:5432/database."
    )


def build_engine_options(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {
            "connect_args": {"check_same_thread": False},
            "poolclass": NullPool,
        }

    pool_size = int(os.environ.get("AGENTEVAL_DB_POOL_SIZE", "5"))
    max_overflow = int(os.environ.get("AGENTEVAL_DB_MAX_OVERFLOW", "10"))
    return {
        "pool_pre_ping": True,
        "pool_size": pool_size,
        "max_overflow": max_overflow,
    }


def database_backend_name(database_url: str) -> str:
    if database_url.startswith("sqlite"):
        return "sqlite"
    if database_url.startswith("postgres"):
        return "postgresql"
    return "unknown"
