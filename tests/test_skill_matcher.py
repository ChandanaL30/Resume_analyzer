"""
test_skill_matcher.py
====================
Unit tests for the skill_matcher module.
Tests extraction of required skills, case-insensitive matching, false positive prevention,
skill coverage calculation, handling of empty job descriptions, and suggestions disclaimer.
"""

import pytest
from skill_matcher import (
    extract_skills_from_text,
    extract_skills_from_resume,
    extract_skills_from_jd,
    find_matched_skills,
    find_missing_skills,
    find_additional_skills,
    calculate_skill_coverage,
    generate_skill_suggestions,
    calculate_match_score,
    categorize_skills,
    get_available_roles,
    get_skills_for_role,
)


def test_extract_common_skills_all_required_categories():
    """
    Verify extraction of all common skill keywords specified:
    - Python, Java, C++, SQL and MySQL
    - Excel, Power BI, Tableau and data visualization
    - Pandas, NumPy, statistics and data analysis
    - Machine learning, deep learning, NLP and generative AI
    - AWS, Azure, Docker and Git
    """
    sample_text = """
    Proficient in Python, Java, C++, SQL, and MySQL databases.
    Experienced in Excel spreadsheets, Power BI, Tableau dashboards, and data visualization.
    Strong skills in Pandas, NumPy, statistics, and business data analysis.
    Hands-on experience building machine learning, deep learning, NLP, and generative AI systems.
    Proficient in cloud deployment using AWS, Azure, Docker containers, and Git version control.
    """
    skills = extract_skills_from_resume(sample_text)

    # Programming & Databases
    assert "Python" in skills
    assert "Java" in skills
    assert "C++" in skills
    assert "SQL" in skills
    assert "MySQL" in skills

    # Data & Visualization
    assert "Excel" in skills
    assert "Power BI" in skills
    assert "Tableau" in skills
    assert "Data Visualization" in skills

    # Analysis & Libraries
    assert "Pandas" in skills
    assert "NumPy" in skills
    assert "Statistics" in skills
    assert "Data Analysis" in skills

    # AI & ML
    assert "Machine Learning" in skills
    assert "Deep Learning" in skills
    assert "NLP" in skills
    assert "Generative AI" in skills

    # Cloud & DevOps
    assert "AWS" in skills
    assert "Azure" in skills
    assert "Docker" in skills
    assert "Git" in skills


def test_extract_skills_from_jd():
    """Verify that extract_skills_from_jd correctly parses job description text."""
    jd_text = "We are seeking a Data Scientist with strong Python, SQL, Machine Learning, and AWS skills."
    jd_skills = extract_skills_from_jd(jd_text)

    assert set(jd_skills) == {"Python", "SQL", "Machine Learning", "AWS"}


def test_find_matched_skills_case_insensitive():
    """Verify finding matching skills regardless of letter casing in resume or JD."""
    resume_skills = ["python", "AWS", "docker", "tableau"]
    required_skills = ["Python", "aws", "Docker", "Java"]

    matched = find_matched_skills(resume_skills, required_skills)
    assert set(matched) == {"Python", "AWS", "Docker"}
    assert "Java" not in matched


def test_find_missing_skills():
    """Verify identifying missing skills required by the job."""
    resume_skills = ["Python", "SQL"]
    required_skills = ["Python", "SQL", "Docker", "Kubernetes", "AWS"]

    missing = find_missing_skills(resume_skills, required_skills)
    assert set(missing) == {"Docker", "Kubernetes", "AWS"}


def test_find_additional_skills():
    """Verify identifying skills present in the resume but not required by the job."""
    resume_skills = ["Python", "SQL", "C++", "Excel"]
    required_skills = ["Python", "SQL"]

    extra = find_additional_skills(resume_skills, required_skills)
    assert set(extra) == {"C++", "Excel"}


def test_calculate_skill_coverage_full_match():
    """Verify 100% coverage when all required skills are present."""
    matched = ["Python", "SQL", "Docker"]
    required = ["Python", "SQL", "Docker"]

    coverage = calculate_skill_coverage(matched, required)
    assert coverage == 100.0


