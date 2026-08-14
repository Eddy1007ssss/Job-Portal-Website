import sqlite3
import unittest

from src.portal_pages import (
    create_job_notifications_for_job,
    get_companies,
    get_job_notifications,
    get_notification_job_id,
    get_portal_stats,
    get_seeker_settings,
    get_unread_notification_count,
    mark_all_notifications_read,
    mark_notification_read,
    sync_recent_job_notifications,
    update_seeker_settings,
)


class PortalPageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript("""
            CREATE TABLE seekers (
                seeker_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                contact_number TEXT
            );

            CREATE TABLE employers (
                employer_id INTEGER PRIMARY KEY,
                company_name TEXT NOT NULL
            );

            CREATE TABLE company_profiles (
                profile_id INTEGER PRIMARY KEY,
                employer_id INTEGER NOT NULL UNIQUE,
                company_name TEXT NOT NULL,
                industry TEXT,
                address TEXT,
                company_description TEXT,
                company_size TEXT,
                logo_url TEXT
            );

            CREATE TABLE jobs (
                job_id INTEGER PRIMARY KEY,
                employer_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                requirements TEXT,
                location TEXT,
                employment_type TEXT,
                work_mode TEXT,
                status TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employer_id) REFERENCES employers(employer_id)
            );

            CREATE TABLE job_notifications (
                notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                seeker_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (seeker_id, job_id),
                FOREIGN KEY (seeker_id) REFERENCES seekers(seeker_id)
                    ON DELETE CASCADE,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE seeker_settings (
                settings_id INTEGER PRIMARY KEY AUTOINCREMENT,
                seeker_id INTEGER NOT NULL UNIQUE,
                email_notifications INTEGER NOT NULL DEFAULT 1,
                application_updates INTEGER NOT NULL DEFAULT 1,
                job_recommendations INTEGER NOT NULL DEFAULT 1,
                profile_visibility TEXT NOT NULL DEFAULT 'Employers',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            INSERT INTO seekers VALUES (
                7, 'Eddy Cheah', 'eddy@example.com', '0123456789'
            );
            INSERT INTO seekers VALUES (
                8, 'Other Seeker', 'other@example.com', NULL
            );

            INSERT INTO employers VALUES (1, 'Zenith Labs');
            INSERT INTO employers VALUES (2, 'Northstar Studio');

            INSERT INTO company_profiles VALUES (
                1, 1, 'Zenith Labs', 'Technology', 'Kuala Lumpur',
                'Builds cloud products', '51-200', NULL
            );
            INSERT INTO company_profiles VALUES (
                2, 2, 'Northstar Studio', 'Design', 'Penang',
                'Creates digital experiences', '11-50', NULL
            );

            INSERT INTO jobs VALUES (
                10, 1, 'Python Developer', 'Build APIs', 'Python and Flask',
                'Kuala Lumpur', 'Full-time', 'On-site', 'Open',
                '2026-08-13 09:00:00'
            );
            INSERT INTO jobs VALUES (
                20, 1, 'QA Engineer', 'Test cloud products', 'Automation',
                'Kuala Lumpur', 'Full-time', 'Hybrid', 'Closed',
                '2026-08-14 09:00:00'
            );
            INSERT INTO jobs VALUES (
                30, 2, 'UI/UX Designer', 'Design user experiences', 'Figma',
                'Penang', 'Contract', 'Remote', 'Open',
                '2026-08-14 10:00:00'
            );

            INSERT INTO job_notifications (
                notification_id, seeker_id, job_id, is_read, created_at
            ) VALUES (
                1, 8, 30, 0, '2026-08-14 10:01:00'
            );
            """)

    def tearDown(self) -> None:
        self.connection.close()

    def test_company_list_includes_only_open_job_counts(self) -> None:
        companies = get_companies(self.connection)

        self.assertEqual(companies[0]["company_name"], "Northstar Studio")
        self.assertEqual(companies[0]["active_job_count"], 1)
        self.assertEqual(companies[1]["company_name"], "Zenith Labs")
        self.assertEqual(companies[1]["active_job_count"], 1)

    def test_about_stats_use_current_database_counts(self) -> None:
        stats = get_portal_stats(self.connection)

        self.assertEqual(stats["company_count"], 2)
        self.assertEqual(stats["open_job_count"], 2)
        self.assertEqual(stats["seeker_count"], 2)

    def test_open_job_creates_notification_for_every_seeker(self) -> None:
        created_count = create_job_notifications_for_job(
            self.connection,
            10,
        )
        recipients = self.connection.execute("""
            SELECT seeker_id
            FROM job_notifications
            WHERE job_id = 10
            ORDER BY seeker_id
            """).fetchall()

        self.assertEqual(created_count, 2)
        self.assertEqual([row["seeker_id"] for row in recipients], [7, 8])

    def test_closed_job_does_not_create_notifications(self) -> None:
        created_count = create_job_notifications_for_job(
            self.connection,
            20,
        )

        self.assertEqual(created_count, 0)
        self.assertEqual(
            self.connection.execute(
                "SELECT COUNT(*) FROM job_notifications WHERE job_id = 20"
            ).fetchone()[0],
            0,
        )

    def test_duplicate_job_notifications_are_not_created(self) -> None:
        first_count = create_job_notifications_for_job(self.connection, 10)
        second_count = create_job_notifications_for_job(self.connection, 10)

        self.assertEqual(first_count, 2)
        self.assertEqual(second_count, 0)

    def test_sync_adds_recent_open_jobs_only_for_current_seeker(self) -> None:
        created_count = sync_recent_job_notifications(self.connection, 7)
        job_ids = self.connection.execute("""
            SELECT job_id
            FROM job_notifications
            WHERE seeker_id = 7
            ORDER BY job_id
            """).fetchall()

        self.assertEqual(created_count, 2)
        self.assertEqual([row["job_id"] for row in job_ids], [10, 30])
        self.assertEqual(
            self.connection.execute("""
                SELECT COUNT(*)
                FROM job_notifications
                WHERE seeker_id = 8 AND job_id = 10
                """).fetchone()[0],
            0,
        )

    def test_notification_list_is_scoped_to_current_seeker(self) -> None:
        sync_recent_job_notifications(self.connection, 7)
        notifications = get_job_notifications(self.connection, 7)

        self.assertEqual(len(notifications), 2)
        self.assertEqual(
            {notification["job_id"] for notification in notifications},
            {10, 30},
        )
        self.assertTrue(
            all(
                "posted a new job" in notification["message"]
                for notification in notifications
            )
        )

    def test_mark_notification_read_requires_ownership(self) -> None:
        result = mark_notification_read(self.connection, 7, 1)

        self.assertEqual(result.outcome, "not_found")
        self.assertEqual(
            self.connection.execute("""
                SELECT is_read
                FROM job_notifications
                WHERE notification_id = 1
                """).fetchone()[0],
            0,
        )

    def test_can_mark_owned_notification_as_read(self) -> None:
        sync_recent_job_notifications(self.connection, 7)
        notification_id = self.connection.execute("""
            SELECT notification_id
            FROM job_notifications
            WHERE seeker_id = 7 AND job_id = 10
            """).fetchone()[0]

        result = mark_notification_read(
            self.connection,
            7,
            notification_id,
        )

        self.assertTrue(result.succeeded)
        self.assertEqual(get_unread_notification_count(self.connection, 7), 1)

    def test_mark_all_read_only_changes_current_seekers_notifications(self) -> None:
        sync_recent_job_notifications(self.connection, 7)
        updated_count = mark_all_notifications_read(self.connection, 7)

        self.assertEqual(updated_count, 2)
        self.assertEqual(get_unread_notification_count(self.connection, 7), 0)
        self.assertEqual(get_unread_notification_count(self.connection, 8), 1)

    def test_notification_job_lookup_requires_ownership(self) -> None:
        self.assertIsNone(get_notification_job_id(self.connection, 7, 1))
        self.assertEqual(get_notification_job_id(self.connection, 8, 1), 30)

    def test_settings_return_safe_defaults(self) -> None:
        settings = get_seeker_settings(self.connection, 7)

        self.assertTrue(settings["email_notifications"])
        self.assertTrue(settings["application_updates"])
        self.assertTrue(settings["job_recommendations"])
        self.assertEqual(settings["profile_visibility"], "Employers")

    def test_updates_settings_only_for_selected_seeker(self) -> None:
        result = update_seeker_settings(
            self.connection,
            7,
            email_notifications=False,
            application_updates=True,
            job_recommendations=False,
            profile_visibility="Private",
        )
        settings = get_seeker_settings(self.connection, 7)

        self.assertTrue(result.succeeded)
        self.assertFalse(settings["email_notifications"])
        self.assertTrue(settings["application_updates"])
        self.assertFalse(settings["job_recommendations"])
        self.assertEqual(settings["profile_visibility"], "Private")

    def test_rejects_invalid_profile_visibility(self) -> None:
        result = update_seeker_settings(
            self.connection,
            7,
            True,
            True,
            True,
            "Everyone",
        )

        self.assertEqual(result.outcome, "invalid")


if __name__ == "__main__":
    unittest.main()
