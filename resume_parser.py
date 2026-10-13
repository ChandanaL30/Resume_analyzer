"""
resume_parser.py
================
Module for securely parsing and extracting text from PDF resumes using PyMuPDF.

Features:
- Streamlit UploadedFile and in-memory byte buffer support.
- Zero disk persistence (processes purely in RAM for privacy).
- File type and file size validation.
- Robust handling of empty, corrupt, password-protected, and scanned/image-only PDFs.
- Explicit notification if a PDF is scanned without OCR support (no hallucinated text).
- Zero private data logging.
"""

import io
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Union

try:
    import pymupdf as fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    try:
        import fitz
        PYMUPDF_AVAILABLE = True
    except ImportError:
        PYMUPDF_AVAILABLE = False


# Maximum permissible resume file size (10 MB is standard for PDF resumes)
DEFAULT_MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = DEFAULT_MAX_FILE_SIZE_MB * 1024 * 1024

# Minimum acceptable PDF byte size
MIN_FILE_SIZE_BYTES = 64


@dataclass
class ParseResult:
    """
    Standardized result structure for parsed resumes.
    """
    success: bool
    text: str
    error: Optional[str] = None
    page_count: int = 0
    file_size_bytes: int = 0
    is_scanned: bool = False


def clean_text(text: Optional[str]) -> str:
    """
    Cleans raw extracted text by removing control characters, excessive whitespace,
    and orphan lines while preserving paragraph structures.

    Args:
        text (Optional[str]): Raw string extracted from document pages.

    Returns:
        str: Cleaned, normalized text.
    """
    if not text:
        return ""

    # Replace carriage returns and excessive tabs
    cleaned = re.sub(r"\r\n", "\n", text)
    cleaned = re.sub(r"[\r\t\v\f]", " ", cleaned)
    # Remove non-printable control characters (keeping standard newlines)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", cleaned)
    # Normalize multiple horizontal spaces
    cleaned = re.sub(r"[ ]{2,}", " ", cleaned)

    # Filter out empty or whitespace-only lines
    lines = [line.strip() for line in cleaned.splitlines()]
    meaningful_lines = [line for line in lines if line]

    return "\n".join(meaningful_lines)


