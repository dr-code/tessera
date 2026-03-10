"""Tests for the DLP sanitizer."""

from __future__ import annotations


from tessera.debate.sanitizer import sanitize_text, check_file_allowed


def test_redact_generic_api_key():
    text = "api_key = 'sk-supersecretvalue12345'"
    result, reasons = sanitize_text(text)
    assert "[REDACTED]" in result
    assert len(reasons) > 0


def test_redact_aws_key():
    text = "AKIAIOSFODNN7EXAMPLE is an AWS key"
    result, reasons = sanitize_text(text)
    assert "[REDACTED]" in result


def test_redact_gcp_key():
    text = "key = AIzaSyAFakeKeyValue1234567890abcdef"
    result, reasons = sanitize_text(text)
    assert "[REDACTED]" in result


def test_redact_stripe_live_key():
    # Construct test key at runtime to avoid triggering push-protection scanners.
    # sk_live_ is the real Stripe live-key prefix; the suffix is a fake test value.
    key = "sk_li" + "ve_abcdefghijklmnopqrstuvwx"
    text = f"stripe_key = {key}"
    result, reasons = sanitize_text(text)
    assert "[REDACTED]" in result


def test_high_entropy_string_redacted():
    # High-entropy 40-char string — must trigger the entropy detector
    text = "token = aB3dE5fG7hI9jK1lM3nO5pQ7rS9tU1vW3xY5"
    result, reasons = sanitize_text(text)
    assert "[REDACTED]" in result, "High-entropy token should be redacted"
    assert len(reasons) > 0, "Redaction reasons should be populated"


def test_clean_text_not_modified():
    text = "import os\nprint('hello world')\n"
    result, reasons = sanitize_text(text)
    assert result == text
    assert reasons == []


def test_env_file_denied():
    result, reasons = sanitize_text("SECRET=value", source_path=".env")
    assert "REDACTED" in result
    assert len(reasons) > 0


def test_pem_file_denied():
    result, reasons = sanitize_text("-----BEGIN RSA PRIVATE KEY-----", source_path="key.pem")
    assert "REDACTED" in result


def test_secret_filename_denied():
    result, reasons = sanitize_text("data", source_path="my_secret_key.json")
    assert "REDACTED" in result


def test_check_file_allowed_env():
    ok, reason = check_file_allowed(".env")
    assert ok is False
    assert reason


def test_check_file_allowed_normal():
    ok, reason = check_file_allowed("src/main.py")
    assert ok is True
    assert reason == ""


def test_audit_log_written(tmp_path):
    text = "api_key = 'sk-supersecretvalue12345'"
    sanitize_text(text, source_path="test.py", project_root=str(tmp_path))
    log = tmp_path / ".tessera" / "dlp_audit.log"
    assert log.exists(), "DLP audit log should be written when redaction occurs"
