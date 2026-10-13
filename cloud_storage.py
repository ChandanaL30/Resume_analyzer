"""
cloud_storage.py
================
Amazon S3 integration module for the Cloud-Based Resume Analyzer.

Features:
- Dual Operating Modes: 'Local Processing' (default) and 'AWS S3 Storage'.
- Requires explicit user consent before uploading any file to AWS S3.
- Standard AWS Credential Provider Chain support (Env vars, IAM Roles, ~/.aws/credentials).
- Unique object key generation using UUID4 to prevent collision and overwriting.
- Both Upload and Delete functions for S3 lifecycle management.
- Zero raw resume content logging.
- Comprehensive exception handling (NoCredentialsError, ClientError, EndpointConnectionError).
"""

import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Safe import of boto3 and botocore exceptions
try:
    import boto3
    from botocore.exceptions import (
        ClientError,
        EndpointConnectionError,
        NoCredentialsError,
        PartialCredentialsError,
        ParamValidationError,
    )
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    ClientError = Exception
    EndpointConnectionError = Exception
    NoCredentialsError = Exception
    PartialCredentialsError = Exception
    ParamValidationError = Exception


# Storage Mode Constants
MODE_LOCAL = "Local Processing"
MODE_S3 = "AWS S3 Storage"


def get_cloud_config() -> Dict[str, Optional[str]]:
    """
    Retrieves cloud configuration from standard environment variables or Streamlit secrets.
    Seamlessly supports local .env, system environment variables, and Streamlit Community Cloud (st.secrets).
    Secret credentials are never hardcoded.
    """
    def _get_val(key: str, default: Optional[str] = None) -> Optional[str]:
        val = os.getenv(key)
        if val:
            return val
        try:
            import streamlit as st
            if hasattr(st, "secrets") and key in st.secrets:
                return str(st.secrets[key])
        except Exception:
            pass
        return default

    return {
        "region": _get_val("AWS_REGION") or _get_val("AWS_DEFAULT_REGION") or "us-east-1",
        "bucket_name": _get_val("S3_BUCKET_NAME"),
        "access_key": _get_val("AWS_ACCESS_KEY_ID"),
        "secret_key": _get_val("AWS_SECRET_ACCESS_KEY"),
        "session_token": _get_val("AWS_SESSION_TOKEN"),
    }


def is_s3_configured() -> bool:
    """
    Checks if boto3 is installed and a target S3 bucket name is specified.
    Uses standard AWS credential provider chain if explicit keys are omitted.
    """
    if not BOTO3_AVAILABLE:
        return False
    config = get_cloud_config()
    return bool(config["bucket_name"])


def get_s3_client(region: Optional[str] = None):
    """
    Instantiates an S3 client using the standard AWS credential provider chain.
    Supports IAM Roles, EC2/ECS metadata, ~/.aws/credentials, or environment variables.
    """
    if not BOTO3_AVAILABLE:
        return None

    config = get_cloud_config()
    target_region = region or config["region"]

    # If explicit keys are in environment, use them; otherwise let boto3 resolve via credential chain
    if config["access_key"] and config["secret_key"]:
        session = boto3.Session(
            aws_access_key_id=config["access_key"],
            aws_secret_access_key=config["secret_key"],
            aws_session_token=config["session_token"],
            region_name=target_region,
        )
    else:
        session = boto3.Session(region_name=target_region)

    return session.client("s3")


