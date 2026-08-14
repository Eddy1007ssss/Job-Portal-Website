import sqlite3
import unittest

from src.saved_jobs import get_saved_jobs, toggle_saved_job


class SavedJobsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript("""
            CREATE TABLE employers (
                employer_id INTEGER PRIMARY KEY,
                company_name TEXT NOT NULL
            );

            CREATE TABLE jobs (
                job_id INTEGER PRIMARY KEY,
                employer_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                location TEXT,
                employment_type TEXT,
                salary_min INTEGER,
                salary_max INTEGER,
                category TEXT,
                experience_level TEXT,
                work_mode TEXT,
                status TEXT NOT NULL
            );

            CREATE TABLE saved_jobs (
                saved_job_id INTEGER PRIMARY KEY AUTOINCREMENT,
                seeker_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                saved_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(seeker_id, job_id)
            );

            INSERT INTO employers VALUES (1, 'Zenith Labs');
            INSERT INTO employers VALUES (2, 'Northstar Studio');

            INSERT INTO jobs VALUES (
                10, 1, 'Frontend Developer', 'Build accessible interfaces',
                'Remote', 'Full-time', 50000, 80000, 'Development',
                'Mid Level', 'Remote', 'Open'
            );
            INSERT INTO jobs VALUES (
                20, 2, 'Product Designer', 'Design product experiences',
                'Penang', 'Contract', 70000, 100000, 'Design',
                'Senior Level', 'Hybrid', 'Closed'
            );
            INSERT INTO jobs VALUES (
                30, 2, 'QA Engineer', 'Test web applications',
                'Kuala Lumpur', 'Full-time', 45000, 65000, 'Quality',
                'Entry Level', 'On-site', 'Open'
            );

            INSERT INTO saved_jobs VALUES (
                1, 7, 20, '2026-08-01 10:00:00'
            );
            INSERT INTO saved_jobs VALUES (
                2, 8, 30, '2026-08-02 10:00:00'
            );
            """)

    def tearDown(self) -> None:
        self.connection.close()

    def saved_count(self, seeker_id: int, job_id: int) -> int:
        return int(
            self.connection.execute(
                """
                SELECT COUNT(*)
                FROM saved_jobs
                WHERE seeker_id = ? AND job_id = ?
                """,
                (seeker_id, job_id),
            ).fetchone()[0]
        )

    def test_saves_open_job_under_logged_in_seeker(self) -> None:
        result = toggle_saved_job(self.connection, seeker_id=7, job_id=10)

        self.assertEqual(result.outcome, "saved")
        self.assertTrue(result.succeeded)
        self.assertEqual(self.saved_count(7, 10), 1)
        self.assertEqual(self.saved_count(8, 10), 0)

    def test_second_toggle_removes_saved_job(self) -> None:
        toggle_saved_job(self.connection, seeker_id=7, job_id=10)
        result = toggle_saved_job(self.connection, seeker_id=7, job_id=10)

        self.assertEqual(result.outcome, "removed")
        self.assertEqual(self.saved_count(7, 10), 0)

    def test_can_remove_saved_job_after_it_closes(self) -> None:
        result = toggle_saved_job(self.connection, seeker_id=7, job_id=20)

        self.assertEqual(result.outcome, "removed")
        self.assertEqual(self.saved_count(7, 20), 0)

    def test_cannot_newly_save_closed_or_missing_job(self) -> None:
        closed_result = toggle_saved_job(
            self.connection,
            seeker_id=9,
            job_id=20,
        )
        missing_result = toggle_saved_job(
            self.connection,
            seeker_id=9,
            job_id=999,
        )

        self.assertEqual(closed_result.outcome, "unavailable")
        self.assertEqual(missing_result.outcome, "not_found")
        self.assertEqual(self.saved_count(9, 20), 0)

    def test_saved_list_contains_only_current_seekers_jobs(self) -> None:
        toggle_saved_job(self.connection, seeker_id=7, job_id=10)
        saved_jobs = get_saved_jobs(self.connection, seeker_id=7)

        self.assertEqual(
            [saved_job["job_id"] for saved_job in saved_jobs],
            [10, 20],
        )
        self.assertNotIn(30, [job["job_id"] for job in saved_jobs])
        self.assertTrue(saved_jobs[0]["is_available"])
        self.assertFalse(saved_jobs[1]["is_available"])
        self.assertEqual(saved_jobs[1]["saved_date"], "01 Aug 2026")


if __name__ == "__main__":
    unittest.main()
