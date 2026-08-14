import sqlite3
import unittest

from src.profile_credentials import (
    CertificateDetails,
    add_certificate_record,
    add_skill_record,
    get_certificate_record,
    update_certificate_record,
    update_skill_record,
    validate_certificate_details,
    validate_skill_name,
)

CURRENT_MONTH = "2026-08"


def certificate_details(**overrides: str) -> CertificateDetails:
    values = {
        "name": "AWS Cloud Practitioner",
        "issuer": "Amazon Web Services",
        "issue_date": "2026-06",
    }
    values.update(overrides)
    return CertificateDetails(**values)


class ProfileCredentialValidationTests(unittest.TestCase):
    def test_requires_skill_name(self) -> None:
        self.assertEqual(validate_skill_name("  "), "Skill name is required.")

    def test_rejects_skill_name_over_80_characters(self) -> None:
        self.assertEqual(
            validate_skill_name("x" * 81),
            "Skill name must not exceed 80 characters.",
        )

    def test_accepts_certificate_without_optional_fields(self) -> None:
        result = validate_certificate_details(
            certificate_details(issuer="", issue_date=""),
            CURRENT_MONTH,
        )

        self.assertIsNone(result)

    def test_requires_certificate_name(self) -> None:
        result = validate_certificate_details(
            certificate_details(name=""),
            CURRENT_MONTH,
        )

        self.assertEqual(result, "Certificate name is required.")

    def test_rejects_invalid_certificate_month(self) -> None:
        result = validate_certificate_details(
            certificate_details(issue_date="2026-13"),
            CURRENT_MONTH,
        )

        self.assertEqual(
            result,
            "Certificate issue date must be a valid month.",
        )

    def test_rejects_future_certificate_month(self) -> None:
        result = validate_certificate_details(
            certificate_details(issue_date="2026-09"),
            CURRENT_MONTH,
        )

        self.assertEqual(
            result,
            "Certificate issue date cannot be in the future.",
        )


class ProfileCredentialDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript("""
            CREATE TABLE seeker_skills (
                skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                seeker_id INTEGER NOT NULL,
                skill_name TEXT NOT NULL,
                UNIQUE(seeker_id, skill_name)
            );

            CREATE TABLE seeker_certificates (
                certificate_id INTEGER PRIMARY KEY AUTOINCREMENT,
                seeker_id INTEGER NOT NULL,
                certificate_name TEXT NOT NULL,
                issuer TEXT,
                issue_date TEXT,
                certificate_filename TEXT,
                original_filename TEXT
            );

            INSERT INTO seeker_skills VALUES (1, 7, 'Python');
            INSERT INTO seeker_skills VALUES (2, 8, 'Java');

            INSERT INTO seeker_certificates VALUES (
                1, 7, 'Google UX Design', 'Google', '2025-05',
                'certificate_7_old.pdf', 'google-ux.pdf'
            );
            INSERT INTO seeker_certificates VALUES (
                2, 8, 'Azure Fundamentals', 'Microsoft', '2025-07',
                NULL, NULL
            );
            """)

    def tearDown(self) -> None:
        self.connection.close()

    def test_adds_multiple_skills_for_one_seeker(self) -> None:
        first = add_skill_record(self.connection, 7, "  JavaScript  ")
        second = add_skill_record(self.connection, 7, "SQL")
        saved_names = [row["skill_name"] for row in self.connection.execute("""
                SELECT skill_name
                FROM seeker_skills
                WHERE seeker_id = 7
                ORDER BY skill_name
                """).fetchall()]

        self.assertTrue(first.succeeded)
        self.assertTrue(second.succeeded)
        self.assertEqual(saved_names, ["JavaScript", "Python", "SQL"])

    def test_blocks_case_insensitive_duplicate_skill(self) -> None:
        result = add_skill_record(self.connection, 7, "python")

        self.assertEqual(result.outcome, "duplicate")

    def test_updates_only_skill_owned_by_seeker(self) -> None:
        result = update_skill_record(self.connection, 7, 1, "Python 3")
        blocked = update_skill_record(self.connection, 7, 2, "Kotlin")

        self.assertEqual(result.outcome, "updated")
        self.assertEqual(blocked.outcome, "not_found")
        self.assertEqual(
            self.connection.execute(
                "SELECT skill_name FROM seeker_skills WHERE skill_id = 1"
            ).fetchone()["skill_name"],
            "Python 3",
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT skill_name FROM seeker_skills WHERE skill_id = 2"
            ).fetchone()["skill_name"],
            "Java",
        )

    def test_blocks_duplicate_when_updating_skill(self) -> None:
        add_skill_record(self.connection, 7, "SQL")
        result = update_skill_record(self.connection, 7, 1, "sql")

        self.assertEqual(result.outcome, "duplicate")

    def test_adds_multiple_certificates_with_optional_files(self) -> None:
        first = add_certificate_record(
            self.connection,
            7,
            certificate_details(),
            "certificate_7_aws.pdf",
            "aws.pdf",
        )
        second = add_certificate_record(
            self.connection,
            7,
            certificate_details(
                name="Scrum Foundation",
                issuer="CertiProf",
                issue_date="",
            ),
        )
        count = self.connection.execute(
            "SELECT COUNT(*) FROM seeker_certificates WHERE seeker_id = 7"
        ).fetchone()[0]

        self.assertTrue(first.succeeded)
        self.assertTrue(second.succeeded)
        self.assertEqual(count, 3)

    def test_updates_certificate_details_and_file(self) -> None:
        result = update_certificate_record(
            self.connection,
            7,
            1,
            certificate_details(name="Google UX Design Professional"),
            "certificate_7_new.pdf",
            "updated-google-ux.pdf",
        )
        saved = get_certificate_record(self.connection, 7, 1)

        self.assertEqual(result.outcome, "updated")
        self.assertEqual(
            saved["certificate_name"],
            "Google UX Design Professional",
        )
        self.assertEqual(saved["original_filename"], "updated-google-ux.pdf")

    def test_can_remove_certificate_file_while_updating(self) -> None:
        result = update_certificate_record(
            self.connection,
            7,
            1,
            certificate_details(name="Google UX Design"),
            None,
            None,
        )
        saved = get_certificate_record(self.connection, 7, 1)

        self.assertTrue(result.succeeded)
        self.assertIsNone(saved["certificate_filename"])
        self.assertIsNone(saved["original_filename"])

    def test_cannot_update_or_read_another_seekers_certificate(self) -> None:
        result = update_certificate_record(
            self.connection,
            7,
            2,
            certificate_details(name="Changed"),
            None,
            None,
        )

        self.assertEqual(result.outcome, "not_found")
        self.assertIsNone(get_certificate_record(self.connection, 7, 2))
        unchanged = get_certificate_record(self.connection, 8, 2)
        self.assertEqual(unchanged["certificate_name"], "Azure Fundamentals")


if __name__ == "__main__":
    unittest.main()
