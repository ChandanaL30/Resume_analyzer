"""
test_cloud_storage.py
=====================
Automated unit tests for cloud_storage.py using unittest.mock.
Tests Amazon S3 integration without requiring an AWS account or active internet connection.
Verifies explicit consent checks, unique key generation, upload/delete functions,
and error handling.
"""

from unittest.mock import MagicMock, patch
import pytest
from botocore.exceptions import ClientError, NoCredentialsError

from cloud_storage import (
    MODE_LOCAL,
    MODE_S3,
    get_cloud_config,
    is_s3_configured,
    generate_unique_object_key,
    test_s3_connection as check_s3_connection,
    upload_file_to_s3,
    delete_file_from_s3,
    upload_analysis_report,
    get_cloud_status,
)


def test_get_cloud_config_reads_env():
    """Verify cloud configuration reads standard environment variables."""
    with patch.dict(
        "os.environ",
        {
            "AWS_REGION": "us-west-2",
            "S3_BUCKET_NAME": "test-resume-bucket",
            "AWS_ACCESS_KEY_ID": "mock-access-key",
            "AWS_SECRET_ACCESS_KEY": "mock-secret-key",
        },
    ):
        config = get_cloud_config()
        assert config["region"] == "us-west-2"
        assert config["bucket_name"] == "test-resume-bucket"
        assert config["access_key"] == "mock-access-key"
        assert config["secret_key"] == "mock-secret-key"


def test_is_s3_configured():
    """Verify is_s3_configured checks for bucket name."""
    with patch.dict("os.environ", {"S3_BUCKET_NAME": "my-bucket"}, clear=True):
        assert is_s3_configured() is True

    with patch.dict("os.environ", {}, clear=True):
        assert is_s3_configured() is False


def test_generate_unique_object_key_uniqueness():
    """Verify that generated S3 keys are unique and include sanitized filenames."""
    key1 = generate_unique_object_key("resumes/", "my resume (final) @2026.pdf")
    key2 = generate_unique_object_key("resumes/", "my resume (final) @2026.pdf")

    # Keys must be unique (UUID token prevents collisions)
    assert key1 != key2
    assert key1.startswith("resumes/")
    assert key1.endswith(".pdf")
    # Must be sanitized (no spaces or parentheses)
    assert "(" not in key1 and ")" not in key1 and " " not in key1


def test_upload_file_to_s3_requires_explicit_consent():
    """CRITICAL REQUIREMENT: Upload must be rejected if user_consent is False."""
    sample_bytes = b"%PDF-1.4 Mock resume content"

    success, msg, key = upload_file_to_s3(
        file_source=sample_bytes,
        filename="resume.pdf",
        bucket_name="my-bucket",
        user_consent=False,  # No consent
    )

    assert success is False
    assert "explicit user consent is required" in msg.lower()
    assert key is None


def test_upload_file_to_s3_mocked_success():
    """Verify successful S3 upload when consent is granted."""
    sample_bytes = b"%PDF-1.4 Mock resume content for test"
    mock_s3 = MagicMock()

    with patch("cloud_storage.get_s3_client", return_value=mock_s3):
        with patch.dict("os.environ", {"S3_BUCKET_NAME": "private-resume-bucket"}):
            success, msg, object_key = upload_file_to_s3(
                file_source=sample_bytes,
                filename="candidate_resume.pdf",
                user_consent=True,
            )

            assert success is True
            assert object_key is not None
            assert object_key.startswith("resumes/")
            assert "s3://private-resume-bucket/" in msg

            # Verify put_object was called with ServerSideEncryption AES256
            mock_s3.put_object.assert_called_once()
            call_kwargs = mock_s3.put_object.call_args[1]
            assert call_kwargs["Bucket"] == "private-resume-bucket"
            assert call_kwargs["Key"] == object_key
            assert call_kwargs["Body"] == sample_bytes
            assert call_kwargs["ServerSideEncryption"] == "AES256"


def test_upload_file_to_s3_mocked_no_credentials_error():
    """Verify graceful handling when AWS credentials are missing during upload."""
    mock_s3 = MagicMock()
    mock_s3.put_object.side_effect = NoCredentialsError()

    with patch("cloud_storage.get_s3_client", return_value=mock_s3):
        with patch.dict("os.environ", {"S3_BUCKET_NAME": "private-resume-bucket"}):
            success, msg, object_key = upload_file_to_s3(
                file_source=b"%PDF-1.4 test",
                filename="resume.pdf",
                user_consent=True,
            )

            assert success is False
            assert "credentials not found" in msg.lower()
            assert object_key is None


