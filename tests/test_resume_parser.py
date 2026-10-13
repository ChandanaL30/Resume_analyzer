"""
test_resume_parser.py
=====================
Comprehensive automated unit tests for resume_parser.py using synthetic in-memory PDFs.
Tests text extraction, file validation, security, error handling, and edge cases.
"""

import io
import pytest

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from resume_parser import (
    clean_text,
    extract_candidate_info,
    extract_text_from_pdf,
    parse_resume_pdf,
    ParseResult,
)


# Helper class to simulate Streamlit's UploadedFile object in memory
class MockUploadedFile(io.BytesIO):
    def __init__(self, buffer: bytes, name: str = "resume.pdf"):
        super().__init__(buffer)
        self.name = name
        self.size = len(buffer)


# ---------------------------------------------------------------------------
# Synthetic PDF Generators (Created 100% in memory)
# ---------------------------------------------------------------------------

def create_synthetic_text_pdf(text_pages: list, title: str = "Resume") -> bytes:
    """Creates a multi-page text PDF in memory."""
    doc = fitz.open()
    for page_text in text_pages:
        page = doc.new_page()
        page.insert_text((50, 72), page_text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_synthetic_empty_page_pdf() -> bytes:
    """Creates a PDF with a blank page containing zero text or images."""
    doc = fitz.open()
    doc.new_page()  # Blank page
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_synthetic_encrypted_pdf(password: str = "secret123") -> bytes:
    """Creates a password-protected PDF in memory."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Confidential Resume - Secret Candidate")
    # Save with AES encryption
    pdf_bytes = doc.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw=password,
        owner_pw=password + "_owner",
    )
    doc.close()
    return pdf_bytes


def create_synthetic_scanned_image_pdf() -> bytes:
    """Creates a PDF with an image and no selectable text, simulating a scanned resume."""
    doc = fitz.open()
    page = doc.new_page()

    # Create a 60x60 synthetic image pixmap
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 60, 60), 0)
    pixmap.clear_with(200)  # Light gray image
    page.insert_image(page.rect, pixmap=pixmap)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_extract_from_valid_single_page_pdf():
    """Verify that text is correctly extracted from a valid synthetic single-page PDF."""
    content = "Jane Doe\njane.doe@example.com\nAWS Cloud Engineer with Python and Docker skills."
    pdf_bytes = create_synthetic_text_pdf([content])

    text, error = extract_text_from_pdf(pdf_bytes)

    assert error is None
    assert "Jane Doe" in text
    assert "jane.doe@example.com" in text
    assert "AWS Cloud Engineer" in text


def test_extract_from_multi_page_pdf():
    """Verify that multi-page resumes extract and concatenate text across all pages."""
    page_1 = "Candidate Profile\nPage 1 Content\nPython, Docker"
    page_2 = "Work History\nPage 2 Content\nKubernetes, AWS Cloud"
    pdf_bytes = create_synthetic_text_pdf([page_1, page_2])

    result = parse_resume_pdf(pdf_bytes)

    assert result.success is True
    assert result.page_count == 2
    assert "Page 1 Content" in result.text
    assert "Page 2 Content" in result.text
    assert result.error is None


def test_streamlit_uploaded_file_simulation():
    """Verify compatibility with Streamlit's UploadedFile object."""
    content = "Michael Scott\nmichael@dundermifflin.com\nManagement, Scrum"
    pdf_bytes = create_synthetic_text_pdf([content])
    mock_file = MockUploadedFile(pdf_bytes, name="michael_resume.pdf")

    text, error = extract_text_from_pdf(mock_file)

    assert error is None
    assert "Michael Scott" in text
    assert "michael@dundermifflin.com" in text
    # Verify stream was rewound
    assert mock_file.tell() == 0


def test_corrupted_pdf_handling():
    """Verify that invalid/corrupt bytes return a clean error without raising uncaught exceptions."""
    corrupted_bytes = b"%PDF-1.4\nCorrupted content completely invalid non-pdf binary %%%"

    text, error = extract_text_from_pdf(corrupted_bytes)

    assert text == ""
    assert error is not None
    assert "corrupted" in error.lower() or "not a valid pdf" in error.lower()


def test_invalid_header_rejection():
    """Verify that non-PDF files (e.g. plain text or executable headers) are rejected."""
    fake_doc = b"Plain text file content pretending to be a document. This is definitely not a valid PDF file format."
    text, error = extract_text_from_pdf(fake_doc)

    assert text == ""
    assert "invalid file" in error.lower() or "header" in error.lower()


def test_empty_bytes_handling():
    """Verify that an empty 0-byte file returns a clean error."""
    text, error = extract_text_from_pdf(b"")

    assert text == ""
    assert "empty" in error.lower()


def test_password_protected_pdf():
    """Verify that password-protected PDFs return an informative password error."""
    encrypted_pdf_bytes = create_synthetic_encrypted_pdf(password="secret_pass_123")

    result = parse_resume_pdf(encrypted_pdf_bytes)

    assert result.success is False
    assert result.text == ""
    assert "password-protected" in result.error.lower()


def test_scanned_image_only_pdf_informs_ocr_unsupported():
    """Verify that image-only/scanned resumes inform the user that OCR is not supported."""
    scanned_bytes = create_synthetic_scanned_image_pdf()

    result = parse_resume_pdf(scanned_bytes)

    assert result.success is False
    assert result.text == ""
    assert result.is_scanned is True
    assert "ocr" in result.error.lower()
    assert "not supported" in result.error.lower()


def test_blank_page_pdf_error():
    """Verify that a PDF with blank pages returns an appropriate error."""
    blank_pdf = create_synthetic_empty_page_pdf()

    result = parse_resume_pdf(blank_pdf)

    assert result.success is False
    assert result.text == ""
    assert "no readable text" in result.error.lower()


def test_file_size_limit_validation():
    """Verify that files exceeding the maximum size limit are rejected."""
    # Test with a 1 MB limit threshold
    dummy_large_bytes = b"%PDF-1.4\n" + b"A" * (2 * 1024 * 1024)  # 2 MB

    result = parse_resume_pdf(dummy_large_bytes, max_size_mb=1)

    assert result.success is False
    assert "exceeds" in result.error.lower()


def test_invalid_filename_extension():
    """Verify that files with non-pdf extensions are rejected."""
    mock_txt_file = MockUploadedFile(b"%PDF-1.4\nContent", name="resume.docx")

    text, error = extract_text_from_pdf(mock_txt_file)

    assert text == ""
    assert "invalid file format" in error.lower()


def test_clean_text_normalization():
    """Verify that text cleaning removes binary control chars and redundant whitespace."""
    dirty_text = "Jane Doe\r\n\r\n\t  Python  Engineer \x00\x05 \n\nAWS Cloud"
    cleaned = clean_text(dirty_text)

    assert "Jane Doe" in cleaned
    assert "Python Engineer" in cleaned
    assert "AWS Cloud" in cleaned
    assert "\r" not in cleaned
    assert "\x00" not in cleaned


def test_extract_candidate_info():
    """Verify extraction of contact information from resume text."""
    sample = """
    Sarah Connor
    sarah.connor@example.org
    (555) 123-4567
    Los Angeles, CA

    Professional Summary
    Senior DevOps engineer with experience in AWS, Kubernetes, and CI/CD pipelines.
    """
    info = extract_candidate_info(sample)

    assert info["name"] == "Sarah Connor"
    assert info["email"] == "sarah.connor@example.org"
    assert "555" in info["phone"]
    assert info["word_count"] > 10
    assert info["character_count"] > 50
