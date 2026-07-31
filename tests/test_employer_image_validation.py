"""Security and boundary tests for employer logo and banner uploads."""

from io import BytesIO

import pytest
from PIL import Image
from werkzeug.datastructures import FileStorage

from src.employer import ImageUploadError, validate_company_image


def make_upload(filename, content):
    return FileStorage(stream=BytesIO(content), filename=filename)


def make_image_bytes(image_format):
    stream = BytesIO()
    Image.new("RGB", (4, 4), color=(37, 99, 235)).save(
        stream,
        format=image_format,
    )
    return stream.getvalue()


@pytest.mark.parametrize(
    ("filename", "expected_message"),
    [
        ("", "No company logo file was selected."),
        ("logo", "Company logo must be a PNG or JPG image."),
        ("logo.gif", "Company logo must be a PNG or JPG image."),
        ("logo.webp", "Company logo must be a PNG or JPG image."),
        ("logo.svg", "Company logo must be a PNG or JPG image."),
        ("logo.pdf", "Company logo must be a PNG or JPG image."),
    ],
)
def test_company_image_rejects_missing_or_disallowed_filename(
    filename,
    expected_message,
):
    upload = make_upload(filename, b"content")

    with pytest.raises(ImageUploadError, match=expected_message):
        validate_company_image(upload, 1024, "Company logo")


@pytest.mark.parametrize(
    "filename",
    ["logo.png", "logo.jpg", "logo.jpeg"],
)
def test_company_image_rejects_empty_files(filename):
    upload = make_upload(filename, b"")

    with pytest.raises(ImageUploadError, match="Company logo file is empty"):
        validate_company_image(upload, 1024, "Company logo")


@pytest.mark.parametrize(
    "filename",
    ["logo.png", "logo.jpg", "logo.jpeg"],
)
def test_company_image_rejects_fake_image_content(filename):
    upload = make_upload(filename, b"This is not an image.")

    with pytest.raises(ImageUploadError, match="Company logo is not a valid image"):
        validate_company_image(upload, 1024, "Company logo")


@pytest.mark.parametrize(
    ("filename", "image_format", "expected_extension"),
    [
        ("logo.png", "PNG", "png"),
        ("logo.PNG", "PNG", "png"),
        ("logo.jpg", "JPEG", "jpg"),
        ("logo.jpeg", "JPEG", "jpg"),
    ],
)
def test_company_image_accepts_real_png_and_jpeg_files(
    filename,
    image_format,
    expected_extension,
):
    upload = make_upload(filename, make_image_bytes(image_format))

    result = validate_company_image(upload, 1024 * 1024, "Company logo")

    assert result == expected_extension
    assert upload.stream.tell() == 0


@pytest.mark.parametrize(
    ("image_name", "maximum_size", "expected_message"),
    [
        ("Company logo", 1024 * 1024, "Company logo must not exceed 1 MB"),
        ("Company banner", 2 * 1024 * 1024, "Company banner must not exceed 2 MB"),
    ],
)
def test_company_image_rejects_files_over_configured_limit(
    image_name,
    maximum_size,
    expected_message,
):
    upload = make_upload("image.png", b"x" * (maximum_size + 1))

    with pytest.raises(ImageUploadError, match=expected_message):
        validate_company_image(upload, maximum_size, image_name)