def test_calculate_skill_coverage_partial_match():
    """Verify formula: (matched unique / total unique required) * 100."""
    matched = ["Python", "SQL"]  # 2 matched
    required = ["Python", "SQL", "Docker", "Kubernetes"]  # 4 required

    coverage = calculate_skill_coverage(matched, required)
    # 2 / 4 * 100 = 50.0%
    assert coverage == 50.0


def test_calculate_skill_coverage_zero_match():
    """Verify 0.0% coverage when zero skills match."""
    matched = []
    required = ["Docker", "Kubernetes"]

    coverage = calculate_skill_coverage(matched, required)
    assert coverage == 0.0


def test_empty_job_requirements_handling():
    """
    Verify that an empty job description or a JD with no recognized skills
    returns success: False and an informative request for a more detailed description,
    rather than displaying a misleading 0% or 100% score.
    """
    resume_skills = ["Python", "SQL", "AWS"]
    empty_jd_skills = []

    result = calculate_match_score(resume_skills, empty_jd_skills)

    assert result["success"] is False
    assert result["target_count"] == 0
    assert result["message"] is not None
    assert "detailed job description" in result["message"].lower()


def test_false_positive_prevention_substrings():
    """
    Verify that short terms do NOT trigger false positives inside unrelated words:
    - 'excel' in 'excellent' or 'excellence'
    - 'git' in 'digital', 'vital', 'legitimate'
    - 'aws' in 'awareness', 'flaws'
    - 'sql' in 'squalor', 'mosque'
    - 'java' in 'javascript'
    - 'c++' in 'classic'
    """
    unrelated_text = """
    She demonstrated excellent communication and digital marketing leadership.
    Maintained security awareness across team initiatives and resolved squalor in legacy processes.
    Enjoys classic literature and writing clean javascript applications.
    """
    detected_skills = extract_skills_from_resume(unrelated_text)

    assert "Excel" not in detected_skills
    assert "Git" not in detected_skills
    assert "AWS" not in detected_skills
    assert "SQL" not in detected_skills
    assert "Java" not in detected_skills  # 'javascript' should detect JavaScript, not Java
    assert "C++" not in detected_skills


def test_generate_skill_suggestions_disclaimer():
    """
    Verify suggestions and ensure they do NOT claim that keyword matching proves
    a candidate's ability or predicts hiring outcomes.
    """
    missing = ["Docker", "Kubernetes"]
    suggestions = generate_skill_suggestions(missing)

    assert len(suggestions) > 0
    # Must include actionable suggestion for missing skills
    assert any("docker" in s.lower() or "kubernetes" in s.lower() for s in suggestions)

    # Must contain disclaimer regarding candidate ability and hiring outcomes
    disclaimer = next(s for s in suggestions if "disclaimer" in s.lower())
    assert "does not evaluate" in disclaimer.lower() or "competence" in disclaimer.lower()
    assert "hiring" in disclaimer.lower()


def test_categorize_skills():
    """Verify that detected skills are categorized properly into domains."""
    skills = ["Python", "AWS", "Docker", "Power BI", "Machine Learning"]
    categories = categorize_skills(skills)

    assert "Programming Languages" in categories
    assert "Python" in categories["Programming Languages"]

    assert "Cloud Computing" in categories
    assert "AWS" in categories["Cloud Computing"]

    assert "DevOps & Infrastructure" in categories
    assert "Docker" in categories["DevOps & Infrastructure"]

    assert "Data Analysis & Visualization" in categories
    assert "Power BI" in categories["Data Analysis & Visualization"]

    assert "AI, Machine Learning & NLP" in categories
    assert "Machine Learning" in categories["AI, Machine Learning & NLP"]


def test_get_available_roles_and_skills():
    """Verify that predefined job roles return expected competencies."""
    roles = get_available_roles()
    assert "Cloud Engineer" in roles
    assert "Data Analyst" in roles
    assert "Machine Learning Engineer" in roles

    da_skills = get_skills_for_role("Data Analyst")
    assert "SQL" in da_skills
    assert "Excel" in da_skills
    assert "Power BI" in da_skills
