"""
test_report_generator.py
========================
Unit tests for report_generator.py.
Verifies the CSV report generation, content accuracy, empty list handling,
and adherence to data privacy (no raw resume text or unnecessary personal data).
"""

import csv
import io
import pytest

from report_generator import generate_csv_report


def test_generate_csv_report_correct_values():
    """Verify that generate_csv_report accurately populates all metrics from real match data."""
    sample_match_data = {
        "success": True,
        "match_percentage": 75.0,
        "matched_skills": ["Python", "AWS", "Docker"],
        "missing_skills": ["Kubernetes"],
        "extra_skills": ["SQL", "Excel"],
        "target_count": 4,
        "matched_count": 3,
        "suggestions": [
            "Add coursework for Kubernetes.",
            "Quantify project outcomes with numbers.",
        ],
    }

    csv_content = generate_csv_report(
        sample_match_data,
        candidate_name="Alex Smith",
        role_name="Cloud Engineer",
    )

    # 1. Must be valid UTF-8 string
    assert isinstance(csv_content, str)
    csv_bytes = csv_content.encode("utf-8")
    assert csv_bytes.decode("utf-8") == csv_content

    # 2. Parse using Python's standard csv.reader
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)
    row_dict = {row[0]: row[1] for row in rows if len(row) == 2}

    # 3. Verify all required metrics
    assert row_dict["Target Position"] == "Cloud Engineer"
    assert row_dict["Candidate Identifier"] == "Alex Smith"
    assert row_dict["Skill Coverage Percentage"] == "75.0%"
    assert row_dict["Total Required Skills"] == "4"
    assert "Python; AWS; Docker" in row_dict["Matched Skills"]
    assert "Kubernetes" in row_dict["Missing Skills"]
    assert "SQL; Excel" in row_dict["Additional Resume Skills"]
    assert "Kubernetes" in row_dict["Improvement Suggestions"]

    # 4. Must not contain raw resume text
    assert "SUMMARY" not in csv_content
    assert "EXPERIENCE" not in csv_content


def test_generate_csv_report_empty_lists():
    """Verify that empty lists are handled safely with clean default labels."""
    empty_match_data = {
        "success": True,
        "match_percentage": 0.0,
        "matched_skills": [],
        "missing_skills": [],
        "extra_skills": [],
        "target_count": 0,
        "matched_count": 0,
        "suggestions": [],
    }

    csv_content = generate_csv_report(empty_match_data)

    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)
    row_dict = {row[0]: row[1] for row in rows if len(row) == 2}

    assert row_dict["Skill Coverage Percentage"] == "0.0%"
    assert row_dict["Total Required Skills"] == "0"
    assert row_dict["Matched Skills"] == "None detected"
    assert row_dict["Missing Skills"] == "None missing"
    assert row_dict["Additional Resume Skills"] == "None detected"
    assert row_dict["Improvement Suggestions"] == "None"


def test_generate_csv_report_dynamic_scores():
    """Verify that the report uses dynamic analysis results without hardcoded scores."""
    custom_score_data = {
        "match_percentage": 42.9,
        "matched_skills": ["Git", "Linux", "Bash"],
        "missing_skills": ["Ansible", "Terraform", "CI/CD", "AWS"],
        "extra_skills": ["PHP"],
        "target_count": 7,
        "suggestions": ["Learn Ansible and Terraform."],
    }

    csv_content = generate_csv_report(custom_score_data)

    assert "42.9%" in csv_content
    assert "7" in csv_content
    assert "Git; Linux; Bash" in csv_content
    assert "Ansible; Terraform; CI/CD; AWS" in csv_content
