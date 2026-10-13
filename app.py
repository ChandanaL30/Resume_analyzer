"""
app.py
======
Cloud-Based Resume Analyzer - Streamlit Web Application
College Cloud Computing Project (Team of 3 Students).

A professional, modern dashboard with a blue and white theme.
Integrates resume_parser.py, skill_matcher.py, and report_generator.py.
Runs 100% locally with zero cloud setup or paid APIs required, with optional AWS S3 sync.
"""

import streamlit as st
from resume_parser import (
    parse_resume_pdf,
    extract_candidate_info,
    PYMUPDF_AVAILABLE,
)
from skill_matcher import (
    get_available_roles,
    get_skills_for_role,
    extract_skills_from_resume,
    extract_skills_from_jd,
    calculate_match_score,
    categorize_skills,
)
from report_generator import (
    create_gauge_chart,
    create_skill_bar_chart,
    create_category_distribution_chart,
    generate_recommendations,
    generate_text_report,
    generate_csv_report,
)
from cloud_storage import (
    MODE_LOCAL,
    MODE_S3,
    get_cloud_status,
    test_s3_connection,
    upload_file_to_s3,
    delete_file_from_s3,
    upload_analysis_report,
)

# -----------------------------------------------------------------------------
# 1. Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Cloud-Based Resume Analyzer",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# 2. Modern Blue & White Theme Styles
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Hero Banner */
    .hero-header {
        background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 50%, #3B82F6 100%);
        color: white;
        padding: 1.8rem 2.2rem;
        border-radius: 14px;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.16);
    }
    .hero-header h1 {
        margin: 0;
        font-size: 2.1rem;
        font-weight: 700;
        color: #FFFFFF;
    }
    .hero-header p {
        margin: 0.4rem 0 0 0;
        font-size: 1.05rem;
        color: #DBEAFE;
    }

    /* Introduction Card */
    .intro-card {
        background-color: #FFFFFF;
        border: 1px solid #BFDBFE;
        border-left: 5px solid #2563EB;
        border-radius: 10px;
        padding: 1rem 1.4rem;
        margin-bottom: 1.6rem;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
    }
    .intro-card h4 {
        margin: 0 0 0.3rem 0;
        color: #1E3A8A;
        font-size: 1.02rem;
        font-weight: 600;
    }
    .intro-card p {
        margin: 0;
        color: #475569;
        font-size: 0.92rem;
        line-height: 1.5;
    }

    /* Metric Cards */
    .metric-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.1rem;
        text-align: center;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
    }
    .metric-card .title {
        font-size: 0.78rem;
        color: #64748B;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    .metric-card .value {
        font-size: 2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-top: 0.2rem;
    }

    /* Pill Badges for Skills */
    .skill-tag {
        display: inline-block;
        padding: 0.35rem 0.8rem;
        margin: 0.25rem;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .skill-matched {
        background-color: #D1FAE5;
        color: #065F46;
        border: 1px solid #A7F3D0;
    }
    .skill-missing {
        background-color: #FEE2E2;
        color: #991B1B;
        border: 1px solid #FECACA;
    }
    .skill-extra {
        background-color: #EFF6FF;
        color: #1E40AF;
        border: 1px solid #BFDBFE;
    }

    /* Candidate Details Banner */
    .candidate-banner {
        background-color: #EFF6FF;
        border: 1px solid #BFDBFE;
        border-radius: 10px;
        padding: 0.85rem 1.2rem;
        color: #1E3A8A;
        font-size: 0.92rem;
        margin-bottom: 1.2rem;
    }

    /* Section Cards */
    .section-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.03);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# 3. Sidebar Configuration & Architecture Overview
