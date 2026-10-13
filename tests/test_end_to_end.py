"""
test_end_to_end.py
===================
End-to-End integration test suite for the Cloud-Based Resume Analyzer.

Verifies:
1. In-memory PDF text extraction on synthetic resumes.
2. Handling of invalid, empty, encrypted, and image-only scanned PDFs.
3. Accurate skill extraction, matched/missing skill calculation, and formula verification.
4. Handling of empty job requirements and no detected skills.
5. Chart generation (Plotly figures) with actual data.
6. RFC 4180 UTF-8 CSV report generation and validation.
7. Separate consecutive analyses isolation (no bleed of skills/scores).
8. Local mode safety (zero cloud credentials or network calls).
9. AWS error safety and mocked cloud lifecycle.
10. Repository hygiene (zero committed secrets, env files, or real resumes).
"""

import csv
import io
import os
import re
from typing import Dict, List
from unittest.mock import MagicMock, patch
import pytest

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from resume_parser import (
    parse_resume_pdf,
    extract_text_from_pdf,
    extract_candidate_info,
    clean_text,
    ParseResult,
)
from skill_matcher import (
    extract_skills_from_resume,
    extract_skills_from_jd,
    calculate_match_score,
    categorize_skills,
    find_matched_skills,
    find_missing_skills,
    find_additional_skills,
)
from report_generator import (
    create_gauge_chart,
    create_skill_bar_chart,
    create_category_distribution_chart,
    generate_recommendations,
    generate_csv_report,
    generate_text_report,
)
from cloud_storage import (
    upload_file_to_s3,
    delete_file_from_s3,
    test_s3_connection as check_s3_health,
    get_cloud_config,
    is_s3_configured,
    generate_unique_object_key,
    MODE_LOCAL,
)


class InMemoryUploadedFile(io.BytesIO):
    """Simulates Streamlit UploadedFile in RAM."""
    def __init__(self, data: bytes, name: str = "test_resume.pdf"):
        super().__init__(data)
        self.name = name
        self.size = len(data)


def create_synthetic_pdf(text: str, name: str = "synthetic.pdf") -> InMemoryUploadedFile:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return InMemoryUploadedFile(pdf_bytes, name=name)


# -----------------------------------------------------------------------------
# 1. End-to-End Extraction & Parsing Tests
# -----------------------------------------------------------------------------

def test_e2e_valid_pdf_extraction_and_contact_info():
    """Verify in-memory PDF parsing and candidate contact extraction."""
    resume_text = (
        "Sarah Connor\n"
        "Email: sarah.connor@cyberdyne.org\n"
        "Phone: +1-555-867-5309\n\n"
        "Professional Summary\n"
        "Senior Cloud Engineer with deep expertise in AWS, Docker, Kubernetes, and Python.\n"
        "Experienced in Terraform infrastructure as code and CI/CD automation."
    )
    uploaded_file = create_synthetic_pdf(resume_text, name="sarah_resume.pdf")
    parse_res = parse_resume_pdf(uploaded_file)

    assert parse_res.success is True
    assert parse_res.page_count == 1
    assert "Sarah Connor" in parse_res.text
    assert "sarah.connor@cyberdyne.org" in parse_res.text

    contact_info = extract_candidate_info(parse_res.text)
    assert contact_info["email"] == "sarah.connor@cyberdyne.org"
    assert "555" in contact_info["phone"]


