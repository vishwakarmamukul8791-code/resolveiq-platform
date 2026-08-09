import os
from contextlib import contextmanager
from contextvars import ContextVar
from threading import Lock

from backend.services.persistence_config import is_supabase_backend


class DatabaseSchemaError(RuntimeError):
    """Raised when the required Supabase migration has not been applied."""


_pool = None
_pool_guard = Lock()
_active_connection = ContextVar(
    "resolveiq_active_database_connection",
    default=None,
)


def _database_url() -> str:
    database_url = os.getenv("SUPABASE_DATABASE_URL", "").strip()

    if not database_url:
        raise RuntimeError("SUPABASE_DATABASE_URL is not configured.")

    return database_url


def _create_pool():
    try:
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool
    except ImportError as exc:
        raise RuntimeError(
            "Supabase persistence requires psycopg and psycopg_pool."
        ) from exc

    pool = ConnectionPool(
        conninfo=_database_url(),
        min_size=0,
        max_size=3,
        open=False,
        timeout=10,
        max_idle=60,
        check=ConnectionPool.check_connection,
        kwargs={
            "autocommit": True,
            "row_factory": dict_row,
            # Supabase transaction pooling does not support prepared
            # statements. Disabling them is also safe with session mode.
            "prepare_threshold": None,
        },
    )
    pool.open()
    return pool


def get_database_pool():
    global _pool

    if not is_supabase_backend():
        raise RuntimeError(
            "Database access requested while local persistence is enabled."
        )

    if _pool is None:
        with _pool_guard:
            if _pool is None:
                _pool = _create_pool()

    return _pool


@contextmanager
def database_connection():
    active = _active_connection.get()

    if active is not None:
        yield active
        return

    with get_database_pool().connection(timeout=10) as connection:
        yield connection


@contextmanager
def database_transaction(lock_key: str | None = None):
    """
    Run related writes in one PostgreSQL transaction.

    The optional advisory lock serializes a logical collection across all
    API instances. Nested service calls reuse the same connection so a
    read-modify-write sequence stays inside the same transaction.

    Note: if code nests two of these calls with *different* lock_keys
    (rather than calling multi_lock_transaction below), only the
    outermost lock is actually taken — the inner call sees
    _active_connection already set and returns before reaching its own
    pg_advisory_xact_lock call. That's intentional for the common case
    (nested calls inside the *same* logical collection, which don't need
    a second lock on themselves) but means naively nesting two unrelated
    single-lock_key calls together does not give you both locks.
    """

    active = _active_connection.get()

    if active is not None:
        yield active
        return

    with get_database_pool().connection(timeout=10) as connection:
        with connection.transaction():
            if lock_key:
                connection.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s))",
                    (lock_key,),
                )

            token = _active_connection.set(connection)

            try:
                yield connection
            finally:
                _active_connection.reset(token)


@contextmanager
def multi_lock_transaction(lock_keys: list):
    """
    Like database_transaction, but acquires an advisory lock for every
    key in lock_keys up front, in a fixed (sorted) order to avoid
    deadlocking against another caller locking the same set in a
    different order. Everything inside the `with` block — including
    calls into functions that individually call database_transaction()
    or collection_transaction() for any of these same namespaces — runs
    in one transaction and reuses this connection.

    Use this when two otherwise-independent writes (each normally
    protected by its own single-namespace lock) need to succeed or fail
    together as one atomic unit — e.g. ask.py recording a question in
    sessions.json and appending the matching entry to history.json.
    Without this, those two writes were separate transactions: if the
    first succeeded and the second then failed (a dropped connection,
    a pool timeout), the session's question count would be
    incremented with no matching history entry, and a client retry
    could double-count the question with no way to tell it apart from
    a genuinely new one (P2-08).
    """

    active = _active_connection.get()

    if active is not None:
        yield active
        return

    with get_database_pool().connection(timeout=10) as connection:
        with connection.transaction():
            for lock_key in sorted(set(lock_keys)):
                connection.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s))",
                    (lock_key,),
                )

            token = _active_connection.set(connection)

            try:
                yield connection
            finally:
                _active_connection.reset(token)


def _record_key(record: dict, position: int) -> str:
    for field in (
        "id",
        "session_id",
        "username",
        "document_name",
    ):
        value = record.get(field)

        if value is not None:
            return str(value)

    return str(position)


def load_collection(namespace: str) -> list:
    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT payload
            FROM public.resolveiq_records
            WHERE namespace = %s
            ORDER BY position ASC
            """,
            (namespace,),
        ).fetchall()

    return [row["payload"] for row in rows]


def save_collection(namespace: str, records: list) -> None:
    try:
        from psycopg.types.json import Jsonb
    except ImportError as exc:
        raise RuntimeError(
            "Supabase persistence requires psycopg."
        ) from exc

    with database_transaction(namespace) as connection:
        connection.execute(
            "DELETE FROM public.resolveiq_records WHERE namespace = %s",
            (namespace,),
        )

        if not records:
            return

        values = [
            (
                namespace,
                _record_key(record, position),
                position,
                Jsonb(record),
            )
            for position, record in enumerate(records)
        ]

        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO public.resolveiq_records (
                    namespace,
                    record_key,
                    position,
                    payload
                ) VALUES (%s, %s, %s, %s)
                """,
                values,
            )


@contextmanager
def collection_transaction(namespace: str):
    with database_transaction(namespace):
        yield


def check_database_schema() -> None:
    if not is_supabase_backend():
        return

    bucket = os.getenv(
        "SUPABASE_STORAGE_BUCKET",
        "resolveiq-documents",
    ).strip()

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT
                to_regclass('public.resolveiq_records') AS records_table,
                to_regclass('public.resolveiq_chunks') AS chunks_table,
                EXISTS (
                    SELECT 1
                    FROM pg_extension
                    WHERE extname = 'vector'
                ) AS vector_enabled,
                EXISTS (
                    SELECT 1
                    FROM pg_attribute AS attribute
                    JOIN pg_class AS relation
                      ON relation.oid = attribute.attrelid
                    JOIN pg_namespace AS schema
                      ON schema.oid = relation.relnamespace
                    WHERE schema.nspname = 'public'
                      AND relation.relname = 'resolveiq_chunks'
                      AND attribute.attname = 'embedding'
                      AND format_type(
                          attribute.atttypid,
                          attribute.atttypmod
                      ) IN ('vector(384)', 'extensions.vector(384)')
                ) AS vector_dimension_valid,
                EXISTS (
                    SELECT 1
                    FROM storage.buckets
                    WHERE id = %s
                      AND public = false
                ) AS private_bucket_exists
            """,
            (bucket,),
        ).fetchone()

    if not (
        row
        and row["records_table"]
        and row["chunks_table"]
        and row["vector_enabled"]
        and row["vector_dimension_valid"]
        and row["private_bucket_exists"]
    ):
        raise DatabaseSchemaError(
            "Supabase schema, vector(384) column, or private Storage "
            "bucket is missing. Apply the SQL migration in "
            "supabase/migrations before starting the API."
        )


def database_is_reachable() -> bool:
    try:
        with database_connection() as connection:
            row = connection.execute("SELECT 1 AS ok").fetchone()
        return bool(row and row["ok"] == 1)
    except Exception:
        return False


def close_database_pool() -> None:
    global _pool

    with _pool_guard:
        if _pool is not None:
            _pool.close()
            _pool = None