# -----------------------------------------------------------------------------
def render_sidebar():
    """Renders academic project metadata, cloud integration status, and instructions."""
    st.sidebar.title("☁️ Cloud Analyzer")
    st.sidebar.caption("College Cloud Computing Project")

    st.sidebar.markdown("---")
    st.sidebar.subheader("👥 Project Team (3 Members)")
    st.sidebar.markdown(
        """
        - **Student 1:** Streamlit UI & Visual Dashboard
        - **Student 2:** Resume Parser & Skill Matching
        - **Student 3:** Cloud Storage & Automated Testing
        """
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("🌐 Storage & Operating Mode")
    operating_mode = st.sidebar.radio(
        "Select Mode:",
        options=[MODE_LOCAL, MODE_S3],
        index=0,
        help="Local Processing keeps all files purely in memory. AWS S3 Storage enables optional cloud archiving.",
    )

    cloud_status = get_cloud_status()

    if operating_mode == MODE_S3:
        st.sidebar.info(f"**S3 Status:** {cloud_status['status_label']}")
        with st.sidebar.expander("ℹ️ AWS S3 Details & Health Check"):
            st.write(f"**Boto3 Installed:** `{cloud_status['boto3_installed']}`")
            st.write(f"**Target Bucket:** `{cloud_status['bucket_name']}`")
            st.write(f"**Region:** `{cloud_status['region']}`")

            if cloud_status["is_configured"]:
                if st.button("Test S3 Bucket Connection", use_container_width=True):
                    success, msg = test_s3_connection()
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
            else:
                st.caption(
                    "AWS S3 is not configured in `.env`. Set `S3_BUCKET_NAME` and your AWS region/credentials to enable."
                )
    else:
        st.sidebar.success("🔒 **Local Processing Mode:** Resumes are processed purely in RAM without persistent disk or cloud storage.")

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "🔒 **Privacy Guarantee:** Uploaded resumes require explicit user consent before any cloud transmission."
    )

    return operating_mode


