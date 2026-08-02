import unittest
from datetime import datetime
from unittest.mock import patch

from fastapi import HTTPException

from backend.services.auth_service import (
    admin_reset_password,
    get_current_user,
    require_password_reset_complete,
)
from backend.services.session_service import (
    close_session,
    create_session,
    record_question,
)


class AuthEnforcementTests(unittest.TestCase):

    def test_deactivated_user_token_is_rejected_immediately(self):
        with (
            patch(
                "backend.services.auth_service.decode_access_token",
                return_value={"username": "dev", "role": "engineer"},
            ),
            patch(
                "backend.services.auth_service.get_user",
                return_value={
                    "username": "dev",
                    "role": "engineer",
                    "is_active": False,
                },
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                get_current_user(token="valid-token")

        self.assertEqual(raised.exception.status_code, 401)

    def test_current_database_role_overrides_stale_token_role(self):
        with (
            patch(
                "backend.services.auth_service.decode_access_token",
                return_value={"username": "mukul", "role": "engineer"},
            ),
            patch(
                "backend.services.auth_service.get_user",
                return_value={
                    "username": "mukul",
                    "role": "admin",
                    "is_active": True,
                    "must_reset_password": False,
                },
            ),
        ):
            user = get_current_user(token="valid-token")

        self.assertEqual(user["role"], "admin")

    def test_temporary_password_blocks_application_access(self):
        with self.assertRaises(HTTPException) as raised:
            require_password_reset_complete({
                "username": "dev",
                "role": "engineer",
                "must_reset_password": True,
            })

        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(
            raised.exception.detail,
            "Password reset required.",
        )

    def test_admin_reset_endpoint_cannot_reset_an_admin(self):
        with (
            patch(
                "backend.services.auth_service._load_users",
                return_value=[{
                    "username": "admin",
                    "role": "admin",
                }],
            ),
            patch(
                "backend.services.auth_service._save_users",
            ) as save_mock,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "Only engineer passwords",
            ):
                admin_reset_password("admin")

        save_mock.assert_not_called()


class SessionEnforcementTests(unittest.TestCase):

    def test_new_session_timestamp_is_timezone_aware(self):
        saved = []

        with (
            patch(
                "backend.services.session_service._load_sessions",
                return_value=[],
            ),
            patch(
                "backend.services.session_service._save_sessions",
                side_effect=lambda sessions: saved.extend(sessions),
            ),
        ):
            create_session("mukul")

        parsed = datetime.fromisoformat(saved[0]["login_time"])
        self.assertIsNotNone(parsed.tzinfo)

    def test_user_cannot_close_another_users_session(self):
        sessions = [{
            "session_id": "session-1",
            "username": "alice",
            "login_time": "2026-08-02T12:00:00+00:00",
            "logout_time": None,
        }]

        with (
            patch(
                "backend.services.session_service._load_sessions",
                return_value=sessions,
            ),
            patch("backend.services.session_service._save_sessions"),
        ):
            found = close_session("session-1", "bob")

        self.assertFalse(found)
        self.assertIsNone(sessions[0]["logout_time"])

    def test_question_is_counted_only_for_owners_open_session(self):
        sessions = [{
            "session_id": "session-1",
            "username": "alice",
            "logout_time": None,
            "questions_asked": 0,
            "high_confidence": 0,
            "medium_confidence": 0,
            "low_confidence": 0,
        }]

        with (
            patch(
                "backend.services.session_service._load_sessions",
                return_value=sessions,
            ),
            patch("backend.services.session_service._save_sessions"),
        ):
            found = record_question(
                "session-1",
                "High",
                "bob",
            )

        self.assertFalse(found)
        self.assertEqual(sessions[0]["questions_asked"], 0)


if __name__ == "__main__":
    unittest.main()
