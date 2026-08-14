import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class JobDepartmentEditTests(unittest.TestCase):
    def test_department_is_stored_by_create_and_edit_routes(self) -> None:
        jobs_source = (PROJECT_ROOT / "src" / "jobs.py").read_text()

        self.assertIn('"department": "TEXT"', jobs_source)
        self.assertGreaterEqual(
            jobs_source.count('request.form.get(\n        "department"'),
            2,
        )
        self.assertIn("department = ?", jobs_source)

    def test_edit_form_prefills_saved_department(self) -> None:
        template = (PROJECT_ROOT / "src" / "templates" / "edit_job.html").read_text()

        self.assertIn("job['department']", template)
        self.assertIn("form_data.get('department'", template)
        self.assertNotIn("\n    ...\n", template)


if __name__ == "__main__":
    unittest.main()