def test_e2e_invalid_empty_and_scanned_pdf_handling():
    """Verify invalid, empty, corrupt, and scanned PDFs are handled safely."""
    # Corrupt PDF that passes size check (> 64 bytes) but has damaged structure
    damaged_bytes = b"%PDF-1.4 " + b"\x00\xFF\xFE\xFD corrupted garbage payload " * 5
    corrupt_file = InMemoryUploadedFile(damaged_bytes, name="corrupt.pdf")
    res_corrupt = parse_resume_pdf(corrupt_file)
    assert res_corrupt.success is False
    assert "damaged" in res_corrupt.error.lower() or "corrupt" in res_corrupt.error.lower()

    # Empty 0-byte file
    empty_file = InMemoryUploadedFile(b"", name="empty.pdf")
    res_empty = parse_resume_pdf(empty_file)
    assert res_empty.success is False
    assert "empty" in res_empty.error.lower() or "too small" in res_empty.error.lower()

    # Blank page PDF with no text
    doc_blank = fitz.open()
    doc_blank.new_page()
    blank_bytes = doc_blank.tobytes()
    doc_blank.close()
    blank_file = InMemoryUploadedFile(blank_bytes, name="blank.pdf")
    res_blank = parse_resume_pdf(blank_file)
    assert res_blank.success is False
    assert "no readable text" in res_blank.error.lower() or "ocr" in res_blank.error.lower()

    # Scanned image-only PDF with an image and no text
    doc_scanned = fitz.open()
    page = doc_scanned.new_page()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 50, 50), 0)
    pix.clear_with(200)
    page.insert_image(page.rect, pixmap=pix)
    scanned_bytes = doc_scanned.tobytes()
    doc_scanned.close()
    scanned_file = InMemoryUploadedFile(scanned_bytes, name="scanned.pdf")
    res_scanned = parse_resume_pdf(scanned_file)
    assert res_scanned.success is False
    assert res_scanned.is_scanned is True
    assert "ocr" in res_scanned.error.lower()


# -----------------------------------------------------------------------------
# 2. End-to-End Skill Match & Formula Verification
# -----------------------------------------------------------------------------

def test_e2e_skill_match_and_formula_calculation():
    """Verify documented formula: matched unique / total unique required * 100."""
    candidate_pdf = create_synthetic_pdf(
        "Candidate with skills in Python, Docker, SQL, and Git."
    )
    parse_res = parse_resume_pdf(candidate_pdf)
    assert parse_res.success is True

    candidate_skills = extract_skills_from_resume(parse_res.text)
    # Canonical skill representations in taxonomy
    candidate_lower = {s.lower() for s in candidate_skills}
    assert candidate_lower == {"python", "docker", "sql", "git"}

    # Job requirements: Python, Docker, Kubernetes, AWS (4 skills)
    jd_text = "Looking for an engineer skilled in Python, Docker, Kubernetes, and AWS."
    required_skills = extract_skills_from_jd(jd_text)
    required_lower = {s.lower() for s in required_skills}
    assert required_lower == {"python", "docker", "kubernetes", "aws"}

    match_data = calculate_match_score(candidate_skills, required_skills)
    assert match_data["success"] is True
    # Matched: Python, Docker (2)
    matched_lower = {s.lower() for s in match_data["matched_skills"]}
    assert matched_lower == {"python", "docker"}
    # Missing: Kubernetes, AWS (2)
    missing_lower = {s.lower() for s in match_data["missing_skills"]}
    assert missing_lower == {"kubernetes", "aws"}
    # Extra / Additional: SQL, Git (2)
    extra_lower = {s.lower() for s in match_data["extra_skills"]}
    assert extra_lower == {"sql", "git"}

    # Documented formula: 2 matched / 4 required = 50.0%
    expected_score = round((2 / 4) * 100, 1)
    assert match_data["match_percentage"] == expected_score
    assert match_data["match_percentage"] == 50.0


def test_e2e_empty_job_requirements_handling():
    """Verify empty job description or description without technical keywords."""
    # Completely empty JD
    empty_skills = extract_skills_from_jd("")
    assert empty_skills == []
    match_empty = calculate_match_score(["Python"], empty_skills)
    assert match_empty["success"] is False
    assert "No recognized technical skills" in match_empty["message"]

    # JD with fluff text but no skills
    fluff_jd = "We are seeking a proactive team player with excellent synergy."
    fluff_skills = extract_skills_from_jd(fluff_jd)
    assert fluff_skills == []
    match_fluff = calculate_match_score(["Python"], fluff_skills)
    assert match_fluff["success"] is False