# -----------------------------------------------------------------------------
# 4. Main Application Workflow
# -----------------------------------------------------------------------------
def main():
    operating_mode = render_sidebar()

    # Hero Header Banner
    st.markdown(
        """
        <div class="hero-header">
            <h1>Cloud-Based Resume Analyzer</h1>
            <p>Automated ATS Skill Coverage, Skill Gap Analysis & Cloud Summary Storage</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. Short Introduction
    st.markdown(
        """
        <div class="intro-card">
            <h4>📖 Welcome to the Cloud-Based Resume Analyzer</h4>
            <p>
                This application evaluates candidate resume alignment against technical job requirements.
                Upload your resume in PDF format, paste a job description or select a role profile, and click
                <b>Analyze Resume</b> to calculate your <b>Skill Coverage Score</b>, visualize matched and missing competencies,
                and export a structured evaluation report.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not PYMUPDF_AVAILABLE:
        st.error(
            "⚠️ **PyMuPDF is not installed.** Please install it by running: `pip install PyMuPDF` in your terminal."
        )

    # -------------------------------------------------------------------------
    # Input Section: PDF Upload & Job Description
    # -------------------------------------------------------------------------
    col_input_left, col_input_right = st.columns([1, 1], gap="large")

    with col_input_left:
        st.subheader("1. Upload Candidate Resume")
        uploaded_file = st.file_uploader(
            "Select a resume in PDF format (Max 10 MB):",
            type=["pdf"],
            help="Uploaded PDF files are processed purely in-memory and discarded upon analysis.",
        )
        if uploaded_file:
            st.caption(f"📄 Selected file: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")

    with col_input_right:
        st.subheader("2. Job Description")
        jd_input_mode = st.radio(
            "Input Mode:",
            options=["Paste Custom Job Description", "Use Predefined Role Template"],
            horizontal=True,
        )

        job_description_text = ""
        target_role_title = "Custom Role"

        if jd_input_mode == "Paste Custom Job Description":
            job_description_text = st.text_area(
                "Paste the target job description or required skills:",
                height=150,
                placeholder=(
                    "e.g. Looking for a Cloud Engineer proficient in AWS, Docker, Kubernetes, "
                    "Python, Terraform, and CI/CD pipelines. Experience with SQL and Git is a plus..."
                ),
            )
        else:
            available_roles = get_available_roles()
            selected_role = st.selectbox("Select Target Role Profile:", options=available_roles)
            target_role_title = selected_role
            role_skills = get_skills_for_role(selected_role)
            default_template = (
                f"We are hiring a {selected_role}.\n"
                f"Key requirements and core skills include: {', '.join(role_skills)}.\n"
                f"Candidates should demonstrate strong technical execution, system design, and communication."
            )
            job_description_text = st.text_area(
                "Role Description Template (editable):",
                value=default_template,
                height=150,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("🔍 Analyze Resume", type="primary", use_container_width=True)

    # -------------------------------------------------------------------------
    # Analysis & Validation Flow
    # -------------------------------------------------------------------------
    # Separate analyses isolation: Reset state if uploaded resume is cleared or changed
    if not uploaded_file and "analysis_results" in st.session_state:
        st.session_state.pop("analysis_results", None)
        st.session_state.pop("uploaded_resume_s3_key", None)
        st.session_state.pop("uploaded_report_s3_key", None)
    elif uploaded_file and "analysis_results" in st.session_state:
        if st.session_state["analysis_results"].get("resume_filename") != uploaded_file.name:
            st.session_state.pop("analysis_results", None)
            st.session_state.pop("uploaded_resume_s3_key", None)
            st.session_state.pop("uploaded_report_s3_key", None)

    if analyze_btn:
        # Clear prior state before validating new analysis run
        st.session_state.pop("analysis_results", None)
        st.session_state.pop("uploaded_resume_s3_key", None)
        st.session_state.pop("uploaded_report_s3_key", None)

        # Validation 1: Missing resume file
        if not uploaded_file:
            st.warning("⚠️ Please upload a PDF resume before proceeding.")
            return

        # Validation 2: Missing job description text
        if not job_description_text or not job_description_text.strip():
            st.warning("⚠️ Please paste a job description or provide technical requirements.")
            return

        # Loading Indicator during analysis
        with st.spinner("Analyzing resume against job requirements in memory..."):
            # 1. Parse PDF in memory
            parse_result = parse_resume_pdf(uploaded_file)
            if not parse_result.success:
                if parse_result.is_scanned:
                    st.error(f"🖼️ {parse_result.error}")
                else:
                    st.error(f"⚠️ {parse_result.error}")
                return

            resume_text = parse_result.text

            # 2. Extract required skills from Job Description
            target_skills = extract_skills_from_jd(job_description_text)

            # Validation 3: Job description with no detected skills
            if not target_skills or len(target_skills) == 0:
                st.warning(
                    "⚠️ No recognized technical skills were detected in the job description. "
                    "Please provide a more detailed job description or include specific technical keywords "
                    "(e.g., Python, SQL, AWS, Docker, Machine Learning)."
                )
                return

            # 3. Extract unique candidate skills from resume
            resume_skills = extract_skills_from_resume(resume_text)

            # 4. Calculate skill coverage score and metrics
            match_data = calculate_match_score(resume_skills, target_skills)
            if not match_data.get("success", True):
                st.warning(f"⚠️ {match_data.get('message')}")
                return

            # 5. Extract candidate metadata (contact heuristics)
            candidate_info = extract_candidate_info(resume_text)

            # 6. Categorize skills for visualization
            categorized = categorize_skills(resume_skills)

            # 7. Generate actionable recommendations
            suggestions = match_data.get("suggestions") or generate_recommendations(
                match_data["missing_skills"], match_data["match_percentage"]
            )

            # 8. Generate exportable reports
            csv_content = generate_csv_report(
                match_data,
                candidate_name=candidate_info.get("name", "Candidate"),
                role_name=target_role_title,
                suggestions=suggestions,
            )
            markdown_content = generate_text_report(
                candidate_info, target_role_title, match_data, suggestions
            )

            # Store in session_state so results persist across download interactions
            file_bytes = uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else uploaded_file.read()
            st.session_state["analysis_results"] = {
                "match_data": match_data,
                "candidate_info": candidate_info,
                "categorized": categorized,
                "suggestions": suggestions,
                "csv_content": csv_content,
                "markdown_content": markdown_content,
                "target_role_title": target_role_title,
                "page_count": parse_result.page_count,
                "resume_bytes": file_bytes,
                "resume_filename": uploaded_file.name,
            }

    # -------------------------------------------------------------------------
    # Render Analysis Dashboard (Only if analysis has been performed)
    # -------------------------------------------------------------------------
    if "analysis_results" in st.session_state:
        res = st.session_state["analysis_results"]
        match_data = res["match_data"]
        candidate_info = res["candidate_info"]
        categorized = res["categorized"]
        suggestions = res["suggestions"]
        csv_content = res["csv_content"]
        markdown_content = res["markdown_content"]
        role_title = res["target_role_title"]
        page_count = res["page_count"]

        st.markdown("---")
        st.subheader("📊 Analysis Results & Candidate Profile")

        # Candidate Details Bar
        st.markdown(
            f"""
            <div class="candidate-banner">
                👤 <b>Candidate:</b> {candidate_info['name']} &nbsp;|&nbsp;
                📧 <b>Email:</b> {candidate_info['email']} &nbsp;|&nbsp;
                📞 <b>Phone:</b> {candidate_info['phone']} &nbsp;|&nbsp;
                📄 <b>Pages:</b> {page_count} &nbsp;|&nbsp;
                📝 <b>Word Count:</b> {candidate_info['word_count']} words
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 6. Calculated Skill Coverage Score Cards
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="title">Skill Coverage</div>
                    <div class="value">{match_data['match_percentage']}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m_col2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="title">Matched Skills</div>
                    <div class="value" style="color: #059669;">{match_data['matched_count']} / {match_data['target_count']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m_col3:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="title">Missing Skills</div>
                    <div class="value" style="color: #DC2626;">{len(match_data['missing_skills'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m_col4:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="title">Total Resume Skills</div>
                    <div class="value">{match_data['resume_total_skills']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # 7 & 8. Visual Charts & Skill Lists
        dash_left, dash_right = st.columns([1, 1], gap="large")

        with dash_left:
            st.plotly_chart(
                create_gauge_chart(match_data["match_percentage"]),
                use_container_width=True,
            )
            # 8. Chart comparing matched and missing skills
            st.plotly_chart(
                create_skill_bar_chart(
                    match_data["matched_count"], len(match_data["missing_skills"])
                ),
                use_container_width=True,
            )

        with dash_right:
            # 7. Matched skills
            st.markdown("#### ✅ Matched Skills")
            if match_data["matched_skills"]:
                matched_html = " ".join(
                    [
                        f'<span class="skill-tag skill-matched">{s}</span>'
                        for s in match_data["matched_skills"]
                    ]
                )
                st.markdown(matched_html, unsafe_allow_html=True)
            else:
                st.write("No matching skills detected from the required list.")

            st.markdown("<br>", unsafe_allow_html=True)

            # 7. Missing skills
            st.markdown("#### ❌ Missing Skills (Skill Gaps)")
            if match_data["missing_skills"]:
                missing_html = " ".join(
                    [
                        f'<span class="skill-tag skill-missing">{s}</span>'
                        for s in match_data["missing_skills"]
                    ]
                )
                st.markdown(missing_html, unsafe_allow_html=True)
            else:
                st.success("All required skills were identified in your resume! 🎉")

            st.markdown("<br>", unsafe_allow_html=True)

            # 7. Additional skills
            st.markdown("#### 💡 Additional Resume Skills")
            if match_data["extra_skills"]:
                extra_html = " ".join(
                    [
                        f'<span class="skill-tag skill-extra">{s}</span>'
                        for s in match_data["extra_skills"][:15]
                    ]
                )
                st.markdown(extra_html, unsafe_allow_html=True)
            else:
                st.write("No additional skills detected.")

        # Category Breakdown Chart
        if categorized:
            st.markdown("---")
            st.plotly_chart(
                create_category_distribution_chart(categorized),
                use_container_width=True,
            )

        # 9. Improvement Suggestions based on results
        st.markdown("---")
        st.subheader("💡 Improvement Suggestions & Observations")
        for tip in suggestions:
            st.markdown(f"- {tip}")

        # 10. Download CSV & Export Options
        st.markdown("---")
        st.subheader("📦 Download Reports & Export Options")
        dl_col1, dl_col2 = st.columns(2)

        with dl_col1:
            st.download_button(
                label="📊 Download CSV Evaluation Report",
                data=csv_content.encode("utf-8"),
                file_name=f"resume_analysis_{candidate_info['name'].lower().replace(' ', '_')}.csv",
                mime="text/csv",
                use_container_width=True,
                help="Downloads structured RFC 4180 CSV summary with all metrics.",
            )

        with dl_col2:
            st.download_button(
                label="📥 Download Markdown Evaluation Report",
                data=markdown_content.encode("utf-8"),
                file_name=f"resume_analysis_{candidate_info['name'].lower().replace(' ', '_')}.md",
                mime="text/markdown",
                use_container_width=True,
                help="Downloads detailed Markdown evaluation report.",
            )

        # Cloud Storage Section (Contextual to Operating Mode)
        st.markdown("---")
        st.subheader("☁️ Cloud Storage (Amazon S3)")

        if operating_mode == MODE_S3:
            st.markdown(
                """
                <div class="intro-card" style="border-left-color: #3B82F6;">
                    <h4>🌐 Amazon S3 Storage Mode Enabled</h4>
                    <p>
                        You can optionally archive candidate resumes and analysis reports to your private S3 bucket.
                        <b>Explicit user consent is strictly required</b> before any file upload.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Explicit User Consent Checkbox
            s3_consent = st.checkbox(
                "I give explicit consent to upload this candidate resume and analysis summary to the configured private AWS S3 bucket.",
                key="s3_user_consent_checkbox",
            )

            if s3_consent:
                s3_col1, s3_col2 = st.columns(2)

                # Option 1: Upload raw resume PDF
                with s3_col1:
                    st.markdown("##### 📄 Candidate Resume (PDF)")
                    if st.button("☁️ Upload Resume to S3", use_container_width=True):
                        success, s3_msg, s3_key = upload_file_to_s3(
                            file_source=res["resume_bytes"],
                            filename=res["resume_filename"],
                            user_consent=True,
                        )
                        if success:
                            st.session_state["uploaded_resume_s3_key"] = s3_key
                            st.success(s3_msg)
                        else:
                            st.error(s3_msg)

                    # Delete action if previously uploaded
                    if "uploaded_resume_s3_key" in st.session_state:
                        del_key = st.session_state["uploaded_resume_s3_key"]
                        st.caption(f"Active Key: `{del_key}`")
                        if st.button("🗑️ Delete Resume from S3", key="del_resume_btn", use_container_width=True):
                            del_success, del_msg = delete_file_from_s3(del_key)
                            if del_success:
                                st.success(del_msg)
                                del st.session_state["uploaded_resume_s3_key"]
                            else:
                                st.error(del_msg)

                # Option 2: Upload analysis summary JSON
                with s3_col2:
                    st.markdown("##### 📊 Analysis Metadata (JSON)")
                    if st.button("☁️ Save Analysis JSON to S3", use_container_width=True):
                        report_payload = {
                            "candidate_name": candidate_info["name"],
                            "email": candidate_info["email"],
                            "target_role": role_title,
                            "match_score": match_data["match_percentage"],
                            "matched_skills": match_data["matched_skills"],
                            "missing_skills": match_data["missing_skills"],
                            "total_resume_skills": match_data["resume_total_skills"],
                        }
                        success, s3_msg, rep_key = upload_analysis_report(
                            report_payload,
                            candidate_name=candidate_info["name"],
                            user_consent=True,
                        )
                        if success:
                            st.session_state["uploaded_report_s3_key"] = rep_key
                            st.success(s3_msg)
                        else:
                            st.error(s3_msg)

                    # Delete action if report uploaded
                    if "uploaded_report_s3_key" in st.session_state:
                        del_rep_key = st.session_state["uploaded_report_s3_key"]
                        st.caption(f"Active Key: `{del_rep_key}`")
                        if st.button("🗑️ Delete Report from S3", key="del_report_btn", use_container_width=True):
                            del_success, del_msg = delete_file_from_s3(del_rep_key)
                            if del_success:
                                st.success(del_msg)
                                del st.session_state["uploaded_report_s3_key"]
                            else:
                                st.error(del_msg)
            else:
                st.info("🔒 Explicit user consent must be checked above before any documents can be transmitted to S3.")

        else:
            # Local Processing Mode Message
            st.markdown(
                """
                <div class="intro-card" style="border-left-color: #10B981;">
                    <h4>🔒 Local Processing Mode Active (Privacy First)</h4>
                    <p>
                        All resume parsing, skill matching, and report generation run <b>purely in-memory</b>.
                        No files or credentials are sent to Amazon S3 or external servers.
                        To enable cloud synchronization, switch to <b>AWS S3 Storage</b> mode in the sidebar.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )


if __name__ == "__main__":
    main()