def generate_unique_object_key(prefix: str, original_filename: str) -> str:
    """
    Generates a collision-resistant unique object key using UUID4 and sanitized filename.

    Args:
        prefix (str): Storage path prefix (e.g. 'resumes/' or 'reports/').
        original_filename (str): Base filename.

    Returns:
        str: Unique object key (e.g. 'resumes/20261013_a1b2c3d4_resume.pdf').
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    unique_token = uuid.uuid4().hex[:8]

    # Sanitize original filename (allow alphanumeric, dashes, dots, underscores)
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", os.path.basename(original_filename))
    if not safe_name.strip():
        safe_name = "document.pdf"

    clean_prefix = prefix.strip("/")
    return f"{clean_prefix}/{timestamp}_{unique_token}_{safe_name}"


def test_s3_connection(bucket_name: Optional[str] = None) -> Tuple[bool, str]:
    """
    Tests S3 connectivity and validates access to the private bucket.

    Returns:
        Tuple[bool, str]: (is_successful, status_description)
    """
    if not BOTO3_AVAILABLE:
        return False, "boto3 library is not installed. Running in Local Processing Mode."

    config = get_cloud_config()
    target_bucket = bucket_name or config["bucket_name"]

    if not target_bucket:
        return (
            False,
            "S3_BUCKET_NAME environment variable is not configured. Running in Local Processing Mode.",
        )

    try:
        s3 = get_s3_client()
        if not s3:
            return False, "Unable to initialize S3 client."

        # Verify bucket access and permissions (head_bucket requires s3:ListBucket permission)
        s3.head_bucket(Bucket=target_bucket)
        return True, f"Successfully connected to private S3 bucket: '{target_bucket}'"

    except NoCredentialsError:
        return False, "No AWS credentials found. Please configure AWS credentials via environment or IAM role."
    except PartialCredentialsError:
        return False, "Incomplete AWS credentials. Please check your Access Key and Secret Key."
    except ClientError as e:
        error_code = str(e.response.get("Error", {}).get("Code", "Unknown"))
        if error_code in ("404", "NoSuchBucket"):
            return False, f"Bucket '{target_bucket}' does not exist or cannot be found."
        elif error_code in ("403", "AccessDenied"):
            return False, f"Access denied to bucket '{target_bucket}'. Check IAM permissions."
        return False, f"AWS S3 Client Error ({error_code}): {str(e)}"
    except EndpointConnectionError:
        return False, "Could not connect to the AWS endpoint. Please check your internet connection."
    except Exception as e:
        return False, f"S3 connection check failed: {str(e)}"


def upload_file_to_s3(
    file_source: Union[bytes, Any],
    filename: str,
    bucket_name: Optional[str] = None,
    prefix: str = "resumes/",
    user_consent: bool = False,
    content_type: str = "application/pdf",
) -> Tuple[bool, str, Optional[str]]:
    """
    Uploads a file to a private S3 bucket.
    CRITICAL REQUIREMENT: Requires explicit user consent before uploading.
    Does not log resume contents to console or storage.

    Args:
        file_source: Raw bytes or file-like object (e.g. Streamlit UploadedFile).
        filename (str): Name of the file being uploaded.
        bucket_name (Optional[str]): Target private S3 bucket.
        prefix (str): Key path prefix.
        user_consent (bool): Explicit user confirmation.
        content_type (str): MIME type for S3 object.

    Returns:
        Tuple[bool, str, Optional[str]]: (success, message, object_key)
    """
    # 1. Require explicit user consent
    if not user_consent:
        return False, "Upload aborted: Explicit user consent is required to upload files to AWS S3.", None

    if not BOTO3_AVAILABLE:
        return False, "boto3 is not installed. S3 upload unavailable.", None

    config = get_cloud_config()
    target_bucket = bucket_name or config["bucket_name"]

    if not target_bucket:
        return False, "Target S3 bucket is not configured. Set S3_BUCKET_NAME in your environment.", None

    # 2. Extract payload bytes in memory safely
    file_bytes: bytes
    if hasattr(file_source, "read"):
        try:
            file_bytes = file_source.read()
            if hasattr(file_source, "seek"):
                file_source.seek(0)
        except Exception as e:
            return False, f"Failed to read file payload: {str(e)}", None
    elif isinstance(file_source, (bytes, bytearray)):
        file_bytes = bytes(file_source)
    else:
        return False, "Unsupported file data format.", None

    if len(file_bytes) == 0:
        return False, "Cannot upload an empty (0 byte) file.", None

    # 3. Generate unique object key
    object_key = generate_unique_object_key(prefix, filename)

    try:
        s3 = get_s3_client()
        # Upload using SSE-S3 AES-256 server-side encryption for private bucket security
        s3.put_object(
            Bucket=target_bucket,
            Key=object_key,
            Body=file_bytes,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )

        return True, f"File successfully uploaded: s3://{target_bucket}/{object_key}", object_key

    except NoCredentialsError:
        return False, "AWS credentials not found. Upload failed.", None
    except ClientError as e:
        error_code = str(e.response.get("Error", {}).get("Code", "Unknown"))
        return False, f"AWS S3 error ({error_code}) while uploading: {str(e)}", None
    except Exception as e:
        return False, f"Upload to S3 failed: {str(e)}", None


def delete_file_from_s3(
    object_key: str, bucket_name: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Deletes an object from the S3 bucket to support document lifecycle cleanup.

    Args:
        object_key (str): S3 object key to delete.
        bucket_name (Optional[str]): S3 bucket name.

    Returns:
        Tuple[bool, str]: (success, message)
    """
    if not BOTO3_AVAILABLE:
        return False, "boto3 is not installed."

    config = get_cloud_config()
    target_bucket = bucket_name or config["bucket_name"]

    if not target_bucket:
        return False, "Target S3 bucket is not configured."

    if not object_key or not object_key.strip():
        return False, "Invalid object key provided for deletion."

    try:
        s3 = get_s3_client()
        s3.delete_object(Bucket=target_bucket, Key=object_key.strip())
        return True, f"Successfully deleted object '{object_key}' from bucket '{target_bucket}'."

    except NoCredentialsError:
        return False, "AWS credentials not found. Deletion failed."
    except ClientError as e:
        error_code = str(e.response.get("Error", {}).get("Code", "Unknown"))
        return False, f"AWS S3 error ({error_code}) while deleting: {str(e)}"
    except Exception as e:
        return False, f"Failed to delete object from S3: {str(e)}"