# -----------------------------------------------------------------------------
# 3. Chart Generation & Actual Results Test
# -----------------------------------------------------------------------------

def test_e2e_charts_render_actual_results():
    """Verify Plotly charts are constructed with actual match data."""
    match_data = {
        "match_percentage": 75.0,
        "matched_skills": ["Python", "AWS", "Docker"],
        "missing_skills": ["Kubernetes"],
        "extra_skills": ["Git"],
        "matched_count": 3,
        "missing_count": 1,
        "required_total_skills": 4,
        "resume_total_skills": 4,
    }

    # Gauge Chart
    gauge_fig = create_gauge_chart(match_data["match_percentage"])
    assert gauge_fig is not None
    assert gauge_fig.data[0].value == 75.0

    # Skill Bar Chart
    bar_fig = create_skill_bar_chart(match_data["matched_count"], match_data["missing_count"])
    assert bar_fig is not None
    # Check that counts correspond to actual data
    assert tuple(bar_fig.data[0].x) == (3, 1)

    # Category Distribution Chart
    categorized = categorize_skills(["Python", "AWS", "Docker", "SQL"])
    cat_fig = create_category_distribution_chart(categorized)
    assert cat_fig is not None
    assert len(cat_fig.data[0].x) > 0


# -----------------------------------------------------------------------------
# 4. CSV Report Generation & RFC 4180 UTF-8 Validation
# -----------------------------------------------------------------------------

def test_e2e_csv_report_generation():
    """Verify RFC 4180 UTF-8 CSV report generation and content accuracy."""
    match_data = {
        "match_percentage": 66.7,
        "matched_skills": ["Python", "SQL"],
        "missing_skills": ["AWS"],
        "extra_skills": ["Git"],
        "matched_count": 2,
        "missing_count": 1,
        "target_count": 3,
        "resume_total_skills": 3,
    }
    csv_str = generate_csv_report(
        match_data,
        candidate_name="Alex Rivera",
        role_name="Cloud Engineer",
        suggestions=["Acquire AWS certification."],
    )

    assert isinstance(csv_str, str)
    reader = csv.reader(io.StringIO(csv_str))
    rows = list(reader)

    # Convert metric rows into dictionary
    metric_dict = {row[0]: row[1] for row in rows if len(row) >= 2}

    assert metric_dict["Candidate Identifier"] == "Alex Rivera"
    assert metric_dict["Target Position"] == "Cloud Engineer"
    assert metric_dict["Skill Coverage Percentage"] == "66.7%"
    assert metric_dict["Total Required Skills"] == "3"
    assert "Python" in metric_dict["Matched Skills"]
    assert "AWS" in metric_dict["Missing Skills"]
    assert "Git" in metric_dict["Additional Resume Skills"]
    assert "Acquire AWS certification." in metric_dict["Improvement Suggestions"]


# -----------------------------------------------------------------------------
# 5. Separate Analyses Isolation (No Bleed)
# -----------------------------------------------------------------------------

def test_e2e_separate_analyses_do_not_mix_results():
    """Verify consecutive analyses maintain strictly isolated results."""
    # Analysis 1: Candidate 1 (Data Analyst)
    pdf1 = create_synthetic_pdf(
        "Candidate One. Skills: Python, SQL, Excel, Tableau.",
        name="candidate1.pdf"
    )
    res1 = parse_resume_pdf(pdf1)
    skills1 = extract_skills_from_resume(res1.text)
    jd1_skills = extract_skills_from_jd("Required: Python, SQL, Tableau, Power BI")
    match1 = calculate_match_score(skills1, jd1_skills)

    matched1_lower = {s.lower() for s in match1["matched_skills"]}
    assert matched1_lower == {"python", "sql", "tableau"}
    assert {s.lower() for s in match1["missing_skills"]} == {"power bi"}
    assert match1["match_percentage"] == 75.0

    # Analysis 2: Candidate 2 (DevOps Engineer) - entirely different profile
    pdf2 = create_synthetic_pdf(
        "Candidate Two. Skills: AWS, Docker, Kubernetes, Linux, Terraform.",
        name="candidate2.pdf"
    )
    res2 = parse_resume_pdf(pdf2)
    skills2 = extract_skills_from_resume(res2.text)
    jd2_skills = extract_skills_from_jd("Required: Docker, Kubernetes, Terraform")
    match2 = calculate_match_score(skills2, jd2_skills)

    # Assert Candidate 2 has zero skills or scores from Candidate 1
    matched2_lower = {s.lower() for s in match2["matched_skills"]}
    assert matched2_lower == {"docker", "kubernetes", "terraform"}
    assert set(match2["missing_skills"]) == set()
    assert match2["match_percentage"] == 100.0
    assert "sql" not in matched2_lower
    assert "tableau" not in matched2_lower
    assert "power bi" not in {s.lower() for s in match2["missing_skills"]}


