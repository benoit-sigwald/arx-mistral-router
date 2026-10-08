"""Tests for sanitization, secret redaction, and log compaction."""

from arx_router.sanitization import (
    bound_and_sanitize,
    compact_logs,
    redact_secrets,
    strip_ansi,
)


def test_redact_private_keys():
    raw = "Header\n-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0\n-----END RSA PRIVATE KEY-----\nFooter"
    redacted = redact_secrets(raw)
    assert "[REDACTED_PRIVATE_KEY]" in redacted
    assert "MIIEowIBAAKCAQEA0" not in redacted


def test_redact_bearer_tokens():
    raw = "Authorization: Bearer super_secret_token_1234567890_abc"
    redacted = redact_secrets(raw)
    assert "[REDACTED_BEARER_TOKEN]" in redacted
    assert "super_secret_token_1234567890_abc" not in redacted


def test_redact_db_credentials():
    raw = "Database connected to postgres://admin:SuperSecretPass123@db.internal:5432/arxdb"
    redacted = redact_secrets(raw)
    assert "[REDACTED_PASSWORD]" in redacted
    assert "SuperSecretPass123" not in redacted


def test_strip_ansi():
    ansi_log = "\x1B[31mERROR\x1B[0m: \x1B[1mFailed\x1B[0m to connect"
    clean = strip_ansi(ansi_log)
    assert clean == "ERROR: Failed to connect"


def test_compact_logs_deduplication():
    repeating_logs = "\n".join(["2026-10-08 10:00:00 Connection retry..."] * 20)
    compacted = compact_logs(repeating_logs, max_repeat=3)
    assert "repeated 20 times" in compacted
    assert compacted.count("Connection retry...") < 10


def test_bound_and_sanitize_truncation():
    huge_text = "A" * 500
    bounded, was_truncated = bound_and_sanitize(huge_text, max_chars=100)
    assert was_truncated is True
    assert len(bounded) > 100  # Includes notice
    assert "[NOTICE: Input truncated to 100 chars" in bounded
