import sqlite3
import unittest
from datetime import UTC, datetime, timedelta

from src.interview_management import (
    InterviewDetails,
    cancel_interview,
    complete_interview,
    get_employer_interviews,
    get_interview_application,
    get_pending_interview_count,
    get_seeker_interviews,
    respond_to_interview,
    save_interview,
    validate_interview_details,
)

NOW = datetime(2026, 8, 14, 0, 0, tzinfo=UTC)


def interview_details(**overrides: str) -> InterviewDetails:
    values = {
        "scheduled_date": "2026-08-20",
        "scheduled_time": "10:00",
        "duration_minutes": "60",
        "interview_mode": "Online",
        "location_or_link": "https://meet.example.com/job-interview",
        "notes": "Please join five minutes early.",
    }
    values.update(overrides)
    return InterviewDetails(**values)


class InterviewManagementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript("""
            CREATE TABLE employers (
                employer_id INTEGER PRIMARY KEY,
                company_name TEXT NOT NULL
            );

            CREATE TABLE seekers (
                seeker_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL
            );

            CREATE TABLE jobs (
                job_id INTEGER PRIMARY KEY,
                employer_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                location TEXT,
                FOREIGN KEY (employer_id) REFERENCES employers(employer_id)
            );

            CREATE TABLE applications (
                application_id INTEGER PRIMARY KEY,
                seeker_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                applied_at TEXT,
                FOREIGN KEY (seeker_id) REFERENCES seekers(seeker_id),
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
            );

            CREATE TABLE interviews (
                interview_id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER NOT NULL UNIQUE,
                employer_id INTEGER NOT NULL,
                scheduled_at TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                interview_mode TEXT NOT NULL,
                location_or_link TEXT NOT NULL,
                notes TEXT,
                status TEXT NOT NULL DEFAULT 'Pending',
                seeker_response_at TEXT,
                seeker_response_reason TEXT,
                cancellation_reason TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (application_id)
                    REFERENCES applications(application_id),
                FOREIGN KEY (employer_id)
                    REFERENCES employers(employer_id)
            );

            INSERT INTO employers VALUES (1, 'Zenith Labs');
            INSERT INTO employers VALUES (2, 'Northstar Studio');

            INSERT INTO seekers VALUES (7, 'Eddy Cheah', 'eddy@example.com');
            INSERT INTO seekers VALUES (8, 'Alicia Tan', 'alicia@example.com');

            INSERT INTO jobs VALUES (
                10, 1, 'Software Developer', 'Kuala Lumpur'
            );
            INSERT INTO jobs VALUES (
                20, 2, 'UI/UX Designer', 'Penang'
            );

            INSERT INTO applications VALUES (
                100, 7, 10, 'Shortlisted', '2026-08-01 09:00:00'
            );
            INSERT INTO applications VALUES (
                101, 8, 10, 'Pending', '2026-08-02 09:00:00'
            );
            INSERT INTO applications VALUES (
                102, 7, 20, 'Shortlisted', '2026-08-03 09:00:00'
            );
            """)

    def tearDown(self) -> None:
        self.connection.close()

    def test_accepts_valid_online_interview_details(self) -> None:
        self.assertIsNone(validate_interview_details(interview_details(), now=NOW))

    def test_rejects_past_interview_date(self) -> None:
        error = validate_interview_details(
            interview_details(scheduled_date="2026-08-13"),
            now=NOW,
        )

        self.assertIn("future", error or "")

    def test_rejects_invalid_duration_and_mode(self) -> None:
        duration_error = validate_interview_details(
            interview_details(duration_minutes="10"),
            now=NOW,
        )
        mode_error = validate_interview_details(
            interview_details(interview_mode="Virtual Reality"),
            now=NOW,
        )

        self.assertIn("between 15 and 240", duration_error or "")
        self.assertIn("valid interview mode", mode_error or "")

    def test_online_interview_requires_safe_web_link(self) -> None:
        error = validate_interview_details(
            interview_details(location_or_link="javascript:alert(1)"),
            now=NOW,
        )

        self.assertIn("http or https", error or "")

    def test_employer_schedules_interview_for_shortlisted_applicant(self) -> None:
        result = self.create_interview()
        saved = self.connection.execute(
            "SELECT * FROM interviews WHERE interview_id = ?",
            (result.record_id,),
        ).fetchone()

        self.assertTrue(result.succeeded)
        self.assertEqual(result.outcome, "created")
        self.assertEqual(saved["application_id"], 100)
        self.assertEqual(saved["status"], "Pending")

    def test_cannot_schedule_before_applicant_is_shortlisted(self) -> None:
        result = save_interview(
            self.connection,
            employer_id=1,
            application_id=101,
            details=interview_details(),
            now=NOW,
        )

        self.assertEqual(result.outcome, "not_shortlisted")

    def test_employer_cannot_schedule_for_another_company(self) -> None:
        result = save_interview(
            self.connection,
            employer_id=2,
            application_id=100,
            details=interview_details(),
            now=NOW,
        )

        self.assertEqual(result.outcome, "not_found")

    def test_rescheduling_resets_applicant_response_to_pending(self) -> None:
        created = self.create_interview()
        respond_to_interview(
            self.connection,
            seeker_id=7,
            interview_id=created.record_id or 0,
            response="Declined",
            reason="The interview conflicts with another appointment.",
            now=NOW,
        )
        result = save_interview(
            self.connection,
            employer_id=1,
            application_id=100,
            details=interview_details(scheduled_time="14:30"),
            now=NOW,
        )
        saved = self.connection.execute(
            "SELECT * FROM interviews WHERE interview_id = ?",
            (created.record_id,),
        ).fetchone()

        self.assertEqual(result.outcome, "rescheduled")
        self.assertEqual(saved["status"], "Pending")
        self.assertIsNone(saved["seeker_response_at"])
        self.assertIsNone(saved["seeker_response_reason"])
        self.assertIsNone(saved["cancellation_reason"])

    def test_seeker_accepts_owned_pending_invitation(self) -> None:
        created = self.create_interview()
        result = respond_to_interview(
            self.connection,
            seeker_id=7,
            interview_id=created.record_id or 0,
            response="Accepted",
            now=NOW,
        )

        self.assertTrue(result.succeeded)
        self.assertEqual(result.outcome, "accepted")

    def test_seeker_must_give_reason_when_declining(self) -> None:
        created = self.create_interview()
        result = respond_to_interview(
            self.connection,
            seeker_id=7,
            interview_id=created.record_id or 0,
            response="Declined",
            reason="",
            now=NOW,
        )
        saved = self.connection.execute(
            "SELECT status FROM interviews WHERE interview_id = ?",
            (created.record_id,),
        ).fetchone()

        self.assertEqual(result.outcome, "invalid_reason")
        self.assertEqual(saved["status"], "Pending")

    def test_decline_reason_is_saved_for_employer(self) -> None:
        created = self.create_interview()
        reason = "The interview conflicts with another appointment."
        result = respond_to_interview(
            self.connection,
            seeker_id=7,
            interview_id=created.record_id or 0,
            response="Declined",
            reason=reason,
            now=NOW,
        )
        interviews = get_employer_interviews(
            self.connection,
            employer_id=1,
            now=NOW,
        )

        self.assertTrue(result.succeeded)
        self.assertEqual(result.outcome, "declined")
        self.assertEqual(interviews[0]["seeker_response_reason"], reason)

    def test_interview_reason_cannot_exceed_500_characters(self) -> None:
        created = self.create_interview()
        result = respond_to_interview(
            self.connection,
            seeker_id=7,
            interview_id=created.record_id or 0,
            response="Declined",
            reason="x" * 501,
            now=NOW,
        )

        self.assertEqual(result.outcome, "invalid_reason")
        self.assertIn("500", result.message)

    def test_seeker_cannot_respond_to_another_seekers_invitation(self) -> None:
        created = self.create_interview()
        result = respond_to_interview(
            self.connection,
            seeker_id=8,
            interview_id=created.record_id or 0,
            response="Accepted",
            now=NOW,
        )

        self.assertEqual(result.outcome, "not_found")

    def test_invitation_cannot_be_answered_twice(self) -> None:
        created = self.create_interview()
        respond_to_interview(
            self.connection,
            7,
            created.record_id or 0,
            "Declined",
            "The interview conflicts with another appointment.",
            now=NOW,
        )
        second_result = respond_to_interview(
            self.connection,
            7,
            created.record_id or 0,
            "Accepted",
            now=NOW,
        )

        self.assertEqual(second_result.outcome, "already_responded")

    def test_lists_are_scoped_to_logged_in_account(self) -> None:
        self.create_interview()
        save_interview(
            self.connection,
            employer_id=2,
            application_id=102,
            details=interview_details(),
            now=NOW,
        )

        seeker_interviews = get_seeker_interviews(
            self.connection,
            seeker_id=7,
            now=NOW,
        )
        employer_interviews = get_employer_interviews(
            self.connection,
            employer_id=1,
            now=NOW,
        )

        self.assertEqual(len(seeker_interviews), 2)
        self.assertEqual(len(employer_interviews), 1)
        self.assertEqual(employer_interviews[0]["job_id"], 10)

    def test_pending_count_includes_only_future_owned_invitations(self) -> None:
        self.create_interview()

        self.assertEqual(
            get_pending_interview_count(self.connection, 7, now=NOW),
            1,
        )
        self.assertEqual(
            get_pending_interview_count(self.connection, 8, now=NOW),
            0,
        )

    def test_employer_cancels_owned_active_interview(self) -> None:
        created = self.create_interview()
        result = cancel_interview(
            self.connection,
            employer_id=1,
            interview_id=created.record_id or 0,
            reason="The interviewer is unavailable at this time.",
        )

        self.assertTrue(result.succeeded)
        self.assertEqual(result.outcome, "cancelled")

    def test_employer_must_give_reason_when_cancelling(self) -> None:
        created = self.create_interview()
        result = cancel_interview(
            self.connection,
            employer_id=1,
            interview_id=created.record_id or 0,
            reason="No",
        )
        saved = self.connection.execute(
            "SELECT status FROM interviews WHERE interview_id = ?",
            (created.record_id,),
        ).fetchone()

        self.assertEqual(result.outcome, "invalid_reason")
        self.assertEqual(saved["status"], "Pending")

    def test_cancellation_reason_is_visible_to_seeker(self) -> None:
        created = self.create_interview()
        reason = "The interviewer is unavailable at this time."
        result = cancel_interview(
            self.connection,
            employer_id=1,
            interview_id=created.record_id or 0,
            reason=reason,
        )
        interviews = get_seeker_interviews(
            self.connection,
            seeker_id=7,
            now=NOW,
        )

        self.assertTrue(result.succeeded)
        self.assertEqual(interviews[0]["cancellation_reason"], reason)

    def test_other_employer_cannot_cancel_interview(self) -> None:
        created = self.create_interview()
        result = cancel_interview(
            self.connection,
            employer_id=2,
            interview_id=created.record_id or 0,
            reason="The interviewer is unavailable at this time.",
        )

        self.assertEqual(result.outcome, "not_found")

    def test_accepted_interview_can_be_completed_after_start_time(self) -> None:
        created = self.create_interview()
        respond_to_interview(
            self.connection,
            7,
            created.record_id or 0,
            "Accepted",
            now=NOW,
        )
        result = complete_interview(
            self.connection,
            employer_id=1,
            interview_id=created.record_id or 0,
            now=NOW + timedelta(days=7),
        )

        self.assertTrue(result.succeeded)
        self.assertEqual(result.outcome, "completed")

    def test_gets_owned_application_and_existing_interview(self) -> None:
        self.create_interview()
        application, interview = get_interview_application(
            self.connection,
            employer_id=1,
            application_id=100,
            now=NOW,
        )

        assert application is not None
        assert interview is not None
        self.assertEqual(application["applicant_name"], "Eddy Cheah")
        self.assertEqual(interview["status"], "Pending")
        self.assertTrue(interview["join_url"].startswith("https://"))

    def create_interview(self):
        return save_interview(
            self.connection,
            employer_id=1,
            application_id=100,
            details=interview_details(),
            now=NOW,
        )


if __name__ == "__main__":
    unittest.main()
