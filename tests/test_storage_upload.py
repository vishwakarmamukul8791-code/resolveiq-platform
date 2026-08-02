import asyncio
import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException, UploadFile

from backend.routes.upload import upload_file
from backend.services.json_storage import (
    StorageCorruptionError,
    load_json_list,
    save_json,
)


class JsonStorageTests(unittest.TestCase):

    def test_corrupt_json_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "users.json"
            path.write_text("{broken", encoding="utf-8")

            with self.assertRaises(StorageCorruptionError):
                load_json_list(path)

    def test_atomic_json_write_round_trips(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "history" / "chat_history.json"
            expected = [{"id": "entry-1"}]

            save_json(path, expected)

            self.assertEqual(load_json_list(path), expected)
            self.assertEqual(
                list(path.parent.glob(f".{path.name}.*.tmp")),
                [],
            )

    def test_non_list_json_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "metadata.json"
            path.write_text('{"unexpected": true}', encoding="utf-8")

            with self.assertRaises(StorageCorruptionError):
                load_json_list(path)


class UploadSafetyTests(unittest.TestCase):

    def test_oversized_upload_is_rejected_and_partial_file_removed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "large.txt"
            upload = UploadFile(
                filename="large.txt",
                file=BytesIO(b"a" * (1024 * 1024 + 1)),
            )

            with (
                patch.dict(
                    os.environ,
                    {"MAX_UPLOAD_SIZE_MB": "1"},
                ),
                patch(
                    "backend.routes.upload.resolve_raw_document_path",
                    return_value=destination,
                ),
            ):
                with self.assertRaises(HTTPException) as raised:
                    asyncio.run(upload_file(
                        file=upload,
                        current_user={"username": "admin"},
                    ))

            self.assertEqual(raised.exception.status_code, 413)
            self.assertFalse(destination.exists())

    def test_fake_pdf_is_rejected_and_removed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "fake.pdf"
            upload = UploadFile(
                filename="fake.pdf",
                file=BytesIO(b"This is not a PDF."),
            )

            with patch(
                "backend.routes.upload.resolve_raw_document_path",
                return_value=destination,
            ):
                with self.assertRaises(HTTPException) as raised:
                    asyncio.run(upload_file(
                        file=upload,
                        current_user={"username": "admin"},
                    ))

            self.assertEqual(raised.exception.status_code, 400)
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
