# Cloud-Based Resume Analyzer ☁️📄

> **College Cloud Computing Project**  
> Developed by a team of 3 students.  
> An automated, privacy-focused Applicant Tracking System (ATS) resume analyzer with optional Amazon S3 cloud storage.

---

## 📌 Project Overview
The **Cloud-Based Resume Analyzer** extracts text from PDF resumes, identifies technical competencies using Python keyword matching, compares candidate skills against target job roles, visualizes match gaps with Plotly, and optionally saves analysis summaries or resumes to Amazon S3.

The project operates in **two distinct modes**:
1. **Local Processing Mode (Default):** Runs 100% in-memory without AWS credentials, paid APIs, a database, or user login. Zero data is transmitted to the cloud.
2. **AWS S3 Storage Mode (Optional):** Integrates with a private Amazon S3 bucket via `boto3`. **Requires explicit user consent** before uploading files, uses collision-proof UUID keys, and provides both upload and delete functionality.

---

## 🚀 Key Features
- **In-Memory PDF Parsing:** Fast text and contact extraction using `PyMuPDF` (`fitz`).
- **Keyword & Skill Matching:** Scans for 50+ technical competencies across Cloud Computing, DevOps, Programming Languages, and Databases.
- **Interactive Visualizations:** ATS match score gauge, coverage bars, and domain distribution charts built with `Plotly`.
- **Target Profiles & Custom Job Descriptions:** Choose pre-configured roles (e.g., Cloud Engineer, DevOps Engineer, Data Analyst) or paste custom job descriptions.
- **Privacy First:** Resumes are processed strictly in-memory and **never stored permanently** unless explicit user consent is given for S3 archiving.
- **Optional AWS S3 Cloud Integration:**
  - Standard AWS Credential Provider Chain (`st.secrets`, environment variables, IAM Roles, or `~/.aws/credentials`).
  - Private S3 Bucket with Server-Side Encryption (`AES256`).
  - Collision-resistant unique object keys (`UUID4`).
  - Explicit user consent checkbox.
  - Upload & Delete lifecycle operations.
  - Zero raw resume text logging.
- **Exportable Reports:** Download comprehensive evaluation reports in Markdown format and RFC 4180 UTF-8 CSV format.
- **Automated Tests:** 42 automated tests using `pytest` (including fully mocked AWS calls).

---

## 🗂️ Project Structure

```text
cloud-resume-analyzer/
│
├── .streamlit/
│   └── config.toml            # Streamlit headless server and telemetry configuration
├── app.py                     # Streamlit web application entry point (modern blue/white theme)
├── resume_parser.py           # In-memory PDF text & contact metadata extraction (PyMuPDF)
├── skill_matcher.py           # Skill taxonomy, regex keyword extraction & ATS scoring
├── report_generator.py        # Plotly charts, Markdown & CSV report generation
├── cloud_storage.py           # Amazon S3 integration (upload, delete, st.secrets fallback)
├── requirements.txt           # Python package dependencies
├── README.md                  # Project documentation & deployment guide
├── .gitignore                 # Excludes secrets, .env, venv, and *.pdf resumes
├── .env.example               # Environment variables template
│
├── tests/                     # Automated unit test suite (42 tests)
│   ├── __init__.py
│   ├── test_cloud_storage.py  # Mocked S3 tests (consent, keys, upload, delete, errors)
│   ├── test_report_generator.py # Tests for CSV generation, UTF-8, and empty lists
│   ├── test_resume_parser.py  # Tests for in-memory PDF extraction, validation, and OCR alert
│   └── test_skill_matcher.py  # Tests for skill extraction, scoring formula, and disclaimers
│
└── docs/                      # Academic documentation
    ├── architecture.md        # Cloud architecture diagram & 12-factor concepts
    ├── aws_s3_setup.md        # Step-by-step private S3 bucket & IAM permissions guide
    └── project_guide.md       # Team responsibilities (3 students) & viva Q&A
```

---

## ⚙️ Local Installation & Setup

### 1. Prerequisites
- Python 3.9 to 3.13 installed on your system.
- Git installed on your system.

