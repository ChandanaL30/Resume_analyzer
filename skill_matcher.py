"""
skill_matcher.py
================
Module for extracting technical competencies, matching resumes against job requirements,
and computing ATS skill coverage using case-insensitive regex pattern matching.

Features:
- Dictionary of common skills across Data Science, AI/ML, Cloud, DevOps, and Programming.
- Strict false-positive prevention (e.g., prevents matching 'Excel' inside 'excellent',
  'Git' inside 'digital', 'AWS' inside 'awareness', or 'Java' inside 'JavaScript').
- Functions for extracting unique skills, finding matches, missing skills, additional skills,
  calculating skill coverage, and generating constructive suggestions.
- Graceful handling when no skills are detected in job descriptions.
- Explicit non-evaluative disclaimer (keyword matching does not prove candidate ability).
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple

# =============================================================================
# 1. Comprehensive Dictionary of Common Technical Skills
# =============================================================================

SKILL_TAXONOMY: Dict[str, List[str]] = {
    "Programming Languages": [
        "Python", "Java", "C++", "C#", "C", "JavaScript", "TypeScript",
        "SQL", "MySQL", "PostgreSQL", "Go", "Golang", "Rust", "R", "PHP"
    ],
    "Data Analysis & Visualization": [
        "Excel", "Power BI", "Tableau", "Data Visualization",
        "Pandas", "NumPy", "Statistics", "Data Analysis", "Spreadsheets"
    ],
    "AI, Machine Learning & NLP": [
        "Machine Learning", "Deep Learning", "NLP", "Generative AI",
        "Scikit-Learn", "TensorFlow", "PyTorch", "Computer Vision",
        "Large Language Models", "LLM"
    ],
    "Cloud Computing": [
        "AWS", "Azure", "Google Cloud", "GCP", "EC2", "S3",
        "AWS Lambda", "CloudFormation", "IAM", "Serverless"
    ],
    "DevOps & Infrastructure": [
        "Docker", "Git", "Kubernetes", "CI/CD", "Terraform", "Ansible",
        "Jenkins", "Linux", "Bash", "Prometheus", "Grafana"
    ],
    "Databases & Storage": [
        "MongoDB", "Redis", "DynamoDB", "SQLite", "Cassandra", "Oracle"
    ],
    "Web & Backend Frameworks": [
        "React", "Node.js", "Express", "FastAPI", "Flask", "Django",
        "HTML", "CSS", "REST API", "GraphQL"
    ],
    "Methodologies & Soft Skills": [
        "Agile", "Scrum", "Microservices", "System Design",
        "Data Structures", "Algorithms", "Problem Solving"
    ]
}

# Skill synonyms and aliases mapping to canonical display names
SKILL_ALIASES: Dict[str, str] = {
    # Programming & Databases
    "python": "Python",
    "java": "Java",
    "c++": "C++",
    "cpp": "C++",
    "sql": "SQL",
    "mysql": "MySQL",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "javascript": "JavaScript",
    "typescript": "TypeScript",

    # Data & Visualization
    "excel": "Excel",
    "ms excel": "Excel",
    "microsoft excel": "Excel",
    "power bi": "Power BI",
    "powerbi": "Power BI",
    "tableau": "Tableau",
    "data visualization": "Data Visualization",
    "data viz": "Data Visualization",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "statistics": "Statistics",
    "statistical analysis": "Statistics",
    "data analysis": "Data Analysis",

    # AI & ML
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
    "deep learning": "Deep Learning",
    "nlp": "NLP",
    "natural language processing": "NLP",
    "generative ai": "Generative AI",
    "genai": "Generative AI",
    "gen ai": "Generative AI",
    "scikit-learn": "Scikit-Learn",
    "sklearn": "Scikit-Learn",
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",

    # Cloud & DevOps
    "aws": "AWS",
    "amazon web services": "AWS",
    "azure": "Azure",
    "microsoft azure": "Azure",
    "docker": "Docker",
    "git": "Git",
    "github": "Git",
    "gitlab": "Git",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "linux": "Linux",
    "terraform": "Terraform",
}

# Predefined job profiles for quick demonstrations
PREDEFINED_ROLES: Dict[str, List[str]] = {
    "Cloud Engineer": [
        "AWS", "Azure", "Docker", "Kubernetes", "Terraform", "Linux",
        "Python", "CI/CD", "Git"
    ],
    "Data Analyst": [
        "SQL", "Excel", "Power BI", "Tableau", "Data Visualization",
        "Python", "Pandas", "Statistics", "Data Analysis"
    ],
    "Machine Learning Engineer": [
        "Python", "Machine Learning", "Deep Learning", "NLP", "Generative AI",
        "Pandas", "NumPy", "TensorFlow", "PyTorch", "Git", "Docker"
    ],
    "DevOps Engineer": [
        "Docker", "Kubernetes", "Git", "CI/CD", "Terraform",
        "Linux", "AWS", "Python"
    ],
    "Full Stack Developer": [
        "JavaScript", "TypeScript", "React", "Node.js", "Python",
        "SQL", "REST API", "Git", "Docker"
    ],
}


def _build_master_catalog() -> Dict[str, str]:
    """
    Builds a unified lookup mapping lowercase skill pattern -> Canonical display name.
    """
    catalog = {}
    # 1. Add all from taxonomy
    for _, skills in SKILL_TAXONOMY.items():
        for skill in skills:
            catalog[skill.lower()] = skill

    # 2. Add aliases
    for alias, canonical in SKILL_ALIASES.items():
        catalog[alias.lower()] = canonical

    return catalog


MASTER_SKILL_LOOKUP = _build_master_catalog()


def get_available_roles() -> List[str]:
    """Returns list of pre-configured job role titles."""
    return list(PREDEFINED_ROLES.keys())


def get_skills_for_role(role_name: str) -> List[str]:
    """Returns required skills for a given job role name."""
    return PREDEFINED_ROLES.get(role_name, [])


# =============================================================================
# 2. Strict Pattern Building & False Positive Prevention
# =============================================================================

def build_skill_regex(skill: str) -> str:
    """
    Constructs a precise regular expression for a skill term.
    Enforces strict word boundaries using lookahead and lookbehind assertions
    to prevent false positives from substrings in common English words.

    Examples prevented:
    - 'excel' inside 'excellent' or 'excellence'
    - 'git' inside 'digital' or 'legitimate'
    - 'aws' inside 'awareness' or 'flaws'
    - 'sql' inside 'squalor' or 'mosque'
    - 'c++' matching 'c+++'
    - 'java' matching 'javascript'

    Args:
        skill (str): Lowercase skill phrase.

    Returns:
        str: Regular expression pattern string.
    """
    esc = re.escape(skill)

    # Special handling for skills ending with '+' (e.g. C++)
    if esc.endswith(r"\+\+"):
        return r"(?<![a-zA-Z0-9_])" + esc + r"(?![a-zA-Z0-9_+])"

    # Multi-word skills with possible internal spaces (e.g., 'power bi', 'generative ai')
    if r"\ " in esc:
        esc = esc.replace(r"\ ", r"\s+")

    return r"(?<![a-zA-Z0-9_])" + esc + r"(?![a-zA-Z0-9_])"


# =============================================================================
# 3. Core Extraction and Matching Functions
# =============================================================================

def extract_skills_from_text(text: str, custom_skills: Optional[Set[str]] = None) -> List[str]:
    """
    Extracts unique recognized skills from freeform text using case-insensitive matching.

    Args:
        text (str): Input text (resume or job description).
        custom_skills (Optional[Set[str]]): Additional custom skills to search for.

    Returns:
        List[str]: Sorted list of unique canonical skill names detected.
    """
    if not text or not isinstance(text, str):
        return []

    found_skills: Set[str] = set()

    # Search through standard taxonomy and aliases
    for phrase, canonical_name in MASTER_SKILL_LOOKUP.items():
        pattern = build_skill_regex(phrase)
        if re.search(pattern, text, re.IGNORECASE):
            found_skills.add(canonical_name)

    # Search custom user-provided skills if provided
    if custom_skills:
        for custom_skill in custom_skills:
            if not custom_skill or not custom_skill.strip():
                continue
            cleaned_custom = custom_skill.strip()
            pattern = build_skill_regex(cleaned_custom.lower())
            if re.search(pattern, text, re.IGNORECASE):
                found_skills.add(cleaned_custom)

    return sorted(list(found_skills))


def extract_skills_from_resume(resume_text: str, custom_skills: Optional[Set[str]] = None) -> List[str]:
    """
    Extracts unique skills from a candidate's resume text.

    Args:
        resume_text (str): Resume text content.
        custom_skills (Optional[Set[str]]): Optional additional skills.

    Returns:
        List[str]: Unique skills detected in the resume.
    """
    return extract_skills_from_text(resume_text, custom_skills=custom_skills)


def extract_skills_from_jd(jd_text: str, custom_skills: Optional[Set[str]] = None) -> List[str]:
    """
    Extracts unique required skills from a job description.

    Args:
        jd_text (str): Job description text.
        custom_skills (Optional[Set[str]]): Optional additional skills.

    Returns:
        List[str]: Unique required skills detected in the job description.
    """
    return extract_skills_from_text(jd_text, custom_skills=custom_skills)


def find_matched_skills(resume_skills: List[str], required_skills: List[str]) -> List[str]:
    """
    Finds skills present in both the candidate's resume and the job requirements.

    Args:
        resume_skills (List[str]): Skills detected on resume.
        required_skills (List[str]): Skills required by job.

    Returns:
        List[str]: Sorted list of matched skills with canonical display casing.
    """
    resume_map = {s.lower(): s for s in resume_skills}
    required_map = {s.lower(): s for s in required_skills}

    matched_keys = set(resume_map.keys()) & set(required_map.keys())
    return sorted([MASTER_SKILL_LOOKUP.get(k, required_map[k]) for k in matched_keys])


def find_missing_skills(resume_skills: List[str], required_skills: List[str]) -> List[str]:
    """
    Finds required skills that are missing from the candidate's resume.

    Args:
        resume_skills (List[str]): Skills detected on resume.
        required_skills (List[str]): Skills required by job.

    Returns:
        List[str]: Sorted list of missing required skills with canonical display casing.
    """
    resume_keys = {s.lower() for s in resume_skills}
    required_map = {s.lower(): s for s in required_skills}

    missing_keys = set(required_map.keys()) - resume_keys
    return sorted([MASTER_SKILL_LOOKUP.get(k, required_map[k]) for k in missing_keys])


def find_additional_skills(resume_skills: List[str], required_skills: List[str]) -> List[str]:
    """
    Finds additional skills present on the resume that were not specifically requested by the job.

    Args:
        resume_skills (List[str]): Skills detected on resume.
        required_skills (List[str]): Skills required by job.

    Returns:
        List[str]: Sorted list of extra candidate skills with canonical display casing.
    """
    required_keys = {s.lower() for s in required_skills}
    resume_map = {s.lower(): s for s in resume_skills}

    extra_keys = set(resume_map.keys()) - required_keys
    return sorted([MASTER_SKILL_LOOKUP.get(k, resume_map[k]) for k in extra_keys])


def calculate_skill_coverage(matched_skills: List[str], required_skills: List[str]) -> float:
    """
    Calculates the skill coverage percentage.

    Formula:
    Skill coverage = matched unique required skills / total unique required skills * 100

    Args:
        matched_skills (List[str]): Matched unique skills.
        required_skills (List[str]): Total unique required skills.

    Returns:
        float: Coverage percentage rounded to 1 decimal place (0.0 to 100.0).
    """
    # Count unique terms using lowercase normalization
    unique_matched = len(set(s.lower() for s in matched_skills))
    unique_required = len(set(s.lower() for s in required_skills))

    if unique_required == 0:
        return 0.0

    coverage = (unique_matched / unique_required) * 100.0
    return round(coverage, 1)


def generate_skill_suggestions(missing_skills: List[str]) -> List[str]:
    """
    Generates actionable resume improvement suggestions based on missing skills.

    Includes an explicit notice that keyword matching evaluates lexical alignment
    rather than proving candidate ability or predicting hiring outcomes.

    Args:
        missing_skills (List[str]): Required skills not found on resume.

    Returns:
        List[str]: Formatted list of suggestions.
    """
    suggestions = []

    if not missing_skills:
        suggestions.append(
            "All required technical skills specified in the job description were detected in your resume."
        )
    else:
        top_missing = missing_skills[:4]
        skills_formatted = ", ".join(f"'{s}'" for s in top_missing)
        suggestions.append(
            f"Consider highlighting practical experience, coursework, or projects involving {skills_formatted}."
        )

        # Domain-specific tips
        data_skills = {"SQL", "Excel", "Power BI", "Tableau", "Pandas", "NumPy", "Statistics"}
        if data_skills.intersection(set(missing_skills)):
            suggestions.append(
                "For data analysis roles, include specific business metrics, dashboards created, or data pipelines built."
            )

        ai_skills = {"Machine Learning", "Deep Learning", "NLP", "Generative AI"}
        if ai_skills.intersection(set(missing_skills)):
            suggestions.append(
                "For AI/ML roles, mention model architectures used, evaluation metrics (e.g. F1-score, accuracy), or deployed endpoints."
            )

        cloud_skills = {"AWS", "Azure", "Docker", "Git", "Kubernetes"}
        if cloud_skills.intersection(set(missing_skills)):
            suggestions.append(
                "For cloud/DevOps roles, highlight containerized applications, cloud architectures, or CI/CD pipelines."
            )

    # General best practice
    suggestions.append(
        "Quantify project outcomes with concrete numbers and action verbs where appropriate."
    )

    # Mandatory academic & ethical disclaimer
    suggestions.append(
        "Disclaimer: This analysis reflects lexical keyword coverage against the provided job description. "
        "Keyword matching does not evaluate overall candidate competence, practical problem-solving ability, "
        "or guarantee hiring decisions."
    )

    return suggestions


# =============================================================================
# 4. High-Level Analysis Interface for Dashboard & Reports
# =============================================================================

def calculate_match_score(
    resume_skills: List[str], target_skills: List[str]
) -> Dict[str, Any]:
    """
    Structured matching engine used by Streamlit app.py and report_generator.py.

    Handles edge cases gracefully: if no skills are detected in the target requirements,
    returns an informative status rather than displaying a misleading score.

    Args:
        resume_skills (List[str]): Unique skills detected on candidate resume.
        target_skills (List[str]): Unique required skills.

    Returns:
        Dict[str, Any]: Structured metrics including coverage score, lists, and advice.
    """
    # Edge case: No skills detected in the job requirements
    if not target_skills or len(target_skills) == 0:
        return {
            "success": False,
            "match_percentage": 0.0,
            "matched_skills": [],
            "missing_skills": [],
            "extra_skills": resume_skills,
            "matched_count": 0,
            "target_count": 0,
            "resume_total_skills": len(resume_skills),
            "message": (
                "No recognized technical skills were detected in the job description. "
                "Please provide a more detailed job description or include specific technical keywords."
            ),
            "suggestions": [
                "Please paste a detailed job description that includes specific tools, technologies, and technical requirements.",
                "Disclaimer: Keyword matching does not evaluate overall candidate competence or predict hiring outcomes."
            ],
        }

    matched = find_matched_skills(resume_skills, target_skills)
    missing = find_missing_skills(resume_skills, target_skills)
    extra = find_additional_skills(resume_skills, target_skills)
    coverage = calculate_skill_coverage(matched, target_skills)
    suggestions = generate_skill_suggestions(missing)

    return {
        "success": True,
        "match_percentage": coverage,
        "matched_skills": matched,
        "missing_skills": missing,
        "extra_skills": extra,
        "matched_count": len(matched),
        "target_count": len(target_skills),
        "resume_total_skills": len(resume_skills),
        "message": None,
        "suggestions": suggestions,
    }


def categorize_skills(skills: List[str]) -> Dict[str, List[str]]:
    """
    Groups a list of skills into taxonomy domains (Cloud, Data, AI/ML, etc.).

    Args:
        skills (List[str]): List of skills to group.

    Returns:
        Dict[str, List[str]]: Categorized breakdown of skills.
    """
    grouped: Dict[str, List[str]] = {cat: [] for cat in SKILL_TAXONOMY.keys()}
    grouped["Other / Specialized"] = []

    for skill in skills:
        assigned = False
        for category, cat_skills in SKILL_TAXONOMY.items():
            if any(skill.lower() == s.lower() for s in cat_skills):
                grouped[category].append(skill)
                assigned = True
                break
        if not assigned:
            grouped["Other / Specialized"].append(skill)

    # Filter out empty categories for clean visualization
    return {k: v for k, v in grouped.items() if len(v) > 0}
