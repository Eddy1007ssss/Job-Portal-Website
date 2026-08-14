import sqlite3
import unittest
from datetime import datetime, timedelta, timezone

from src.password_reset_logic import (
    create_password_reset_token,
    get_password_reset_token_status,
    reset_account_password,
    validate_email_address,
    validate_new_password,
)

NOW = datetime(2026, 8, 14, 6, 0, tzinfo=timezone.utc)


def generate_test_hash(password: str) -> str:
    return f"test-hash:{password}"


def check_test_hash(stored_hash: str, password: str) -> bool:
    return stored_hash == generate_test_hash(password)


class PasswordResetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript("""
            CREATE TABLE seekers (
                seeker_id INTEGER PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            );

            CREATE TABLE employers (
                employer_id INTEGER PRIMARY KEY,
                company_email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            );

            CREATE TABLE password_reset_tokens (
                reset_id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_type TEXT NOT NULL,
                account_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                CHECK(account_type IN ('seeker', 'employer'))
            );

            INSERT INTO seekers VALUES (
                7,
                'eddy@example.com',
                'test-hash:OldPass1'
            );

            INSERT INTO employers VALUES (
                3,
                'jobs@zenith.example',
                'test-hash:Employer1'
            );
            """)

    def tearDown(self) -> None:
        self.connection.close()

    def create_seeker_token(self) -> str:
        token = create_password_reset_token(
            self.connection,
            "eddy@example.com",
            "seeker",
            now=NOW,
        )
        self.assertIsNotNone(token)
        return token or ""

    def test_validates_email_format(self) -> None:
        self.assertIsNone(validate_email_address("eddy@example.com"))
        self.assertIsNotNone(validate_email_address("not-an-email"))

    def test_password_rules_require_length_upper_lower_and_number(self) -> None:
        invalid_passwords = (
            "Short1",
            "lowercase1",
            "UPPERCASE1",
            "NoNumbers",
        )

        for password in invalid_passwords:
            with self.subTest(password=password):
                self.assertIsNotNone(validate_new_password(password))

        self.assertIsNone(validate_new_password("StrongPass1"))

    def test_creates_hashed_one_time_token_for_registered_seeker(self) -> None:
        token = self.create_seeker_token()
        saved = self.connection.execute(
            "SELECT * FROM password_reset_tokens"
        ).fetchone()

        self.assertNotEqual(saved["token_hash"], token)
        self.assertEqual(saved["account_type"], "seeker")
        self.assertEqual(saved["account_id"], 7)
        self.assertEqual(
            get_password_reset_token_status(
                self.connection,
                token,
                now=NOW,
            ).outcome,
            "valid",
        )

    def test_creates_token_for_registered_employer(self) -> None:
        token = create_password_reset_token(
            self.connection,
            "JOBS@ZENITH.EXAMPLE",
            "employer",
            now=NOW,
        )
        status = get_password_reset_token_status(
            self.connection,
            token or "",
            now=NOW,
        )

        self.assertIsNotNone(token)
        self.assertEqual(status.account_type, "employer")
        self.assertEqual(status.account_id, 3)

    def test_unknown_email_does_not_create_token(self) -> None:
        token = create_password_reset_token(
            self.connection,
            "unknown@example.com",
            "seeker",
            now=NOW,
        )

        self.assertIsNone(token)
        self.assertEqual(
            self.connection.execute(
                "SELECT COUNT(*) FROM password_reset_tokens"
            ).fetchone()[0],
            0,
        )

    def test_requesting_new_token_invalidates_previous_token(self) -> None:
        first_token = self.create_seeker_token()
        second_token = create_password_reset_token(
            self.connection,
            "eddy@example.com",
            "seeker",
            now=NOW + timedelta(minutes=1),
        )

        self.assertEqual(
            get_password_reset_token_status(
                self.connection,
                first_token,
                now=NOW + timedelta(minutes=1),
            ).outcome,
            "invalid",
        )
        self.assertEqual(
            get_password_reset_token_status(
                self.connection,
                second_token or "",
                now=NOW + timedelta(minutes=1),
            ).outcome,
            "valid",
        )

    def test_token_expires_after_thirty_minutes(self) -> None:
        token = self.create_seeker_token()
        status = get_password_reset_token_status(
            self.connection,
            token,
            now=NOW + timedelta(minutes=31),
        )

        self.assertEqual(status.outcome, "expired")

    def test_rejects_password_confirmation_mismatch(self) -> None:
        token = self.create_seeker_token()
        result = self.reset_password(token, "NewPassword1", "Different1")

        self.assertEqual(result.outcome, "mismatch")
        self.assertEqual(self.seeker_password_hash(), "test-hash:OldPass1")

    def test_rejects_weak_new_password(self) -> None:
        token = self.create_seeker_token()
        result = self.reset_password(token, "weakpass", "weakpass")

        self.assertEqual(result.outcome, "weak")
        self.assertEqual(self.seeker_password_hash(), "test-hash:OldPass1")

    def test_rejects_current_password_as_new_password(self) -> None:
        token = self.create_seeker_token()
        result = self.reset_password(token, "OldPass1", "OldPass1")

        self.assertEqual(result.outcome, "same_password")

    def test_updates_seeker_password_and_consumes_token(self) -> None:
        token = self.create_seeker_token()
        result = self.reset_password(token, "NewPassword1", "NewPassword1")

        self.assertTrue(result.succeeded)
        self.assertEqual(
            self.seeker_password_hash(),
            "test-hash:NewPassword1",
        )
        self.assertEqual(
            get_password_reset_token_status(
                self.connection,
                token,
                now=NOW,
            ).outcome,
            "invalid",
        )

    def test_used_token_cannot_reset_password_twice(self) -> None:
        token = self.create_seeker_token()
        first_result = self.reset_password(
            token,
            "NewPassword1",
            "NewPassword1",
        )
        second_result = self.reset_password(
            token,
            "AnotherPass2",
            "AnotherPass2",
        )

        self.assertTrue(first_result.succeeded)
        self.assertEqual(second_result.outcome, "invalid")

    def test_updates_employer_password(self) -> None:
        token = create_password_reset_token(
            self.connection,
            "jobs@zenith.example",
            "employer",
            now=NOW,
        )
        result = self.reset_password(
            token or "",
            "NewEmployer2",
            "NewEmployer2",
        )
        saved = self.connection.execute(
            "SELECT password_hash FROM employers WHERE employer_id = 3"
        ).fetchone()

        self.assertTrue(result.succeeded)
        self.assertEqual(saved["password_hash"], "test-hash:NewEmployer2")

    def reset_password(
        self,
        token: str,
        new_password: str,
        confirm_password: str,
    ):
        return reset_account_password(
            self.connection,
            token,
            new_password,
            confirm_password,
            now=NOW,
            check_hash=check_test_hash,
            generate_hash=generate_test_hash,
        )

    def seeker_password_hash(self) -> str:
        row = self.connection.execute(
            "SELECT password_hash FROM seekers WHERE seeker_id = 7"
        ).fetchone()
        return str(row["password_hash"])


if __name__ == "__main__":
    unittest.main()
