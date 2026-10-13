"""
report_generator.py
===================
Generates visual charts with Plotly and comprehensive text/markdown summary reports.
"""

import csv
import io
from typing import Any, Dict, List, Optional
import plotly.graph_objects as go


def create_gauge_chart(score: float) -> go.Figure:
    """
    Creates an interactive gauge chart for the ATS Match Score using Plotly.

    Args:
        score (float): Match percentage (0.0 to 100.0).

    Returns:
        go.Figure: Plotly Figure object.
    """
    # Determine needle / bar color based on score tier
    if score >= 75:
        bar_color = "#10B981"  # Emerald green
    elif score >= 50:
        bar_color = "#F59E0B"  # Amber / orange
    else:
        bar_color = "#EF4444"  # Red

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "%", "font": {"size": 42, "color": "#1E293B"}},
            title={"text": "ATS Match Score", "font": {"size": 20, "color": "#475569"}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#94A3B8"},
                "bar": {"color": bar_color, "thickness": 0.28},
                "bgcolor": "white",
                "borderwidth": 2,
                "bordercolor": "#E2E8F0",
                "steps": [
                    {"range": [0, 50], "color": "#FEE2E2"},    # Soft red
                    {"range": [50, 75], "color": "#FEF3C7"},   # Soft yellow
                    {"range": [75, 100], "color": "#D1FAE5"},  # Soft green
                ],
                "threshold": {
                    "line": {"color": "#0F172A", "width": 3},
                    "thickness": 0.75,
                    "value": score,
                },
            },
        )
    )

    fig.update_layout(
        height=280,
        margin=dict(l=25, r=25, t=50, b=25),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "sans-serif"},
    )
    return fig


def create_skill_bar_chart(matched_count: int, missing_count: int) -> go.Figure:
    """
    Creates a comparison bar chart between matched and missing skills.

    Args:
        matched_count (int): Number of matched skills.
        missing_count (int): Number of missing skills.

    Returns:
        go.Figure: Plotly horizontal bar chart.
    """
    categories = ["Matched Skills", "Missing Skills"]
    counts = [matched_count, missing_count]
    colors = ["#10B981", "#EF4444"]

    fig = go.Figure(
        go.Bar(
            x=counts,
            y=categories,
            orientation="h",
            marker=dict(color=colors, line=dict(color="#CBD5E1", width=1)),
            text=counts,
            textposition="auto",
        )
    )

    fig.update_layout(
        title={"text": "Skill Coverage Breakdown", "font": {"size": 16}},
        xaxis_title="Number of Skills",
        height=200,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="#F1F5F9"),
    )
    return fig