def _validate_source(
    pdf_source: Union[str, bytes, io.BytesIO, Any],
    max_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB,
) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Validates file format, size limits, and reads bytes safely into memory.

    Returns:
        Tuple[Optional[bytes], Optional[str]]: (pdf_bytes, error_message)
    """
    max_bytes = max_size_mb * 1024 * 1024

    # 1. Check filename extension if available (e.g. Streamlit UploadedFile)
    filename = getattr(pdf_source, "name", None)
    if isinstance(filename, str) and not filename.lower().endswith(".pdf"):
        return None, "Invalid file format. Only PDF files (.pdf) are supported."

    # 2. Extract raw bytes from source
    pdf_bytes: Optional[bytes] = None

    if hasattr(pdf_source, "read"):
        try:
            pdf_bytes = pdf_source.read()
            # Rewind file pointer if supported so caller can reuse if needed
            if hasattr(pdf_source, "seek"):
                pdf_source.seek(0)
        except Exception as e:
            return None, f"Unable to read uploaded file: {str(e)}"
    elif isinstance(pdf_source, (bytes, bytearray)):
        pdf_bytes = bytes(pdf_source)
    elif isinstance(pdf_source, str):
        # Local file path
        if not pdf_source.lower().endswith(".pdf"):
            return None, "Invalid file path. File must end with .pdf."
        try:
            with open(pdf_source, "rb") as f:
                pdf_bytes = f.read()
        except FileNotFoundError:
            return None, f"File not found: {pdf_source}"
        except Exception as e:
            return None, f"Could not open file: {str(e)}"
    else:
        return None, "Unsupported file input format. Please provide a PDF file."

    # 3. Size validation
    if not pdf_bytes or len(pdf_bytes) == 0:
        return None, "The uploaded PDF file is empty (0 bytes)."

    file_size = len(pdf_bytes)
    if file_size > max_bytes:
        size_mb = file_size / (1024 * 1024)
        return (
            None,
            f"File size exceeds the {max_size_mb} MB limit (current size: {size_mb:.1f} MB). Please upload a smaller PDF.",
        )

    if file_size < MIN_FILE_SIZE_BYTES:
        return None, "The uploaded file is too small to be a valid PDF document."

    # 4. PDF Magic Header check (%PDF-)
    if not (pdf_bytes.startswith(b"%PDF-") or b"%PDF-" in pdf_bytes[:1024]):
        return None, "Invalid file format. The file header does not match a standard PDF document."

    return pdf_bytes, None


def parse_resume_pdf(
    pdf_source: Union[str, bytes, io.BytesIO, Any],
    max_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB,
) -> ParseResult:
    """
    Parses an in-memory PDF resume using PyMuPDF.

    Performs comprehensive validation for:
    - File size and type
    - Password protection
    - Corrupt or malformed structure
    - Empty pages
    - Image-only / scanned documents (reports OCR unsupported)

    Args:
        pdf_source: File path, bytes, or Streamlit UploadedFile object.
        max_size_mb (int): Maximum allowable file size in megabytes.

    Returns:
        ParseResult: Dataclass containing success status, cleaned text, error message,
                     and metadata.
    """
    if not PYMUPDF_AVAILABLE:
        return ParseResult(
            success=False,
            text="",
            error="PyMuPDF library is not installed. Please install it using 'pip install PyMuPDF'.",
        )

    # Validate file type, size, and magic header
    pdf_bytes, validation_error = _validate_source(pdf_source, max_size_mb=max_size_mb)
    if validation_error:
        return ParseResult(success=False, text="", error=validation_error)

    file_size = len(pdf_bytes)
    doc = None

    try:
        # Open strictly from in-memory byte buffer (no disk file created)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        # Check for password encryption
        if getattr(doc, "is_encrypted", False):
            # Try authenticating with an empty password (some PDFs allow this)
            if not doc.authenticate(""):
                return ParseResult(
                    success=False,
                    text="",
                    error="This PDF is password-protected. Please remove the password and upload an unlocked resume.",
                    file_size_bytes=file_size,
                )

        page_count = len(doc)
        if page_count == 0:
            return ParseResult(
                success=False,
                text="",
                error="The uploaded PDF contains no pages.",
                file_size_bytes=file_size,
            )

        extracted_text_chunks = []
        has_embedded_images = False

        # Extract text page by page
        for page_idx in range(page_count):
            page = doc[page_idx]

            # Track if page has images
            if len(page.get_images()) > 0:
                has_embedded_images = True

            page_text = page.get_text("text")
            if page_text and page_text.strip():
                extracted_text_chunks.append(page_text.strip())

        raw_combined = "\n\n".join(extracted_text_chunks)
        cleaned_text = clean_text(raw_combined)

        # Check if no text was extracted
        if not cleaned_text:
            if has_embedded_images:
                return ParseResult(
                    success=False,
                    text="",
                    error=(
                        "Scanned document detected. This PDF contains only images with no extractable text. "
                        "OCR (Optical Character Recognition) is not supported; please upload a text-based PDF."
                    ),
                    page_count=page_count,
                    file_size_bytes=file_size,
                    is_scanned=True,
                )
            else:
                return ParseResult(
                    success=False,
                    text="",
                    error="The uploaded PDF has no readable text. Please upload a standard text-based PDF.",
                    page_count=page_count,
                    file_size_bytes=file_size,
                )

        return ParseResult(
            success=True,
            text=cleaned_text,
            error=None,
            page_count=page_count,
            file_size_bytes=file_size,
            is_scanned=False,
        )

    except fitz.FileDataError:
        return ParseResult(
            success=False,
            text="",
            error="The uploaded file appears to be corrupted or is not a valid PDF document.",
            file_size_bytes=file_size,
        )
    except Exception as e:
        return ParseResult(
            success=False,
            text="",
            error=f"Error reading PDF: {str(e)}",
            file_size_bytes=file_size,
        )
    finally:
        if doc is not None:
            doc.close()


def extract_text_from_pdf(
    pdf_source: Union[str, bytes, io.BytesIO, Any],
    max_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB,
) -> Tuple[str, Optional[str]]:
    """
    Standard interface used by Streamlit app.py and tests.
    Extracts plain text in memory without disk persistence.

    Args:
        pdf_source: File path, bytes, or Streamlit UploadedFile object.
        max_size_mb (int): Maximum file size limit in MB.

    Returns:
        Tuple[str, Optional[str]]: (extracted_text, error_message).
                                   If successful, error_message is None.
    """
    result = parse_resume_pdf(pdf_source, max_size_mb=max_size_mb)
    return result.text, result.error


def extract_candidate_info(text: str) -> Dict[str, Union[str, int]]:
    """
    Extracts candidate contact details and document statistics from resume text.
    Does not log or store private data.

    Args:
        text (str): Extracted resume text.

    Returns:
        Dict: Extracted candidate profile metrics (email, phone, name, word count).
    """
    info = {
        "name": "Candidate",
        "email": "Not detected",
        "phone": "Not detected",
        "word_count": 0,
        "character_count": 0,
    }

    if not text:
        return info

    words = text.split()
    info["word_count"] = len(words)
    info["character_count"] = len(text)

    # 1. Email extraction via regex
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"
    email_match = re.search(email_pattern, text)
    if email_match:
        info["email"] = email_match.group(0)

    # 2. Phone number extraction (handles international and local formats)
    phone_pattern = r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
    phone_match = re.search(phone_pattern, text)
    if phone_match:
        info["phone"] = phone_match.group(0).strip()

    # 3. Candidate name heuristic:
    # First 5 non-empty lines, looking for 2-4 capitalized words, excluding common headers
    ignored_keywords = {
        "resume", "curriculum", "vitae", "cv", "profile", "contact",
        "education", "experience", "skills", "summary", "objective",
        "projects", "certifications", "work", "email", "phone"
    }

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[:5]:
        lower_line = line.lower()
        if any(keyword in lower_line for keyword in ignored_keywords):
            continue
        if "@" in line or any(char.isdigit() for char in line):
            continue
        line_words = line.split()
        if 2 <= len(line_words) <= 4 and len(line) <= 45:
            info["name"] = line
            break

    return info
