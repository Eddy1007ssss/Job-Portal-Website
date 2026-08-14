import sqlite3
import unittest
from typing import Any

from src.job_search import (
    SORT_OPTIONS,
    JobFilters,
    build_job_filter_query,
    parse_optional_integer,
)


class JobSearchTests(unittest.TestCase):
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
                requirements TEXT,
                description TEXT,
                category TEXT,
                location TEXT,
                employment_type TEXT,
                experience_level TEXT,
                work_mode TEXT,
                salary_min INTEGER,
                salary_max INTEGER,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            INSERT INTO employers VALUES (1, 'Zenith Labs');
            INSERT INTO employers VALUES (2, 'Northstar Studio');

            INSERT INTO jobs VALUES (
                10, 1, 'Frontend Developer',
                'React, JavaScript and accessibility skills',
                'Build user interfaces', 'Development', 'Remote',
                'Full-time', 'Mid Level', 'Remote', 50000, 80000, 'Open',
                '2026-07-10 09:00:00'
            );
            INSERT INTO jobs VALUES (
                20, 2, 'Product Designer',
                'Figma and prototyping',
                'Design clear product experiences', 'Design', 'Penang',
                'Contract', 'Senior Level', 'Hybrid', 70000, 100000, 'Open',
                '2026-08-01 14:30:00'
            );
            INSERT INTO jobs VALUES (
                30, 1, 'React Engineer',
                'React', 'This vacancy is closed', 'Development', 'Remote',
                'Full-time', 'Mid Level', 'Remote', 60000, 90000, 'Closed',
                '2026-08-10 12:00:00'
            );
            """)

    def tearDown(self) -> None:
        self.connection.close()

    def make_filters(self, **overrides: Any) -> JobFilters:
        values: dict[str, Any] = {
            "keyword": "",
            "location": "",
            "category": "",
            "employment_type": "",
            "experience_level": "",
            "work_mode": "",
            "minimum_salary": None,
            "maximum_salary": None,
            "sort": "newest",
            "page": 1,
        }
        values.update(overrides)
        return JobFilters(**values)

    def search_titles(self, filters: JobFilters) -> list[str]:
        where_clause, parameters = build_job_filter_query(filters)
        rows = self.connection.execute(
            f"""
            SELECT jobs.title
            FROM jobs
            JOIN employers
                ON employers.employer_id = jobs.employer_id
            WHERE {where_clause}
            ORDER BY jobs.job_id
            """,
            parameters,
        ).fetchall()
        return [str(row["title"]) for row in rows]

    def sorted_titles(self, filters: JobFilters) -> list[str]:
        where_clause, parameters = build_job_filter_query(filters)
        rows = self.connection.execute(
            f"""
            SELECT jobs.title
            FROM jobs
            JOIN employers
                ON employers.employer_id = jobs.employer_id
            WHERE {where_clause}
            ORDER BY {SORT_OPTIONS[filters.sort]}
            """,
            parameters,
        ).fetchall()
        return [str(row["title"]) for row in rows]

    def test_keyword_searches_job_title_company_and_skill(self) -> None:
        self.assertEqual(
            self.search_titles(self.make_filters(keyword="Frontend")),
            ["Frontend Developer"],
        )
        self.assertEqual(
            self.search_titles(self.make_filters(keyword="Zenith")),
            ["Frontend Developer"],
        )
        self.assertEqual(
            self.search_titles(self.make_filters(keyword="JavaScript")),
            ["Frontend Developer"],
        )

    def test_filters_work_mode_and_salary_range(self) -> None:
        filters = self.make_filters(
            work_mode="Hybrid",
            minimum_salary=60000,
            maximum_salary=80000,
        )

        self.assertEqual(self.search_titles(filters), ["Product Designer"])

    def test_combines_location_salary_category_and_employment_type(self) -> None:
        filters = self.make_filters(
            location="Penang",
            category="Design",
            employment_type="Contract",
            minimum_salary=65000,
            maximum_salary=75000,
        )

        self.assertEqual(self.search_titles(filters), ["Product Designer"])

        no_match = self.make_filters(
            location="Penang",
            category="Development",
            employment_type="Contract",
            minimum_salary=65000,
            maximum_salary=75000,
        )
        self.assertEqual(self.search_titles(no_match), [])

    def test_closed_jobs_are_never_returned(self) -> None:
        filters = self.make_filters(keyword="React")

        self.assertEqual(self.search_titles(filters), ["Frontend Developer"])

    def test_invalid_optional_numbers_are_ignored(self) -> None:
        self.assertEqual(parse_optional_integer(" 50000 "), 50000)
        self.assertIsNone(parse_optional_integer(""))
        self.assertIsNone(parse_optional_integer("not-a-number"))

    def test_job_title_sort_uses_supported_value(self) -> None:
        self.assertIn("title_az", SORT_OPTIONS)
        self.assertIn("jobs.title", SORT_OPTIONS["title_az"])

    def test_sorts_open_jobs_by_latest_posting_date(self) -> None:
        filters = self.make_filters(sort="newest")

        self.assertEqual(
            self.sorted_titles(filters),
            ["Product Designer", "Frontend Developer"],
        )

    def test_sorts_open_jobs_by_salary_in_both_directions(self) -> None:
        highest_first = self.make_filters(sort="salary_high")
        lowest_first = self.make_filters(sort="salary_low")

        self.assertEqual(
            self.sorted_titles(highest_first),
            ["Product Designer", "Frontend Developer"],
        )
        self.assertEqual(
            self.sorted_titles(lowest_first),
            ["Frontend Developer", "Product Designer"],
        )

    def test_sorting_keeps_active_search_and_filter_criteria(self) -> None:
        filters = self.make_filters(
            keyword="React",
            location="Remote",
            category="Development",
            employment_type="Full-time",
            sort="salary_high",
        )

        self.assertEqual(self.sorted_titles(filters), ["Frontend Developer"])


if __name__ == "__main__":
    unittest.main()
