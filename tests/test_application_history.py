import sqlite3
import unittest

from src.application_history import (
    format_application_date,
    get_application_history,
    parse_application_history_options,
)


class ApplicationHistoryTests(unittest.TestCase):
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
                location TEXT NOT NULL,
                employment_type TEXT NOT NULL
            );

            CREATE TABLE applications (
                application_id INTEGER PRIMARY KEY,
                seeker_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                applied_at TEXT
            );

            INSERT INTO employers VALUES (1, 'Zenith Labs');
            INSERT INTO employers VALUES (2, 'Alpha Tech');

            INSERT INTO jobs VALUES (
                10, 1, 'Backend Developer', 'Kuala Lumpur', 'Full-time'
            );
            INSERT INTO jobs VALUES (
                20, 2, 'Frontend Developer', 'Penang', 'Internship'
            );
            INSERT INTO jobs VALUES (
                30, 2, 'QA Engineer', 'Remote', 'Full-time'
            );

            INSERT INTO applications VALUES (
                100, 7, 10, 'Pending', '2026-07-10 09:00:00'
            );
            INSERT INTO applications VALUES (
                101, 7, 20, 'Rejected', '2026-08-01 14:30:00'
            );
            INSERT INTO applications VALUES (
                102, 8, 30, 'Accepted', '2026-08-02 12:00:00'
            );
            """)

    def tearDown(self) -> None:
        self.connection.close()

    def test_returns_only_logged_in_seekers_history_newest_first(self) -> None:
        options = parse_application_history_options("all", "newest")

        applications, total_count = get_application_history(
            self.connection,
            seeker_id=7,
            options=options,
        )

        self.assertEqual(total_count, 2)
        application_ids = [
            application["application_id"] for application in applications
        ]
        self.assertEqual(application_ids, [101, 100])
        self.assertNotIn(102, application_ids)

    def test_history_contains_required_user_story_fields(self) -> None:
        options = parse_application_history_options("all", "newest")

        applications, _ = get_application_history(
            self.connection,
            seeker_id=7,
            options=options,
        )

        latest = applications[0]
        self.assertEqual(latest["title"], "Frontend Developer")
        self.assertEqual(latest["company_name"], "Alpha Tech")
        self.assertEqual(latest["application_date"], "01 Aug 2026")
        self.assertEqual(latest["application_status"], "Rejected")

    def test_filters_history_by_status_without_changing_total(self) -> None:
        options = parse_application_history_options("pending", "newest")

        applications, total_count = get_application_history(
            self.connection,
            seeker_id=7,
            options=options,
        )

        self.assertEqual(total_count, 2)
        self.assertEqual(len(applications), 1)
        self.assertEqual(applications[0]["application_status"], "Pending")

    def test_sorts_history_by_company_name(self) -> None:
        options = parse_application_history_options("all", "company")

        applications, _ = get_application_history(
            self.connection,
            seeker_id=7,
            options=options,
        )

        self.assertEqual(
            [application["company_name"] for application in applications],
            ["Alpha Tech", "Zenith Labs"],
        )

    def test_invalid_filter_and_sort_fall_back_to_safe_defaults(self) -> None:
        options = parse_application_history_options(
            "not-a-status",
            "DROP TABLE applications",
        )

        applications, total_count = get_application_history(
            self.connection,
            seeker_id=7,
            options=options,
        )

        self.assertEqual(options.status_key, "all")
        self.assertEqual(options.sort_key, "newest")
        self.assertEqual(total_count, 2)
        self.assertEqual(len(applications), 2)
        table = self.connection.execute(
            "SELECT name FROM sqlite_master WHERE name = 'applications'"
        ).fetchone()
        self.assertIsNotNone(table)

    def test_accepts_withdrawn_status_filter(self) -> None:
        options = parse_application_history_options("withdrawn", "newest")

        self.assertEqual(options.status_key, "withdrawn")
        self.assertEqual(options.status_value, "Withdrawn")

    def test_formats_missing_and_legacy_application_dates(self) -> None:
        self.assertEqual(format_application_date(None), "Date unavailable")
        self.assertEqual(format_application_date(""), "Date unavailable")
        self.assertEqual(
            format_application_date("legacy-date"),
            "legacy-date",
        )


if __name__ == "__main__":
    unittest.main()
