"""Focused boundary tests for job-seeker validation helpers."""

from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo

import pytest
from werkzeug.datastructures import FileStorage

from src.seeker import (
    CERTIFICATE_EXTENSIONS,
    EMAIL_PATTERN,
    IMAGE_EXTENSIONS,
    PHONE_PATTERN,
    RESUME_EXTENSIONS,
    _allowed,
    _is_pdf,
    _parse_month,
    _validate_date_range,
    _validate_issue_month,
    _validate_month_range,
)


@pytest.mark.parametrize(
    ("filename", "extensions", "expected"),
    [
        ("avatar.png", IMAGE_EXTENSIONS, True),
        ("avatar.PNG", IMAGE_EXTENSIONS, True),
        ("photo.jpeg", IMAGE_EXTENSIONS, True),
        ("photo.webp", IMAGE_EXTENSIONS, True),
        ("photo.gif", IMAGE_EXTENSIONS, False),
        ("photo", IMAGE_EXTENSIONS, False),
        ("photo.", IMAGE_EXTENSIONS, False),
        ("archive.png.exe", IMAGE_EXTENSIONS, False),
        ("resume.pdf", RESUME_EXTENSIONS, True),
        ("resume.PDF", RESUME_EXTENSIONS, True),
        ("resume.docx", RESUME_EXTENSIONS, False),
        ("resume", RESUME_EXTENSIONS, False),
        ("certificate.pdf", CERTIFICATE_EXTENSIONS, True),
        ("certificate.DOC", CERTIFICATE_EXTENSIONS, True),
        ("certificate.docx", CERTIFICATE_EXTENSIONS, True),
        ("certificate.jpeg", CERTIFICATE_EXTENSIONS, True),
        ("certificate.txt", CERTIFICATE_EXTENSIONS, False),
        ("certificate", CERTIFICATE_EXTENSIONS, False),
    ],
)
def test_allowed_file_extensions(filename, extensions, expected):
    assert _allowed(filename, extensions) is expected


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (b"%PDF-1.7 document", True),
        (b"%PDF-", True),
        (b"%PDF", False),
        (b" %PDF-1.7", False),
        (b"", False),
        (b"\x89PNG\r\n", False),
        (b"%pdf-1.7", False),
    ],
)
def test_pdf_signature_validation(content, expected):
    uploaded_file = FileStorage(stream=BytesIO(content), filename="resume.pdf")

    assert _is_pdf(uploaded_file) is expected
    assert uploaded_file.stream.tell() == 0


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2024-01", (2024, 1, 1)),
        ("2024-12", (2024, 12, 1)),
        ("2000-02", (2000, 2, 1)),
        ("", None),
        (None, None),
        ("2024", None),
        ("2024-", None),
        ("-01", None),
        ("year-01", None),
        ("2024-month", None),
        ("2024-00", None),
        ("2024-13", None),
    ],
)
def test_parse_month_values(value, expected):
    result = _parse_month(value)

    if expected is None:
        assert result is None
    else:
        assert (result.year, result.month, result.day) == expected


@pytest.mark.parametrize(
    ("start_value", "end_value", "expected"),
    [
        ("", "", "Start date is required."),
        ("2024-01", "", None),
        ("2024-01", "Present", None),
        ("2024-01", "2024-01", None),
        ("2024-01", "2024-02", None),
        ("2024-02", "2024-01", "End date cannot be earlier than the start date."),
        ("2023-12", "2024-01", None),
        ("2024-10", "2024-09", "End date cannot be earlier than the start date."),
    ],
)
def test_experience_month_range_validation(start_value, end_value, expected):
    assert _validate_month_range(start_value, end_value) == expected


@pytest.mark.parametrize(
    ("email", "expected"),
    [
        ("user@example.com", True),
        ("first.last@example.com", True),
        ("user+jobs@example.com", True),
        ("user_name@example.co.uk", True),
        ("USER123@EXAMPLE.ORG", True),
        ("employee@sub.company.com", True),
        ("a1@b2.io", True),
        ("plainaddress", False),
        ("@example.com", False),
        ("user@", False),
        ("user@example", False),
        ("user@example.c", False),
        ("user name@example.com", False),
        ("user@example com", False),
    ],
)
def test_seeker_email_pattern(email, expected):
    assert (EMAIL_PATTERN.fullmatch(email) is not None) is expected


@pytest.mark.parametrize(
    ("phone", "expected"),
    [
        ("01234567", True),
        ("0123456789", True),
        ("012345678901234", True),
        ("+60123456789", True),
        ("012-3456789", True),
        ("012 345 6789", True),
        ("+60 12345678", True),
        ("0123456", False),
        ("0123456789012345", False),
        ("01234abc", False),
        ("(012)3456789", False),
        ("012_3456789", False),
        ("", False),
        ("+60.1234567", False),
    ],
)
def test_seeker_phone_pattern(phone, expected):
    assert (PHONE_PATTERN.fullmatch(phone) is not None) is expected


def _month_offset(offset):
    current = datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
    month_index = current.year * 12 + current.month - 1 + offset
    year, zero_based_month = divmod(month_index, 12)
    return f"{year:04d}-{zero_based_month + 1:02d}"


@pytest.mark.parametrize(
    ("start_value", "end_value", "expected"),
    [
        ("", "", "Please enter a valid start date."),
        ("not-a-date", "", "Please enter a valid start date."),
        (_month_offset(-2), "", None),
        (_month_offset(-2), _month_offset(0), None),
        (_month_offset(-1), _month_offset(-1), None),
        (_month_offset(0), "", None),
        (_month_offset(1), "", "The start date cannot be in the future."),
        (_month_offset(-1), _month_offset(1), "The end date cannot be in the future."),
        (
            _month_offset(0),
            _month_offset(-1),
            "The end date cannot be earlier than the start date.",
        ),
        (_month_offset(-1), "invalid", "Please enter a valid end date."),
    ],
)
def test_full_date_range_validation(start_value, end_value, expected):
    assert _validate_date_range(start_value, end_value) == expected


@pytest.mark.parametrize(
    ("issue_date", "expected"),
    [
        ("", None),
        (_month_offset(0), None),
        (_month_offset(-1), None),
        (_month_offset(1), "Certificate issue date cannot be in the future."),
        ("9999-12", "Certificate issue date cannot be in the future."),
    ],
)
def test_certificate_issue_month_validation(issue_date, expected):
    assert _validate_issue_month(issue_date) == expected
