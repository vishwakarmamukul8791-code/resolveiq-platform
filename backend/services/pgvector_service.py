from collections.abc import Sequence

import numpy as np

from backend.services.database_service import (
    database_connection,
    database_transaction,
)
from backend.services.embedding_service import EMBEDDING_DIMENSION


DOCUMENT_STORAGE_LOCK = "resolveiq-document-storage"


def _vector_literal(values: Sequence[float]) -> str:
    vector = np.asarray(values, dtype="float32").reshape(-1)

    if vector.shape[0] != EMBEDDING_DIMENSION:
        raise ValueError(
            "Embedding dimension does not match the configured pgvector "
            f"column: expected={EMBEDDING_DIMENSION}, "
            f"actual={vector.shape[0]}"
        )

    if not np.all(np.isfinite(vector)):
        raise ValueError("Embedding contains a non-finite value.")

    return "[" + ",".join(f"{float(value):.9g}" for value in vector) + "]"


def load_chunk_metadata() -> list:
    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                chunk_id::text AS chunk_id,
                document_name,
                chunk,
                page_number,
                source_location
            FROM public.resolveiq_chunks
            ORDER BY created_at ASC, chunk_id ASC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def count_chunks() -> int:
    with database_connection() as connection:
        row = connection.execute(
            "SELECT count(*)::integer AS count "
            "FROM public.resolveiq_chunks"
        ).fetchone()

    return int(row["count"])


def _insert_chunks(connection, records: list, embeddings) -> None:
    prepared = np.asarray(embeddings, dtype="float32")

    if prepared.ndim != 2 or prepared.shape[0] != len(records):
        raise ValueError(
            "Chunk and embedding counts must match before persistence."
        )

    values = [
        (
            record["chunk_id"],
            record["document_name"],
            record["chunk"],
            record.get("page_number"),
            record.get("source_location"),
            _vector_literal(embedding),
        )
        for record, embedding in zip(records, prepared, strict=True)
    ]

    if not values:
        return

    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO public.resolveiq_chunks (
                chunk_id,
                document_name,
                chunk,
                page_number,
                source_location,
                embedding
            ) VALUES (%s::uuid, %s, %s, %s, %s, %s::extensions.vector)
            """,
            values,
        )


def commit_processed_document(
    document_name: str,
    records: list,
    embeddings,
    file_hash: str,
) -> int:
    """
    Atomically replace one document's vectors and registry entry.

    The registry is read, updated, and saved *inside* this function's
    advisory-locked transaction rather than being handed in as an
    already-computed proposed_registry by the caller. Previously the
    caller (process.py) read the registry before acquiring the lock, so
    two concurrent uploads could both read the same "before" registry,
    each add their own document to it, and then whichever commit wins
    the lock second would overwrite the first commit's registry entry
    with a copy that never saw it (P2-03). Reading the registry here,
    under the lock, means every commit sees the latest state left by
    whichever transaction most recently held the lock.
    """

    from backend.services.bm25_service import invalidate_cache
    from backend.services.document_registry import load_registry, save_registry

    with database_transaction(DOCUMENT_STORAGE_LOCK) as connection:
        current_registry = load_registry()
        updated_registry = [
            entry for entry in current_registry
            if entry["document_name"] != document_name
        ]
        updated_registry.append({
            "document_name": document_name,
            "hash": file_hash,
        })

        connection.execute(
            "DELETE FROM public.resolveiq_chunks WHERE document_name = %s",
            (document_name,),
        )
        _insert_chunks(connection, records, embeddings)
        save_registry(updated_registry)

    invalidate_cache()

    return count_chunks()


def delete_document_data(document_name: str) -> int:
    """
    Atomically remove a document's chunks and registry entry.

    As with commit_processed_document, the registry is now read and
    rewritten inside the locked transaction rather than being passed in
    pre-computed by the caller, closing the same class of TOCTOU race
    (P2-03) on the delete path.
    """

    from backend.services.bm25_service import invalidate_cache
    from backend.services.document_registry import load_registry, save_registry

    with database_transaction(DOCUMENT_STORAGE_LOCK) as connection:
        current_registry = load_registry()
        updated_registry = [
            entry for entry in current_registry
            if entry["document_name"] != document_name
        ]

        result = connection.execute(
            "DELETE FROM public.resolveiq_chunks "
            "WHERE document_name = %s",
            (document_name,),
        )
        removed = result.rowcount
        save_registry(updated_registry)

    invalidate_cache()

    return int(removed)


def search_pgvector(
    query_embedding,
    top_k: int,
    document_name: str | None = None,
    document_names: Sequence[str] | None = None,
) -> tuple[list, list]:
    """
    document_name scopes to exactly one document. document_names scopes
    to any of a set of documents (e.g. a guest account's allow-list) —
    the filter is pushed into the SQL WHERE clause and applied *before*
    ORDER BY / LIMIT, so a restricted caller's top_k candidates are
    chosen only from documents they're allowed to see, rather than
    picking the global top_k first and filtering afterwards (which could
    discard every allowed-document match if it didn't happen to rank in
    the unfiltered top_k — see P3-01).
    """
    query_vector = np.asarray(query_embedding, dtype="float32")

    if query_vector.ndim == 2 and query_vector.shape[0] == 1:
        query_vector = query_vector[0]

    literal = _vector_literal(query_vector)

    sql = """
        SELECT
            chunk_id::text AS chunk_id,
            document_name,
            chunk,
            page_number,
            source_location,
            embedding <=> %s::extensions.vector AS distance
        FROM public.resolveiq_chunks
    """
    parameters = [literal]

    if document_names is not None:
        names = list(document_names)
        if not names:
            return [], []
        sql += " WHERE document_name = ANY(%s)"
        parameters.append(names)
    elif document_name is not None:
        sql += " WHERE document_name = %s"
        parameters.append(document_name)

    sql += " ORDER BY embedding <=> %s::extensions.vector ASC LIMIT %s"
    parameters.extend([literal, top_k])

    with database_connection() as connection:
        rows = connection.execute(sql, parameters).fetchall()

    results = []
    distances = []

    for row in rows:
        result = dict(row)
        result["distance"] = float(result["distance"])
        results.append(result)
        distances.append(result["distance"])

    return results, distances