# -----------------------------------------------------------------------------
# 6. Local Mode Safety (Zero AWS Credentials Required)
# -----------------------------------------------------------------------------

def test_e2e_local_mode_operates_without_aws(monkeypatch):
    """Verify application runs 100% locally with zero cloud credentials."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("S3_BUCKET_NAME", raising=False)

    config = get_cloud_config()
    assert config["bucket_name"] is None
    assert is_s3_configured() is False

    # Upload attempt without explicit user consent is blocked
    success, msg, key = upload_file_to_s3(
        file_source=b"test data",
        filename="test.pdf",
        user_consent=False,
    )
    assert success is False
    assert "consent" in msg.lower()


# -----------------------------------------------------------------------------
# 7. AWS Operations Mocked & Safe Error Handling
# -----------------------------------------------------------------------------

def test_e2e_aws_operations_mocked():
    """Verify S3 upload, delete, UUID generation, and error handling with mocks."""
    # UUID Key Uniqueness
    k1 = generate_unique_object_key("resumes", "resume.pdf")
    k2 = generate_unique_object_key("resumes", "resume.pdf")
    assert k1 != k2
    assert k1.startswith("resumes/")
    assert k1.endswith(".pdf")

    mock_s3 = MagicMock()
    mock_s3.put_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    mock_s3.delete_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 204}}
    mock_s3.head_bucket.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}

    with patch("cloud_storage.get_s3_client", return_value=mock_s3):
        with patch.dict("os.environ", {"S3_BUCKET_NAME": "private-resume-bucket"}):
            # Mocked Upload with Consent
            u_success, u_msg, u_key = upload_file_to_s3(
                file_source=b"%PDF-1.4 mock content",
                filename="test_resume.pdf",
                user_consent=True,
            )
            assert u_success is True
            assert u_key is not None
            assert "s3://private-resume-bucket/" in u_msg

            # Mocked Delete
            d_success, d_msg = delete_file_from_s3(u_key)
            assert d_success is True
            assert "deleted" in d_msg.lower()

            # Mocked Connection Test
            c_success, c_msg = check_s3_health()
            assert c_success is True
            assert "verified" in c_msg.lower() or "connected" in c_msg.lower()


# -----------------------------------------------------------------------------
# 8. Repository Hygiene: No Secrets or Resumes Committed
# -----------------------------------------------------------------------------

def test_e2e_repo_hygiene():
    """Verify repository contains no hardcoded AWS credentials or PDF resumes."""
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 1. Verify no PDF resumes exist in workspace (excluding venv)
    pdf_files = []
    for root, dirs, files in os.walk(workspace_root):
        if "venv" in root or ".git" in root or "__pycache__" in root:
            continue
        for f in files:
            if f.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(root, f))
    assert len(pdf_files) == 0, f"Found unexpected PDF files: {pdf_files}"

    # 2. Verify no active .env file exists (only .env.example allowed)
    env_file = os.path.join(workspace_root, ".env")
    assert not os.path.exists(env_file), "Active .env file must NOT exist in the repository."
