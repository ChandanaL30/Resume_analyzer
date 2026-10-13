# College Project Guide & Viva Preparation

## 1. Team Responsibilities (Team of 3 Students)

To divide work cleanly for your submission and professor evaluation, use this breakdown:

| Team Member | Module & Files | Key Responsibilities |
| :--- | :--- | :--- |
| **Student 1 (Frontend & UX Lead)** | `app.py`, `report_generator.py` | Built the Streamlit interface, custom modern styling, metric cards, and Plotly interactive chart integration. |
| **Student 2 (NLP & Matching Logic Lead)** | `resume_parser.py`, `skill_matcher.py` | Implemented PyMuPDF text extraction, contact info regex, skill taxonomy design, and ATS gap scoring logic. |
| **Student 3 (Cloud & QA Lead)** | `cloud_storage.py`, `tests/`, `docs/` | Configured optional AWS S3 `boto3` integration, environment security (`.env.example`), test suite with `pytest`, and architecture documentation. |

---

## 2. Quick Demo Workflow for Evaluations

1. **Start the App:**
   ```bash
   cd cloud-resume-analyzer
   streamlit run app.py
   ```
2. **Demonstrate Role Selection:**
   - Select **Cloud Engineer** or paste a custom job description.
   - Point out the pre-populated required skills (AWS, Docker, Kubernetes, etc.).
3. **Upload a Sample PDF Resume:**
   - Upload any student PDF resume.
   - Click **Analyze Resume**.
4. **Showcase Results:**
   - Point out the **ATS Match Score Gauge** (Plotly).
   - Show the **Matched Skills** (green badges) vs. **Missing Skills** (red badges).
   - Show the **Candidate Profile** (Email, Phone, Word Count extracted via regex).
5. **Demonstrate Cloud / Local Features:**
   - Show the **Status Badge** in the sidebar.
   - Click **Save Analysis Summary to AWS S3** to show either the S3 upload or the safe Local Mode fallback.
   - Click **Download Markdown Report** to export the candidate evaluation.
6. **Run Unit Tests to prove code quality:**
   ```bash
   pytest tests/
   ```

---

## 3. Top Viva / Oral Exam Questions & Answers

### Q1: Why did you choose AWS S3 for storage instead of a traditional SQL database?
> **Answer:**
> Amazon S3 is an **Object Storage** service engineered for storing unstructured and semi-structured artifacts (such as JSON metadata, text reports, or files) with 99.999999999% (11 9s) data durability. For report generation and file archiving, S3 is highly scalable, cost-effective, and does not require provisioning or managing database instances.

### Q2: How does the application maintain data privacy?
> **Answer:**
> Resumes contain Personally Identifiable Information (PII). In our design, PDF files are processed purely in-memory as byte streams using PyMuPDF and are **never saved permanently to disk or to the cloud**. Only aggregated, non-sensitive analysis summaries (match scores and skill keywords) can optionally be sent to S3.

### Q3: What happens if AWS credentials are not available?
> **Answer:**
> The application incorporates **graceful degradation** and fault-tolerant design. If boto3 or AWS credentials are not configured, the system operates seamlessly in **Local Mode** without throwing unhandled exceptions or blocking the user experience.

### Q4: How is the ATS score computed?
> **Answer:**
> We extract recognized keywords from both the candidate resume and the target job description using regex word boundaries. The match score is computed as:
> $$\text{Score} = \left(\frac{\text{Count of Matched Skills}}{\text{Total Required Target Skills}}\right) \times 100$$

### Q5: What makes this cloud-native?
> **Answer:**
> It adheres to cloud-native 12-factor principles: configuration is stored in environment variables (`.env`), the application tier is stateless and containerizable, dependencies are strictly declared (`requirements.txt`), and cloud storage is treated as an attached resource.