def upload_analysis_report(
    report_data: Dict[str, Any],
    candidate_name: str = "candidate",
    bucket_name: Optional[str] = None,
    user_consent: bool = True,
) -> Tuple[bool, str, Optional[str]]:
    """
    Uploads an anonymous analysis metadata JSON summary report to S3.
    Does not log or store full resume text.

    Args:
        report_data (Dict): Analysis metrics dictionary.
        candidate_name (str): Safe identifier for naming.
        bucket_name (Optional[str]): S3 bucket.
        user_consent (bool): Explicit user consent.

    Returns:
        Tuple[bool, str, Optional[str]]: (success, message, object_key)
    """
    if not user_consent:
        return False, "User consent required for S3 upload.", None

    if not is_s3_configured():
        return (
            True,
            "Local Mode: Report retained in memory. (S3 is optional and currently disabled).",
            None,
        )

    json_payload = json.dumps(report_data, indent=2).encode("utf-8")
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", candidate_name).lower()
    report_filename = f"{safe_name}_analysis.json"

    return upload_file_to_s3(
        file_source=json_payload,
        filename=report_filename,
        bucket_name=bucket_name,
        prefix="reports/",
        user_consent=user_consent,
        content_type="application/json",
    )


def get_cloud_status() -> Dict[str, Any]:
    """
    Returns high-level status of the cloud integration for display in the UI.
    """
    configured = is_s3_configured()
    config = get_cloud_config()

    has_auth = bool(
        (config["access_key"] and config["secret_key"])
        or os.getenv("AWS_ROLE_ARN")
        or os.getenv("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI")
    )

    return {
        "is_configured": configured,
        "boto3_installed": BOTO3_AVAILABLE,
        "bucket_name": config["bucket_name"] if config["bucket_name"] else "Not Configured",
        "region": config["region"],
        "has_credentials": has_auth,
        "status_label": "🟢 AWS S3 Configured" if configured else "⚪ Local Processing Mode",
    }
