import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from backend.routes import demo


class PublicDemoTests(unittest.TestCase):

    def test_public_demo_context_is_fail_closed_when_guest_mode_off(self):
        with patch.dict(
            os.environ,
            {"GUEST_MODE_ENABLED": "false", "GUEST_ALLOWED_DOCUMENTS": "Public.txt"},
            clear=False,
        ):
            with self.assertRaises(HTTPException) as ctx:
                demo.get_public_demo_context()

        self.assertEqual(ctx.exception.status_code, 404)

    def test_public_demo_context_requires_explicit_allowlist(self):
        with patch.dict(
            os.environ,
            {"GUEST_MODE_ENABLED": "true", "GUEST_ALLOWED_DOCUMENTS": ""},
            clear=False,
        ):
            with self.assertRaises(HTTPException) as ctx:
                demo.get_public_demo_context()

        self.assertEqual(ctx.exception.status_code, 503)

    def test_public_demo_context_returns_only_allowlisted_document_metadata(self):
        fake_health = {
            "status": "Healthy",
            "database": "Connected",
            "vector_store": "Loaded",
            "jwt_secret": "Configured",
            "gemini_api": "Configured",
        }
        fake_stats = {
            "total_documents": 999,
            "total_chunks": 99999,
            "embedding_model": "demo-embedding-model",
            "embedding_provider": "demo-provider",
            "embedding_dimension": 384,
            "vector_database": "pgvector",
            "top_k": 5,
            "chunk_size": 500,
            "chunk_overlap": 100,
            "reranker_enabled": False,
            "query_rewrite_enabled": False,
        }

        with (
            patch.dict(
                os.environ,
                {
                    "GUEST_MODE_ENABLED": "true",
                    "GUEST_ALLOWED_DOCUMENTS": (
                        "Public_Runbook.pdf, Demo_Incidents.csv,Public_Runbook.pdf"
                    ),
                },
                clear=False,
            ),
            patch.object(
                demo,
                "load_registry",
                return_value=[
                    {"document_name": "Public_Runbook.pdf"},
                    {"document_name": "Demo_Incidents.csv"},
                    {"document_name": "Private_Internal.txt"},
                ],
            ),
            patch.object(demo, "get_health_status", return_value=fake_health),
            patch.object(demo, "get_stats", return_value=fake_stats),
        ):
            payload = demo.get_public_demo_context()

        self.assertEqual(payload["mode"], "public-demo-read-only")
        self.assertEqual(
            [doc["name"] for doc in payload["documents"]],
            ["Demo_Incidents.csv", "Public_Runbook.pdf"],
        )
        self.assertEqual(payload["document_count"], 2)
        self.assertNotIn("jwt_secret", payload["health"])
        self.assertNotIn("gemini_api", payload["health"])
        self.assertNotIn("total_documents", payload["retrieval_config"])
        self.assertNotIn("total_chunks", payload["retrieval_config"])

    def test_public_demo_count_tracks_current_registered_allowlisted_documents(self):
        with (
            patch.dict(
                os.environ,
                {
                    "GUEST_MODE_ENABLED": "true",
                    "GUEST_ALLOWED_DOCUMENTS": "A.txt,B.txt,C.txt",
                },
                clear=False,
            ),
            patch.object(
                demo,
                "load_registry",
                return_value=[
                    {"document_name": "A.txt"},
                    {"document_name": "C.txt"},
                    {"document_name": "Private.txt"},
                ],
            ),
            patch.object(demo, "get_health_status", return_value={"status": "Healthy"}),
            patch.object(demo, "get_stats", return_value={}),
        ):
            payload = demo.get_public_demo_context()

        self.assertEqual(payload["document_count"], 2)
        self.assertEqual(
            [doc["name"] for doc in payload["documents"]],
            ["A.txt", "C.txt"],
        )

    def test_public_demo_security_contract_never_grants_admin_authority(self):
        with (
            patch.dict(
                os.environ,
                {"GUEST_MODE_ENABLED": "true", "GUEST_ALLOWED_DOCUMENTS": "Public.txt"},
                clear=False,
            ),
            patch.object(
                demo,
                "load_registry",
                return_value=[{"document_name": "Public.txt"}],
            ),
            patch.object(demo, "get_health_status", return_value={"status": "Healthy"}),
            patch.object(demo, "get_stats", return_value={}),
        ):
            payload = demo.get_public_demo_context()

        security = payload["security"]
        self.assertTrue(security["real_admin_auth_required"])
        self.assertFalse(security["destructive_actions_enabled"])
        self.assertFalse(security["engineer_identity_exposed"])
        self.assertFalse(security["private_documents_exposed"])
        self.assertFalse(security["credentials_exposed"])


if __name__ == "__main__":
    unittest.main()
