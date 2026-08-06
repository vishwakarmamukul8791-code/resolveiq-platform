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

    connection.executemany(
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
    proposed_registry: list,
) -> int:
    """Atomically replace one document's vectors and registry entry."""

    from backend.services.document_registry import save_registry

    with database_transaction(DOCUMENT_STORAGE_LOCK) as connection:
        connection.execute(
            "DELETE FROM public.resolveiq_chunks WHERE document_name = %s",
            (document_name,),
        )
        _insert_chunks(connection, records, embeddings)
        save_registry(proposed_registry)

    return count_chunks()


def delete_document_data(
    document_name: str,
    proposed_registry: list,
) -> int:
    """Atomically remove a document's chunks and registry entry."""

    from backend.services.document_registry import save_registry

    with database_transaction(DOCUMENT_STORAGE_LOCK) as connection:
        result = connection.execute(
            "DELETE FROM public.resolveiq_chunks "
            "WHERE document_name = %s",
            (document_name,),
        )
        removed = result.rowcount
        save_registry(proposed_registry)

    return int(removed)


def search_pgvector(
    query_embedding,
    top_k: int,
    document_name: str | None = None,
) -> tuple[list, list]:
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

    if document_name is not None:
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
