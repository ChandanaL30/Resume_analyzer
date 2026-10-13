# Amazon S3 Private Bucket Setup & IAM Configuration Guide

> **Academic Project Reference:** College Cloud Computing Project  
> This guide details how to configure a private AWS S3 bucket and IAM permissions with least-privilege access for the Cloud-Based Resume Analyzer.

---

## 1. Overview & Cloud Security Principles

1. **Private by Default:**  
   The S3 bucket must **never** be publicly accessible. All public access block settings (`BlockPublicAcls`, `IgnorePublicAcls`, `BlockPublicPolicy`, `RestrictPublicBuckets`) must remain enabled.
2. **Server-Side Encryption (SSE):**  
   All objects stored in S3 are encrypted at rest using `AES256` (SSE-S3).
3. **Explicit Consent & Lifecycle Management:**  
   The application requires explicit user consent before any file transmission and provides both `Upload` and `Delete` capabilities.
4. **Credential Isolation:**  
   Credentials are never hardcoded. Boto3 utilizes the standard AWS credential provider chain (`.env`, environment variables, AWS CLI credentials file, or IAM Roles).

---

## 2. Step 1: Create a Private S3 Bucket

### Option A: Using the AWS CLI
Run these commands in PowerShell or Bash:

```bash
# 1. Set your variables
$BUCKET_NAME="college-cloud-resume-analyzer-$(Get-Random)"
$AWS_REGION="us-east-1"

# 2. Create the bucket
aws s3api create-bucket `
    --bucket $BUCKET_NAME `
    --region $AWS_REGION

# 3. Enable Block Public Access (Enforces private bucket status)
aws s3api put-public-access-block `
    --bucket $BUCKET_NAME `
    --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# 4. Enable default Server-Side Encryption (SSE-S3 AES256)
aws s3api put-bucket-encryption `
    --bucket $BUCKET_NAME `
    --server-side-encryption-configuration '{"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]}'
```

### Option B: Using the AWS Management Console
1. Navigate to **Amazon S3 > Buckets > Create bucket**.
2. **Bucket name:** Enter a globally unique name (e.g., `cloud-resume-analyzer-yourname-2026`).
3. **AWS Region:** Select your preferred region (e.g., `us-east-1` or `ap-south-1`).
4. **Object Ownership:** Keep *ACLs disabled (recommended)*.
5. **Block Public Access settings for this bucket:** Ensure **Block all public access** is **checked** (Enabled).
6. **Default encryption:** Select **Server-side encryption with Amazon S3 managed keys (SSE-S3)**.
7. Click **Create bucket**.

---

## 3. Step 2: Minimum Required IAM Policy (Least Privilege)

Create an IAM policy that only grants the minimal permissions required by the application:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BucketLevelPermissions",
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:GetBucketLocation"
            ],
            "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME"
        },
        {
            "Sid": "ObjectLevelPermissions",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME/*"
        }
    ]
}
```

> **Note on Permissions:**  
> - `s3:ListBucket` & `s3:GetBucketLocation` are required to test connectivity (`head_bucket`).  
> - `s3:PutObject` is required to upload resumes and JSON summaries.  
> - `s3:DeleteObject` allows users to purge uploaded objects to respect candidate data retention preferences.  
> - No admin or broad `*` permissions are granted.

---

## 4. Step 3: Configure the Local Environment

1. In the `cloud-resume-analyzer/` folder, create `.env` from `.env.example`:
   ```powershell
   copy .env.example .env
   ```
2. Open `.env` and fill in your bucket name and region:
   ```env
   AWS_REGION=us-east-1
   S3_BUCKET_NAME=your-private-resume-analyzer-bucket
   AWS_ACCESS_KEY_ID=your_aws_access_key_id_here
   AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key_here
   ```
   *(If running on AWS EC2/ECS with an attached IAM role or using Streamlit Cloud secrets, leave the local access key and secret key blank).*

---

## 5. Verification & Testing

- **Mocked Unit Tests (No AWS account required):**  
  All AWS code paths (connection tests, bucket not found 404, access denied 403, missing credentials, unique key generation, upload, and delete) are 100% verified using mocked tests:
  ```powershell
  python -m pytest tests/test_cloud_storage.py -v
  ```
- **Local Fallback:**  
  If `.env` credentials are missing or invalid, the application operates in **Local Processing Mode** without crashing or throwing unhandled errors.