### 2. Navigate to Project Directory
```powershell
cd cloud-resume-analyzer
```

### 3. Create & Activate Virtual Environment
**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If script execution is disabled in PowerShell, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first, or run `.\venv\Scripts\python.exe -m ...` directly).*

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 5. Run Automated Unit Tests
Validate all 42 automated tests (runs locally with 0 cloud credentials or network calls):
```powershell
pytest tests/ -v
```

### 6. Run the Application Locally
```powershell
streamlit run app.py
```
Open your browser at 👉 **`http://localhost:8501`**.

---

## 🌐 Online Deployment Guide

### Step 1: Push the Repository to GitHub

Before deploying to the cloud, the project must be hosted in your GitHub account.

1. **Verify that secrets and resumes are ignored:**
   Ensure `.gitignore` is in place. It prevents committing `.env`, `venv/`, and `*.pdf` files:
   ```powershell
   git status
   ```
2. **Initialize Git (if not already initialized):**
   ```powershell
   git init
   ```
3. **Stage all project files:**
   ```powershell
   git add .
   ```
4. **Confirm staged files do not contain `.env`, `venv/`, or `.pdf` resumes:**
   ```powershell
   git status
   ```
   *(Ensure only source files like `app.py`, `requirements.txt`, `README.md`, `tests/`, etc., appear under "Changes to be committed").*
5. **Create the initial commit:**
   ```powershell
   git commit -m "Initial commit: Cloud-Based Resume Analyzer"
   ```
