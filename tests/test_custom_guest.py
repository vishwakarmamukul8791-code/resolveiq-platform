import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from backend.routes.custom_guest import (
    _chunk_text,
    _normalize_text,
    _retrieve_chunks,
    _safe_filename,
)


class CustomGuestSandboxTests(unittest.TestCase):
    def test_txt_filename_is_sanitized_to_basename(self):
        self.assertEqual(_safe_filename("../../incident.txt"), "incident.txt")

    def test_non_txt_filename_is_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            _safe_filename("incident.pdf")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_short_document_is_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            _normalize_text("too short")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_chunking_is_bounded_and_overlapping(self):
        text = "A" * 1600
        chunks = _chunk_text(text)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 700 for chunk in chunks))

    def test_bm25_returns_relevant_chunk(self):
        chunks = [
            "Oracle ORA-12154 indicates the connect identifier could not be resolved.",
            "Kubernetes pods may restart because of CrashLoopBackOff.",
        ]
        results = _retrieve_chunks("How do I fix ORA-12154 Oracle connect identifier?", chunks)
        self.assertTrue(results)
        self.assertEqual(results[0]["chunk_index"], 1)

    def test_bm25_handles_a_single_chunk_document(self):
        chunks = [
            "Redis timeouts occur when the client connection pool is exhausted under load."
        ]
        results = _retrieve_chunks("Why are Redis requests timing out due to connection pool exhaustion?", chunks)
        self.assertTrue(results)
        self.assertEqual(results[0]["chunk_index"], 1)

    def test_bm25_returns_empty_for_unrelated_query(self):
        chunks = [
            "Oracle ORA-12154 indicates the connect identifier could not be resolved.",
            "Kubernetes pods may restart because of CrashLoopBackOff.",
        ]
        results = _retrieve_chunks("how to bake chocolate cake", chunks)
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