def test_upload_file_to_s3_mocked_client_error():
    """Verify graceful handling when S3 returns an AccessDenied error."""
    mock_s3 = MagicMock()
    error_response = {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}
    mock_s3.put_object.side_effect = ClientError(error_response, "PutObject")

    with patch("cloud_storage.get_s3_client", return_value=mock_s3):
        with patch.dict("os.environ", {"S3_BUCKET_NAME": "private-resume-bucket"}):
            success, msg, object_key = upload_file_to_s3(
                file_source=b"%PDF-1.4 test",
                filename="resume.pdf",
                user_consent=True,
            )

            assert success is False
            assert "accessdenied" in msg.lower()
            assert object_key is None


def test_delete_file_from_s3_mocked_success():
    """Verify S3 object deletion succeeds."""
    mock_s3 = MagicMock()

    with patch("cloud_storage.get_s3_client", return_value=mock_s3):
        with patch.dict("os.environ", {"S3_BUCKET_NAME": "private-resume-bucket"}):
            success, msg = delete_file_from_s3("resumes/test_object_123.pdf")

            assert success is True
            assert "successfully deleted" in msg.lower()
            mock_s3.delete_object.assert_called_once_with(
                Bucket="private-resume-bucket", Key="resumes/test_object_123.pdf"
            )


def test_delete_file_from_s3_mocked_client_error():
    """Verify graceful handling when S3 delete returns an error."""
    mock_s3 = MagicMock()
    error_response = {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}}
    mock_s3.delete_object.side_effect = ClientError(error_response, "DeleteObject")

    with patch("cloud_storage.get_s3_client", return_value=mock_s3):
        with patch.dict("os.environ", {"S3_BUCKET_NAME": "private-resume-bucket"}):
            success, msg = delete_file_from_s3("resumes/non_existent.pdf")

            assert success is False
            assert "nosuchkey" in msg.lower()


def test_test_s3_connection_mocked_success():
    """Verify S3 connection testing passes when bucket is reachable."""
    mock_s3 = MagicMock()

    with patch("cloud_storage.get_s3_client", return_value=mock_s3):
        with patch.dict("os.environ", {"S3_BUCKET_NAME": "my-private-bucket"}):
            success, msg = check_s3_connection()

            assert success is True
            assert "successfully connected" in msg.lower()
            mock_s3.head_bucket.assert_called_once_with(Bucket="my-private-bucket")


def test_test_s3_connection_mocked_404():
    """Verify S3 connection testing informs user when bucket does not exist."""
    mock_s3 = MagicMock()
    error_response = {"Error": {"Code": "404", "Message": "Not Found"}}
    mock_s3.head_bucket.side_effect = ClientError(error_response, "HeadBucket")

    with patch("cloud_storage.get_s3_client", return_value=mock_s3):
        with patch.dict("os.environ", {"S3_BUCKET_NAME": "missing-bucket"}):
            success, msg = check_s3_connection()

            assert success is False
            assert "does not exist" in msg.lower()


def test_upload_analysis_report_mocked():
    """Verify uploading an anonymous report JSON summary to S3."""
    mock_s3 = MagicMock()
    sample_report = {
        "candidate_name": "Test Candidate",
        "match_score": 85.0,
        "matched_skills": ["Python", "AWS"],
    }

    with patch("cloud_storage.get_s3_client", return_value=mock_s3):
        with patch.dict("os.environ", {"S3_BUCKET_NAME": "private-resume-bucket"}):
            success, msg, key = upload_analysis_report(
                sample_report, candidate_name="Jane Doe", user_consent=True
            )

            assert success is True
            assert key is not None
            assert key.startswith("reports/")
            assert key.endswith(".json")
            mock_s3.put_object.assert_called_once()


def test_local_mode_operates_cleanly_without_aws():
    """Verify that when S3 is not configured, local mode remains functional."""
    with patch.dict("os.environ", {}, clear=True):
        status = get_cloud_status()
        assert status["is_configured"] is False
        assert status["status_label"] == "⚪ Local Processing Mode"

        # Connection check returns informative local message rather than crashing
        connected, msg = check_s3_connection()
        assert connected is False
        assert "local processing mode" in msg.lower()
