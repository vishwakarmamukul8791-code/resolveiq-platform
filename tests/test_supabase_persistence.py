import os
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import numpy as np

from backend.routes.auth import reset_password
from backend.services import json_storage
from backend.services.object_storage_service import (
    ObjectAlreadyExistsError,
    upload_unique_document,
)
from backend.services.persistence_config import (
    get_persistence_backend,
    validate_persistence_configuration,
)
from backend.services.pgvector_service import _vector_literal


class PersistenceConfigurationTests(unittest.TestCase):

    def test_local_backend_remains_the_development_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_persistence_backend(), "local")
            validate_persistence_configuration()

    def test_supabase_backend_requires_all_secrets(self):
        with patch.dict(
            os.environ,
            {"PERSISTENCE_BACKEND": "supabase"},
            clear=True,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "SUPABASE_DATABASE_URL",
            ):
                validate_persistence_configuration()

    def test_production_refuses_an_implicit_local_backend(self):
        with patch.dict(
            os.environ,
            {"ENVIRONMENT": "production"},
            clear=True,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "refusing temporary filesystem",
            ):
                get_persistence_backend()

    def test_supabase_backend_accepts_complete_configuration(self):
        with patch.dict(
            os.environ,
            {
                "PERSISTENCE_BACKEND": "supabase",
                "SUPABASE_DATABASE_URL": "postgresql://example",
                "SUPABASE_URL": "https://project.supabase.co",
                "SUPABASE_SERVICE_ROLE_KEY": "secret",
            },
            clear=True,
        ):
            validate_persistence_configuration()


class DatabaseBackedJsonStorageTests(unittest.TestCase):

    def test_load_routes_to_postgres_collection(self):
        with (
            patch.object(json_storage, "is_supabase_backend", return_value=True),
            patch.object(
                json_storage,
                "load_collection",
                return_value=[{"username": "mukul"}],
            ) as load_mock,
        ):
            result = json_storage.load_json_list(Path("users.json"))

        self.assertEqual(result, [{"username": "mukul"}])
        load_mock.assert_called_once_with("users.json")

    def test_save_routes_to_postgres_collection(self):
        records = [{"session_id": "session-1"}]

        with (
            patch.object(json_storage, "is_supabase_backend", return_value=True),
            patch.object(json_storage, "save_collection") as save_mock,
        ):
            json_storage.save_json(Path("sessions.json"), records)

        save_mock.assert_called_once_with("sessions.json", records)

    def test_synchronized_write_uses_database_transaction(self):
        entered = []

        @contextmanager
        def fake_transaction(namespace):
            entered.append(namespace)
            yield

        with (
            patch.object(json_storage, "is_supabase_backend", return_value=True),
            patch.object(
                json_storage,
                "collection_transaction",
                side_effect=fake_transaction,
            ),
        ):
            @json_storage.synchronized_storage(Path("history.json"))
            def operation():
                return "done"

            self.assertEqual(operation(), "done")

        self.assertEqual(entered, ["history.json"])


class PgvectorValidationTests(unittest.TestCase):

    def test_vector_literal_enforces_384_dimensions(self):
        literal = _vector_literal(np.zeros(384, dtype="float32"))

        self.assertTrue(literal.startswith("["))
        self.assertTrue(literal.endswith("]"))

        with self.assertRaisesRegex(ValueError, "dimension"):
            _vector_literal(np.zeros(10, dtype="float32"))

    def test_vector_literal_rejects_non_finite_values(self):
        vector = np.zeros(384, dtype="float32")
        vector[0] = np.nan

        with self.assertRaisesRegex(ValueError, "non-finite"):
            _vector_literal(vector)


class PrivateObjectStorageTests(unittest.TestCase):

    def test_duplicate_filename_gets_a_safe_suffix(self):
        with patch(
            "backend.services.object_storage_service._upload_once",
            side_effect=[ObjectAlreadyExistsError("kb.txt"), None],
        ) as upload_mock:
            stored_name = upload_unique_document(Path("temp"), "kb.txt")

        self.assertEqual(stored_name, "kb(1).txt")
        self.assertEqual(upload_mock.call_count, 2)


class PasswordResetTokenTests(unittest.TestCase):

    def test_password_reset_returns_replacement_token(self):
        updated_user = {
            "username": "mukul",
            "role": "admin",
            "token_version": 3,
        }

        with (
            patch(
                "backend.routes.auth.verify_current_password",
                return_value=True,
            ),
            patch(
                "backend.routes.auth.set_new_password",
                return_value=updated_user,
            ),
            patch(
                "backend.routes.auth.create_access_token",
                return_value="replacement-token",
            ) as token_mock,
        ):
            result = reset_password(
                current_password="old-password",
                new_password="new-password",
                current_user={"username": "mukul"},
            )

        self.assertEqual(result["access_token"], "replacement-token")
        token_mock.assert_called_once_with("mukul", "admin", 3)


if __name__ == "__main__":
    unittest.main()
