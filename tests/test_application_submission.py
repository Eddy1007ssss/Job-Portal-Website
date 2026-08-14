import sqlite3
import unittest

from src.application_submission import (
    can_submit_application,
    submit_application,
)


class ApplicationSubmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript("""
            CREATE TABLE applications (
                application_id INTEGER PRIMARY KEY AUTOINCREMENT,
                seeker_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                cover_letter TEXT,
                resume_filename TEXT,
                status TEXT NOT NULL,
                applied_at TEXT,
                updated_at TEXT,
                UNIQUE(seeker_id, job_id)
            );

            INSERT INTO applications VALUES (
                1, 7, 10, 'Old cover letter', 'old.pdf', 'Withdrawn',
                '2025-01-01 00:00:00', '2025-01-02 00:00:00'
            );
            INSERT INTO applications VALUES (
                2, 7, 20, 'Rejected cover letter', 'resume.pdf', 'Rejected',
                '2025-02-01 00:00:00', '2025-02-02 00:00:00'
            );
            INSERT INTO applications VALUES (
                3, 7, 30, 'Pending cover letter', 'resume.pdf', 'Pending',
                '2025-03-01 00:00:00', '2025-03-02 00:00:00'
            );
            """)

    def tearDown(self) -> None:
        self.connection.close()

    def get_application(self, application_id: int) -> sqlite3.Row:
        return self.connection.execute(
            "SELECT * FROM applications WHERE application_id = ?",
            (application_id,),
        ).fetchone()

    def test_withdrawn_application_can_be_submitted_again(self) -> None:
        result = submit_application(
            self.connection,
            seeker_id=7,
            job_id=10,
            cover_letter="A new and improved cover letter.",
            resume_filename="latest.pdf",
        )

        application = self.get_application(1)
        self.assertEqual(result.outcome, "reapplied")
        self.assertTrue(result.succeeded)
        self.assertEqual(result.application_id, 1)
        self.assertEqual(application["status"], "Pending")
        self.assertEqual(
            application["cover_letter"],
            "A new and improved cover letter.",
        )
        self.assertEqual(application["resume_filename"], "latest.pdf")
        self.assertNotEqual(application["applied_at"], "2025-01-01 00:00:00")
        application_count = self.connection.execute(
            "SELECT COUNT(*) AS total FROM applications WHERE job_id = 10"
        ).fetchone()["total"]
        self.assertEqual(application_count, 1)

    def test_rejected_application_cannot_be_submitted_again(self) -> None:
        result = submit_application(
            self.connection,
            seeker_id=7,
            job_id=20,
            cover_letter="Another cover letter.",
            resume_filename="new.pdf",
        )

        application = self.get_application(2)
        self.assertEqual(result.outcome, "already_exists")
        self.assertEqual(result.previous_status, "Rejected")
        self.assertEqual(application["status"], "Rejected")
        self.assertEqual(application["cover_letter"], "Rejected cover letter")

    def test_pending_application_cannot_be_duplicated(self) -> None:
        result = submit_application(
            self.connection,
            seeker_id=7,
            job_id=30,
            cover_letter="Another cover letter.",
            resume_filename=None,
        )

        self.assertEqual(result.outcome, "already_exists")
        self.assertEqual(result.previous_status, "Pending")

    def test_new_job_creates_a_new_application(self) -> None:
        result = submit_application(
            self.connection,
            seeker_id=7,
            job_id=40,
            cover_letter="My first application for this new job.",
            resume_filename="resume.pdf",
        )

        self.assertEqual(result.outcome, "submitted")
        self.assertTrue(result.succeeded)
        application = self.connection.execute(
            "SELECT * FROM applications WHERE seeker_id = 7 AND job_id = 40"
        ).fetchone()
        self.assertEqual(application["status"], "Pending")

    def test_only_withdrawn_status_is_eligible_for_reapplication(self) -> None:
        self.assertTrue(can_submit_application(None))
        self.assertTrue(can_submit_application("Withdrawn"))
        self.assertFalse(can_submit_application("Rejected"))
        self.assertFalse(can_submit_application("Pending"))
        self.assertFalse(can_submit_application("Accepted"))


if __name__ == "__main__":
    unittest.main()