6. **Create a new repository on GitHub:**
   - Go to [github.com/new](https://github.com/new).
   - Name your repository (e.g., `cloud-resume-analyzer`).
   - Choose **Public** (or **Private**).
   - Do **NOT** initialize with a README, .gitignore, or license (they already exist in this repo).
   - Click **Create repository**.
7. **Link your local repository and push:**
   ```powershell
   git branch -M main
   git remote add origin https://github.com/<YOUR-GITHUB-USERNAME>/cloud-resume-analyzer.git
   git push -u origin main
   ```

---

### Step 2: Deploy to Streamlit Community Cloud

Streamlit Community Cloud provides free, instant cloud hosting with continuous deployment linked directly to your GitHub repository.

1. **Sign in to Streamlit Community Cloud:**
   - Navigate to [share.streamlit.io](https://share.streamlit.io/).
   - Click **Continue with GitHub** and authorize Streamlit.
2. **Create a New App:**
   - Click the **"New app"** (or **"Create app"**) button.
   - Select **"I have an existing app"** if prompted.
3. **Configure Deployment Settings:**
   - **Repository:** Select your repository: `<YOUR-GITHUB-USERNAME>/cloud-resume-analyzer`
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **App URL (optional):** Choose an available custom subdomain (e.g., `resume-analyzer-team.streamlit.app`).
4. **Configure Python Version (under Advanced settings):**
   - Click **Advanced settings**.
   - Select Python **3.11** or **3.12**.

---

### Step 3: Secure Cloud Credential Configuration (AWS S3)

> **Important:** If you only wish to use **Local Processing Mode** in the cloud, you can **skip this step**. The app runs with zero configuration and zero credentials!

If you want to enable the live **AWS S3 Storage Mode** on Streamlit Community Cloud:

1. In the Streamlit app deployment modal (or via **App Settings → Secrets** in the deployed app dashboard), paste your AWS configuration into the **Secrets** text area using TOML syntax:
   ```toml
   # Streamlit Community Cloud Secrets (st.secrets)
   AWS_REGION = "us-east-1"
   S3_BUCKET_NAME = "your-private-resume-analyzer-bucket"
   AWS_ACCESS_KEY_ID = "your_iam_access_key_here"
   AWS_SECRET_ACCESS_KEY = "your_iam_secret_key_here"
   ```
2. **How this works securely:**
   - Streamlit Cloud encrypts and stores these values in `st.secrets`.
   - `cloud_storage.py` automatically checks `st.secrets` as a fallback when environment variables are not set.
   - **Never commit `.env` or AWS keys to GitHub.**
3. Click **Save** in the Secrets dialog.
4. Click **Deploy!**

---

### Step 4: Test the Live Application with a Synthetic Resume

Once Streamlit Cloud finishes building your container, your app will be live at `https://<your-subdomain>.streamlit.app`.

To test the application safely without using real personal data:

1. **Generate a Synthetic Test PDF Resume:**  
   Run this one-line command in your terminal (uses PyMuPDF to create a clean, synthetic PDF):
   ```powershell
   python -c "import fitz; doc = fitz.open(); p = doc.new_page(); p.insert_text((50, 72), 'Alex Rivera\nalex.rivera@example.com | +1-555-0142\n\nPROFESSIONAL SUMMARY\nCloud & DevOps Engineer with 3+ years experience in cloud infrastructure, containerization, and backend automation.\n\nTECHNICAL SKILLS\n- Cloud: AWS, S3, EC2, Lambda\n- DevOps: Docker, Kubernetes, Git, CI/CD, Linux\n- Languages: Python, SQL, Bash\n- Databases: MySQL, PostgreSQL\n\nEXPERIENCE\nCloud Engineer | Acme Systems\n- Automated infrastructure deployment with Docker and Git\n- Configured private AWS S3 buckets and IAM policies\n- Developed Python data processing utilities'); doc.save('synthetic_sample_resume.pdf'); doc.close(); print('Created synthetic_sample_resume.pdf')"
   ```
2. **Test In-Memory Local Processing Mode on the Live URL:**
   - Drag and drop `synthetic_sample_resume.pdf` into the file uploader.
   - Under **Job Role**, choose **"Cloud Engineer"** (or paste a job description).
   - Click **"Analyze Resume"**.
   - **Verify:**
     - Match gauge displays an ATS score (e.g., ~70-80%).
     - Skills breakdown displays Matched Skills (e.g., `aws`, `docker`, `python`, `git`), Missing Skills, and Additional Skills.
     - Interactive Plotly charts render properly.
     - Click **"Download RFC 4180 CSV Report"** and verify the downloaded file.
3. **Test AWS S3 Storage Mode (if S3 secrets were configured):**
   - Switch the sidebar radio button to **AWS S3 Storage**.
   - Click **"Test S3 Bucket Connection"** → Confirm green banner: *"Bucket connection verified!"*.
   - Check the explicit consent checkbox: *"I consent to store this resume file in Amazon S3"*.
   - Click **"Upload Resume to S3"** → Confirm green banner with unique UUID key (`resumes/...uuid.pdf`).
   - Click **"Delete from S3"** → Confirm file is deleted.
4. **Test Error Handling:**
   - Try uploading a `.txt` file (should be rejected by uploader).
   - Try submitting with empty job description (should display clear guidance prompt).

---

## 🔒 Security & Privacy Guarantees

| Requirement | Implementation |
|---|---|
| **Zero Disk Retention** | PDFs are parsed from memory buffers (`io.BytesIO`). Files are deleted from RAM after processing. |
| **No Unconsented Uploads** | S3 uploads are strictly blocked unless user explicitly checks the consent checkbox. |
| **Credential Safety** | Standard AWS Credential Chain / `st.secrets` supported. Zero credentials hardcoded. `.gitignore` blocks `.env` and `.env.*`. |
| **No Resume Storage in Git** | `.gitignore` includes `*.pdf` to prevent accidental commit of resumes. |
| **Least Privilege IAM** | Requires only `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket`, `s3:HeadBucket`. No admin privileges required. |

---

## 👥 Team Work Allocation (3 Students)
- **Student 1:** UI/UX & Streamlit Lead (`app.py`, `report_generator.py`)
- **Student 2:** Resume Parser & NLP Scoring Lead (`resume_parser.py`, `skill_matcher.py`)
- **Student 3:** Cloud Architecture & Quality Lead (`cloud_storage.py`, `tests/`, `docs/`)

See [docs/project_guide.md](docs/project_guide.md) for detailed viva questions and answers.
