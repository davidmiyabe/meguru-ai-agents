"""Database helpers for working with the Supabase/Postgres cache."""

from __future__ import annotations

import os
from collections.abc import Mapping
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Generator, Optional, Tuple

try:  # pragma: no cover - optional dependency
    import psycopg2  # type: ignore[import-not-found]
    from psycopg2.extras import Json, RealDictCursor  # type: ignore[import-not-found]
    from psycopg2.extensions import connection as PGConnection  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - handled gracefully in tests
    psycopg2 = None  # type: ignore[assignment]
    Json = None  # type: ignore[assignment]
    RealDictCursor = None  # type: ignore[assignment]
    PGConnection = Any  # type: ignore[assignment]

CACHE_TABLE_NAME = "api_cache"


def get_connection(dsn: Optional[str] = None) -> PGConnection:
    """Return a new database connection using the configured DSN."""

    if psycopg2 is None:  # pragma: no cover - dependency missing in lightweight environments
        raise RuntimeError("psycopg2 is not installed; database operations are unavailable")
    connection_dsn = dsn or os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if not connection_dsn:
        raise RuntimeError("No database DSN configured via SUPABASE_DB_URL or DATABASE_URL")
    return psycopg2.connect(connection_dsn)


@contextmanager
def connection_ctx(dsn: Optional[str] = None) -> Generator[PGConnection, None, None]:
    """Context manager that yields a database connection and ensures it is closed."""

    connection = get_connection(dsn)
    try:
        yield connection
    finally:
        connection.close()


def ensure_cache_table(connection: PGConnection) -> None:
    """Create the cache table if it does not already exist."""

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {CACHE_TABLE_NAME} (
                key TEXT PRIMARY KEY,
                value JSONB NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    connection.commit()


def get_cache_entry(
    connection: PGConnection, key: str
) -> Optional[Tuple[Dict[str, Any], datetime]]:
    """Return a cached value and its timestamp for the supplied key."""

    cursor_kwargs: Dict[str, Any] = {}
    if RealDictCursor is not None:
        cursor_kwargs["cursor_factory"] = RealDictCursor
    with connection.cursor(**cursor_kwargs) as cursor:
        cursor.execute(
            f"SELECT value, updated_at FROM {CACHE_TABLE_NAME} WHERE key = %s",
            (key,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        value = row.get("value")
        updated_at = row.get("updated_at")
        if value is None or updated_at is None:
            return None
        if isinstance(value, Mapping):
            return dict(value), updated_at
        return value, updated_at


def set_cache_entry(
    connection: PGConnection, key: str, value: Dict[str, Any]
) -> None:
    """Insert or update a cache entry."""

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            INSERT INTO {CACHE_TABLE_NAME} (key, value, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (key) DO UPDATE
            SET value = EXCLUDED.value,
                updated_at = NOW()
            """,
            (key, Json(value) if Json is not None else value),
        )
    connection.commit()


__all__ = [
    "CACHE_TABLE_NAME",
    "connection_ctx",
    "ensure_cache_table",
    "get_cache_entry",
    "get_connection",
    "set_cache_entry",
]