def create_category_distribution_chart(categorized_skills: Dict[str, List[str]]) -> go.Figure:
    """
    Creates a bar chart of skills detected across technical domains.

    Args:
        categorized_skills (Dict[str, List[str]]): Categorized skills dictionary.

    Returns:
        go.Figure: Plotly vertical bar chart.
    """
    categories = list(categorized_skills.keys())
    counts = [len(v) for v in categorized_skills.values()]

    fig = go.Figure(
        go.Bar(
            x=categories,
            y=counts,
            marker_color="#3B82F6",
            text=counts,
            textposition="auto",
        )
    )

    fig.update_layout(
        title={"text": "Resume Skills by Category", "font": {"size": 16}},
        yaxis_title="Count",
        height=260,
        margin=dict(l=20, r=20, t=40, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_tickangle=-25,
        yaxis=dict(showgrid=True, gridcolor="#F1F5F9"),
    )
    return fig


def generate_recommendations(missing_skills: List[str], match_score: float) -> List[str]:
    """
    Generates actionable, personalized recommendations for resume improvement.

    Args:
        missing_skills (List[str]): List of missing keywords.
        match_score (float): Overall ATS match percentage.

    Returns:
        List[str]: Actionable recommendation bullet points.
    """
    recommendations = []

    if match_score >= 80:
        recommendations.append("🌟 Strong alignment! Your resume closely reflects the job requirements.")
    elif match_score >= 55:
        recommendations.append("⚡ Moderate match. Bridging a few high-priority skill gaps will significantly improve your chances.")
    else:
        recommendations.append("⚠️ Low alignment. Consider tailoring your resume with hands-on projects featuring the target skills.")

    # High-impact skill recommendations
    if missing_skills:
        top_missing = missing_skills[:4]
        skills_str = ", ".join(f"**{s}**" for s in top_missing)
        recommendations.append(
            f"Add relevant coursework, projects, or practical experience for key missing skills: {skills_str}."
        )

        # Cloud-specific suggestion
        cloud_keywords = {"AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform"}
        overlap = cloud_keywords.intersection(set(missing_skills))
        if overlap:
            recommendations.append(
                f"Cloud gap detected: Consider obtaining an entry-level cloud certification (e.g., AWS Cloud Practitioner) or deploying a demo project using {', '.join(overlap)}."
            )

    recommendations.append(
        "Quantify your accomplishments using action verbs and metrics (e.g., 'Reduced deployment time by 30% using Docker')."
    )
    recommendations.append(
        "Disclaimer: This analysis reflects lexical keyword coverage against the provided job description. "
        "Keyword matching does not evaluate overall candidate competence, practical problem-solving ability, "
        "or guarantee hiring decisions."
    )

    return recommendations


def generate_text_report(
    candidate_info: Dict[str, any],
    role_name: str,
    match_data: Dict[str, any],
    recommendations: List[str],
) -> str:
    """
    Compiles an exportable Markdown evaluation report.

    Args:
        candidate_info (Dict): Candidate details (name, email, phone, word count).
        role_name (str): Target job role title.
        match_data (Dict): Match metrics dictionary.
        recommendations (List[str]): Actionable advice.

    Returns:
        str: Formatted Markdown text report.
    """
    matched_str = ", ".join(match_data.get("matched_skills", [])) or "None detected"
    missing_str = ", ".join(match_data.get("missing_skills", [])) or "None missing"
    extra_str = ", ".join(match_data.get("extra_skills", [])) or "None"

    rec_lines = "\n".join(f"- {rec}" for rec in recommendations)

    report = f"""# Cloud-Based Resume Analyzer - Evaluation Report
============================================================
**Target Position:** {role_name}
**Candidate Name:** {candidate_info.get('name', 'Candidate')}
**Contact Email:** {candidate_info.get('email', 'Not detected')}
**Contact Phone:** {candidate_info.get('phone', 'Not detected')}
**Resume Word Count:** {candidate_info.get('word_count', 0)} words

---

## 1. Overall Match Summary
- **ATS Match Score:** {match_data.get('match_percentage', 0.0)}%
- **Target Skills Required:** {match_data.get('target_count', 0)}
- **Matched Skills:** {match_data.get('matched_count', 0)}
- **Missing Skills:** {len(match_data.get('missing_skills', []))}
- **Total Skills on Resume:** {match_data.get('resume_total_skills', 0)}

---

## 2. Skill Breakdown
### Matched Skills:
{matched_str}

### Missing Target Skills:
{missing_str}

### Additional Candidate Skills:
{extra_str}

---

## 3. Recommendations & Next Steps
{rec_lines}

---
*Report generated by Cloud-Based Resume Analyzer (College Cloud Computing Project).*
"""
    return report


def generate_csv_report(
    match_data: Dict[str, Any],
    candidate_name: Optional[str] = None,
    role_name: Optional[str] = None,
    suggestions: Optional[List[str]] = None,
) -> str:
    """
    Generates a structured, downloadable CSV evaluation report from actual analysis results.

    The CSV includes:
    - Skill coverage percentage
    - Total required skills
    - Matched skills
    - Missing skills
    - Additional resume skills
    - Improvement suggestions

    Formatted using UTF-8 standard encoding with safe handling for empty lists.
    Does not embed raw resume text or unnecessary personal information.

    Args:
        match_data (Dict[str, Any]): Real output dictionary from calculate_match_score.
        candidate_name (Optional[str]): Safe candidate display identifier (e.g. "Candidate").
        role_name (Optional[str]): Target job position.
        suggestions (Optional[List[str]]): List of improvement suggestions (falls back to match_data["suggestions"]).

    Returns:
        str: Valid RFC 4180 CSV string content.
    """
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")

    # Header
    writer.writerow(["Metric", "Value"])

    if role_name:
        writer.writerow(["Target Position", role_name])
    if candidate_name:
        writer.writerow(["Candidate Identifier", candidate_name])

    # 1. Skill coverage percentage
    coverage = match_data.get("match_percentage", 0.0)
    writer.writerow(["Skill Coverage Percentage", f"{coverage}%"])

    # 2. Total required skills
    target_count = match_data.get(
        "target_count",
        len(match_data.get("matched_skills", [])) + len(match_data.get("missing_skills", [])),
    )
    writer.writerow(["Total Required Skills", target_count])

    # 3. Matched skills
    matched_skills = match_data.get("matched_skills", [])
    writer.writerow(
        ["Matched Skills", "; ".join(matched_skills) if matched_skills else "None detected"]
    )

    # 4. Missing skills
    missing_skills = match_data.get("missing_skills", [])
    writer.writerow(
        ["Missing Skills", "; ".join(missing_skills) if missing_skills else "None missing"]
    )

    # 5. Additional resume skills
    extra_skills = match_data.get("extra_skills", [])
    writer.writerow(
        ["Additional Resume Skills", "; ".join(extra_skills) if extra_skills else "None detected"]
    )

    # 6. Improvement suggestions
    sug_list = suggestions or match_data.get("suggestions", [])
    writer.writerow(
        ["Improvement Suggestions", " | ".join(sug_list) if sug_list else "None"]
    )

    return output.getvalue()

