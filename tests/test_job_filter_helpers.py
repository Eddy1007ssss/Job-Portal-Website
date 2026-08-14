"""Unit tests for job-listing filter parsing and SQL parameter building."""

import pytest

from src.jobs import (
    JobFilters,
    build_job_filter_query,
    get_current_seeker_id,
    parse_optional_integer,
    read_job_filters,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("", None),
        ("   ", None),
        ("0", 0),
        ("1", 1),
        ("42", 42),
        (" 42 ", 42),
        ("-1", -1),
        ("+7", 7),
        ("0010", 10),
        ("3.5", None),
        ("1,000", None),
        ("abc", None),
        ("12abc", None),
        ("--2", None),
        ("0x10", None),
    ],
)
def test_parse_optional_integer_cases(value, expected):
    assert parse_optional_integer(value) == expected


def make_filters(**overrides):
    values = {
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


@pytest.mark.parametrize(
    ("overrides", "expected_clause", "expected_parameters"),
    [
        ({}, "jobs.status = 'Open'", []),
        (
            {"keyword": "Python"},
            "jobs.title LIKE ?",
            ["%Python%", "%Python%", "%Python%", "%Python%", "%Python%"],
        ),
        ({"location": "Kuala Lumpur"}, "jobs.location LIKE ?", ["%Kuala Lumpur%"]),
        ({"category": "Development"}, "jobs.category = ?", ["Development"]),
        ({"employment_type": "Full-time"}, "jobs.employment_type = ?", ["Full-time"]),
        (
            {"experience_level": "Entry Level"},
            "jobs.experience_level = ?",
            ["Entry Level"],
        ),
        ({"work_mode": "Hybrid"}, "jobs.work_mode = ?", ["Hybrid"]),
        ({"minimum_salary": 3000}, "jobs.salary_max", [3000]),
        ({"maximum_salary": 6000}, "jobs.salary_min", [6000]),
    ],
)
def test_build_job_filter_query_single_filter(
    overrides,
    expected_clause,
    expected_parameters,
):
    where_clause, parameters = build_job_filter_query(make_filters(**overrides))

    assert "jobs.status = 'Open'" in where_clause
    assert expected_clause in where_clause
    assert parameters == expected_parameters


def test_build_job_filter_query_combines_all_parameters_in_order():
    filters = make_filters(
        keyword="Engineer",
        location="Penang",
        category="Development",
        employment_type="Full-time",
        experience_level="Mid Level",
        work_mode="Remote",
        minimum_salary=4000,
        maximum_salary=9000,
    )

    where_clause, parameters = build_job_filter_query(filters)

    assert where_clause.count("?") == 12
    assert parameters == [
        "%Engineer%",
        "%Engineer%",
        "%Engineer%",
        "%Engineer%",
        "%Engineer%",
        "%Penang%",
        "Development",
        "Full-time",
        "Mid Level",
        "Remote",
        4000,
        9000,
    ]


@pytest.mark.parametrize(
    ("query_string", "attribute", "expected"),
    [
        ({}, "page", 1),
        ({"page": "0"}, "page", 1),
        ({"page": "-5"}, "page", 1),
        ({"page": "3"}, "page", 3),
        ({"sort": "salary_high"}, "sort", "salary_high"),
        ({"sort": "invalid-sort"}, "sort", "newest"),
        ({"keyword": "  Python Developer  "}, "keyword", "Python Developer"),
        ({"location": "  Johor  "}, "location", "Johor"),
        ({"minimum_salary": "3500"}, "minimum_salary", 3500),
        ({"maximum_salary": "not-number"}, "maximum_salary", None),
    ],
)
def test_read_job_filters_normalizes_query_values(
    app,
    query_string,
    attribute,
    expected,
):
    with app.test_request_context("/jobs", query_string=query_string):
        filters = read_job_filters()

    assert getattr(filters, attribute) == expected


@pytest.mark.parametrize(
    ("session_values", "expected"),
    [
        ({}, None),
        ({"seeker_authenticated": False, "seeker_id": 5}, None),
        ({"seeker_authenticated": "true", "seeker_id": 5}, None),
        ({"seeker_authenticated": True}, None),
        ({"seeker_authenticated": True, "seeker_id": None}, None),
        ({"seeker_authenticated": True, "seeker_id": "7"}, 7),
        ({"seeker_authenticated": True, "seeker_id": 8}, 8),
        ({"seeker_authenticated": True, "seeker_id": "invalid"}, None),
    ],
)
def test_get_current_seeker_id_requires_valid_authenticated_session(
    app,
    session_values,
    expected,
):
    with app.test_request_context("/jobs"):
        from flask import session

        session.update(session_values)
        assert get_current_seeker_id() == expected
