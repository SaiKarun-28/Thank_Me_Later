"""
Security and Secret Redaction Tests.
Proves that sentinel keys never appear in logs or responses.
"""
import io
import logging
from fastapi.testclient import TestClient

from app.utils.security import (
    active_secrets,
    register_secret,
    redact_text,
    SecretRedactingLoggingFilter,
    sanitize_url,
)


def test_sentinel_key_registration_and_redaction():
    """Verify that a registered sentinel key is completely scrubbed from text."""
    sentinel = "SENTINEL-998877-SECRET"
    register_secret(sentinel)
    
    text = f"Encountered error connecting with key: {sentinel}"
    redacted = redact_text(text)
    
    assert sentinel not in redacted
    assert "[REDACTED]" in redacted


def test_token_patterns_redaction():
    """Verify that standard token patterns are scrubbed even without explicit registration."""
    groq_key = "gsk_1234567890abcdef1234567890abcdef"
    gemini_key = "AIzaSyD-1234567890abcdef1234567890abc"
    bearer_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"

    text = f"Keys: groq={groq_key}, gemini={gemini_key}, auth={bearer_token}"
    redacted = redact_text(text)

    assert groq_key not in redacted
    assert gemini_key not in redacted
    assert bearer_token not in redacted
    assert redacted.count("[REDACTED]") == 3


def test_logging_filter_scrubs_sentinel(sentinel_key):
    """Verify that SecretRedactingLoggingFilter scrubs secrets in log output."""
    register_secret(sentinel_key)
    
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.addFilter(SecretRedactingLoggingFilter())
    
    test_logger = logging.getLogger("test_redaction")
    test_logger.handlers = [handler]
    test_logger.setLevel(logging.INFO)
    
    test_logger.info("Attempting authentication with %s", sentinel_key)
    handler.flush()
    
    log_content = log_capture.getvalue()
    assert sentinel_key not in log_content
    assert "[REDACTED]" in log_content


def test_validation_error_drops_input(client: TestClient, sentinel_key: str):
    """
    Verify that FastAPI RequestValidationError handler drops the 'input' field,
    guaranteeing that invalid payloads with sensitive values never echo them back.
    """
    # Send invalid type for request fields with sentinel key embedded in payload
    payload = {
        "provider": 12345,  # Invalid: expected string
        "model": "llama-3.3-70b-versatile",
        "api_key": sentinel_key,
    }
    
    response = client.post(
        "/settings/test",
        json=payload,
        headers={"X-LLM-Key": sentinel_key},
    )
    
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    
    # Inspect all error items in detail
    for error_item in data["detail"]:
        assert "input" not in error_item, "Validation error must never contain 'input' field!"
    
    # Entire response string must never contain sentinel key
    assert sentinel_key not in response.text


def test_sentinel_never_in_provider_failure_response(client: TestClient, sentinel_key: str):
    """
    Verify that when a provider connection fails, the sentinel key is never reflected
    in the response body or headers.
    """
    payload = {
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
    }
    
    # Send a sentinel key that will fail auth against upstream mock/real endpoint
    response = client.post(
        "/settings/test",
        json=payload,
        headers={"X-LLM-Key": sentinel_key},
    )
    
    # Sentinel key must NEVER be echoed anywhere in response body or headers
    assert sentinel_key not in response.text
    for header_name, header_val in response.headers.items():
        assert sentinel_key not in header_val


def test_sanitize_url_validation():
    """Verify HTTP/HTTPS enforcement, loopback/private IP rejection, and non-web scheme rejection."""
    # Valid URLs
    assert sanitize_url("https://jobs.lever.co/company/job-id") == "https://jobs.lever.co/company/job-id"
    assert sanitize_url("http://example.com/apply") == "http://example.com/apply"
    
    # Invalid schemes
    assert sanitize_url("javascript:alert(1)") is None
    assert sanitize_url("file:///etc/passwd") is None
    assert sanitize_url("ftp://server.com/job") is None
    assert sanitize_url("data:text/html,<script>") is None

    # Internal / private hostnames
    assert sanitize_url("http://localhost:8000/apply") is None
    assert sanitize_url("http://127.0.0.1:8000/apply") is None
    assert sanitize_url("http://0.0.0.0:8000/apply") is None
    assert sanitize_url("http://host.docker.internal:8000/apply") is None
    assert sanitize_url("http://192.168.1.1/apply") is None
    assert sanitize_url("http://10.0.0.1/apply") is None
    assert sanitize_url("http://169.254.169.254/latest/meta-data") is None

    # Empty / None
    assert sanitize_url("") is None
    assert sanitize_url(None) is None
