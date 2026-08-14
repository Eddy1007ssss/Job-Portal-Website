from dataclasses import dataclass
from typing import Any

SORT_OPTIONS = {
    "newest": "jobs.created_at DESC",
    "oldest": "jobs.created_at ASC",
    "salary_high": """
        COALESCE(jobs.salary_max, jobs.salary_min, 0) DESC
    """,
    "salary_low": """
        COALESCE(jobs.salary_min, jobs.salary_max, 0) ASC
    """,
    "title_az": "jobs.title COLLATE NOCASE ASC",
}


@dataclass
class JobFilters:
    keyword: str
    location: str
    category: str
    employment_type: str
    experience_level: str
    work_mode: str
    minimum_salary: int | None
    maximum_salary: int | None
    sort: str
    page: int


def parse_optional_integer(value: str | None) -> int | None:
    """Convert an optional query parameter to an integer."""

    if value is None:
        return None

    cleaned_value = value.strip()

    if not cleaned_value:
        return None

    try:
        return int(cleaned_value)
    except ValueError:
        return None


def build_job_filter_query(filters: JobFilters) -> tuple[str, list[Any]]:
    """Build a parameterized SQL condition for the Find Jobs page."""

    conditions = ["jobs.status = 'Open'"]
    parameters: list[Any] = []

    if filters.keyword:
        keyword = f"%{filters.keyword}%"
        conditions.append("""
            (
                jobs.title LIKE ?
                OR employers.company_name LIKE ?
                OR jobs.requirements LIKE ?
                OR jobs.description LIKE ?
                OR jobs.category LIKE ?
            )
            """)
        parameters.extend([keyword] * 5)

    if filters.location:
        conditions.append("jobs.location LIKE ?")
        parameters.append(f"%{filters.location}%")

    if filters.category:
        conditions.append("jobs.category = ?")
        parameters.append(filters.category)

    if filters.employment_type:
        conditions.append("jobs.employment_type = ?")
        parameters.append(filters.employment_type)

    if filters.experience_level:
        conditions.append("jobs.experience_level = ?")
        parameters.append(filters.experience_level)

    if filters.work_mode:
        conditions.append("jobs.work_mode = ?")
        parameters.append(filters.work_mode)

    if filters.minimum_salary is not None:
        conditions.append("""
            COALESCE(
                jobs.salary_max,
                jobs.salary_min,
                0
            ) >= ?
            """)
        parameters.append(filters.minimum_salary)

    if filters.maximum_salary is not None:
        conditions.append("""
            COALESCE(
                jobs.salary_min,
                jobs.salary_max,
                0
            ) <= ?
            """)
        parameters.append(filters.maximum_salary)

    return " AND ".join(conditions), parameters
