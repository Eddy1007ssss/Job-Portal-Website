import sqlite3
import unittest

from src.application_withdrawal import (
    can_employer_update_application,
    withdraw_application,
)


class ApplicationWithdrawalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript("""
            CREATE TABLE applications (
                application_id INTEGER PRIMARY KEY,
                seeker_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                updated_at TEXT
            );

            INSERT INTO applications VALUES (1, 7, 'Pending', NULL);
            INSERT INTO applications VALUES (2, 7, 'Shortlisted', NULL);
            INSERT INTO applications VALUES (3, 8, 'Pending', NULL);
            INSERT INTO applications VALUES (4, 7, 'Accepted', NULL);
            """)

    def tearDown(self) -> None:
        self.connection.close()

    def application_status(self, application_id: int) -> str:
        row = self.connection.execute(
            "SELECT status FROM applications WHERE application_id = ?",
            (application_id,),
        ).fetchone()
        return str(row["status"])

    def test_withdraws_owned_pending_application(self) -> None:
        result = withdraw_application(
            self.connection,
            application_id=1,
            seeker_id=7,
        )

        self.assertTrue(result.succeeded)
        self.assertEqual(self.application_status(1), "Withdrawn")
        updated_at = self.connection.execute(
            "SELECT updated_at FROM applications WHERE application_id = 1"
        ).fetchone()["updated_at"]
        self.assertIsNotNone(updated_at)

    def test_cannot_withdraw_application_after_review(self) -> None:
        result = withdraw_application(
            self.connection,
            application_id=2,
            seeker_id=7,
        )

        self.assertEqual(result.outcome, "not_pending")
        self.assertEqual(result.previous_status, "Shortlisted")
        self.assertEqual(self.application_status(2), "Shortlisted")

    def test_cannot_withdraw_accepted_application(self) -> None:
        result = withdraw_application(
            self.connection,
            application_id=4,
            seeker_id=7,
        )

        self.assertEqual(result.outcome, "not_pending")
        self.assertEqual(self.application_status(4), "Accepted")

    def test_cannot_withdraw_another_seekers_application(self) -> None:
        result = withdraw_application(
            self.connection,
            application_id=3,
            seeker_id=7,
        )

        self.assertEqual(result.outcome, "not_found")
        self.assertEqual(self.application_status(3), "Pending")

    def test_cannot_withdraw_same_application_twice(self) -> None:
        first_result = withdraw_application(self.connection, 1, 7)
        second_result = withdraw_application(self.connection, 1, 7)

        self.assertTrue(first_result.succeeded)
        self.assertEqual(second_result.outcome, "not_pending")
        self.assertEqual(second_result.previous_status, "Withdrawn")

    def test_employer_cannot_change_withdrawn_application(self) -> None:
        self.assertFalse(can_employer_update_application("Withdrawn"))
        self.assertTrue(can_employer_update_application("Pending"))
        self.assertTrue(can_employer_update_application("Shortlisted"))


if __name__ == "__main__":
    unittest.main()
