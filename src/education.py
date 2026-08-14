from dataclasses import dataclass
from typing import IO, Protocol

from PIL import Image, UnidentifiedImageError

EDUCATION_STATUSES = {"Completed", "In Progress"}
MINIMUM_EDUCATION_YEAR = 1900
EDUCATION_CERTIFICATE_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
EDUCATION_CERTIFICATE_IMAGE_FORMATS = {"PNG", "JPEG"}
EDUCATION_CERTIFICATE_MAX_SIZE = 5 * 1024 * 1024


class EducationCertificateUpload(Protocol):
    @property
    def filename(self) -> str | None: ...

    @property
    def stream(self) -> IO[bytes]: ...


class EducationCertificateError(ValueError):
    """Raised when an education certificate upload is invalid."""


@dataclass(frozen=True)
class EducationDetails:
    qualification: str
    institution: str
    field_of_study: str
    start_year: str
    end_year: str
    status: str


def validate_education_details(
    details: EducationDetails,
    current_year: int,
) -> str | None:
    """Validate the fields shared by add and update education requests."""

    if not details.qualification:
        return "Qualification is required."

    if not details.institution:
        return "Institution is required."

    if not details.field_of_study:
        return "Field of study is required."

    if details.status not in EDUCATION_STATUSES:
        return "Select a valid education status."

    if not _is_valid_year(details.start_year):
        return "Start year must be a valid four-digit year."

    if not _is_valid_year(details.end_year):
        return "End year must be a valid four-digit year."

    start_year = int(details.start_year)
    end_year = int(details.end_year)

    if start_year < MINIMUM_EDUCATION_YEAR:
        return f"Start year cannot be earlier than {MINIMUM_EDUCATION_YEAR}."

    if start_year > current_year:
        return "Start year cannot be in the future."

    if end_year < start_year:
        return "End year cannot be earlier than start year."

    if details.status == "Completed" and end_year > current_year:
        return "A completed education end year cannot be in the future."

    return None


def validate_education_certificate(file: EducationCertificateUpload) -> str:
    """Validate an uploaded certificate and return its normalized extension."""

    original_filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1]

    if "." not in original_filename:
        raise EducationCertificateError(
            "Certificate must be a PDF, PNG, JPG or JPEG file."
        )

    extension = original_filename.rsplit(".", 1)[1].lower()

    if extension not in EDUCATION_CERTIFICATE_EXTENSIONS:
        raise EducationCertificateError(
            "Certificate must be a PDF, PNG, JPG or JPEG file."
        )

    file.stream.seek(0, 2)
    file_size = file.stream.tell()
    file.stream.seek(0)

    if file_size <= 0:
        raise EducationCertificateError("Certificate file cannot be empty.")

    if file_size > EDUCATION_CERTIFICATE_MAX_SIZE:
        raise EducationCertificateError("Certificate file must not exceed 5 MB.")

    if extension == "pdf":
        signature = file.stream.read(5)
        file.stream.seek(0)

        if signature != b"%PDF-":
            raise EducationCertificateError("Certificate is not a valid PDF file.")

        return "pdf"

    try:
        with Image.open(file.stream) as uploaded_image:
            uploaded_image.verify()
            image_format = uploaded_image.format
    except (UnidentifiedImageError, OSError, SyntaxError) as error:
        raise EducationCertificateError(
            "Certificate is not a valid image file."
        ) from error
    finally:
        file.stream.seek(0)

    if image_format not in EDUCATION_CERTIFICATE_IMAGE_FORMATS:
        raise EducationCertificateError(
            "Certificate must be a PDF, PNG, JPG or JPEG file."
        )

    expected_format = "PNG" if extension == "png" else "JPEG"

    if image_format != expected_format:
        raise EducationCertificateError(
            "Certificate file extension does not match its contents."
        )

    return "png" if image_format == "PNG" else "jpg"


def _is_valid_year(value: str) -> bool:
    return len(value) == 4 and value.isdigit()
