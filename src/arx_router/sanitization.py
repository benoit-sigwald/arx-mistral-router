"""Sanitization, secret redaction, log compaction, and deterministic input pre-processing."""

import re
from typing import Tuple

# Common sensitive pattern regexes
RE_BEARER = re.compile(r"(?i)(bearer\s+)([a-zA-Z0-9_\-\.]{16,})")
RE_API_KEY = re.compile(r"(?i)(api[_-]?key|secret|token|password|auth[_-]?token|client[_-]?secret)[\s=:\"']+([a-zA-Z0-9_\-\.]{12,})")
RE_PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+PRIVATE KEY-----")
RE_MISTRAL_KEY = re.compile(r"(?i)(mistral[_-]?api[_-]?key|mistral[_-]?token)[\s=:\"']+([a-zA-Z0-9_\-\.]{16,})")
RE_DB_CONN = re.compile(r"(?i)(postgres|postgresql|mysql|oracle|mongodb):\/\/[^:\/\s]+:([^@\/\s]+)@")
RE_ANSI = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def redact_secrets(text: str) -> str:
    """Redact known API keys, tokens, and private keys from inputs and outputs."""
    if not text:
        return text

    # Redact private keys
    text = RE_PRIVATE_KEY.sub("[REDACTED_PRIVATE_KEY]", text)
    # Redact DB credentials
    text = RE_DB_CONN.sub(r"\1://[USER]:[REDACTED_PASSWORD]@", text)
    # Redact Bearer tokens
    text = RE_BEARER.sub(r"\1[REDACTED_BEARER_TOKEN]", text)
    # Redact Mistral / generic API keys
    text = RE_MISTRAL_KEY.sub(r"\1: [REDACTED_MISTRAL_KEY]", text)
    text = RE_API_KEY.sub(r"\1: [REDACTED_SECRET]", text)

    return text


def strip_ansi(text: str) -> str:
    """Strip ANSI escape sequences from logs or text."""
    if not text:
        return text
    return RE_ANSI.sub("", text)


def compact_logs(logs: str, max_repeat: int = 3) -> str:
    """
    Compact verbose and repeating log lines to save LLM tokens.
    Replaces 4+ identical contiguous lines with a summary tag.
    """
    if not logs:
        return logs

    cleaned = strip_ansi(logs)
    lines = cleaned.splitlines()
    if not lines:
        return ""

    compacted = []
    current_line = None
    repeat_count = 0

    for line in lines:
        # Strip timestamps or common log prefixes for repetition comparison
        norm_line = re.sub(r"^\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?\s*", "", line).strip()
        
        if norm_line == current_line:
            repeat_count += 1
        else:
            if repeat_count > max_repeat:
                compacted.append(f"... [repeated {repeat_count} times: {current_line[:120]}]")
            elif repeat_count > 0:
                compacted.extend([current_line] * repeat_count)

            current_line = norm_line
            repeat_count = 1
            compacted.append(line)

    if repeat_count > max_repeat:
        compacted.append(f"... [repeated {repeat_count} times: {current_line[:120]}]")
    elif repeat_count > 1:
        compacted.extend([current_line] * (repeat_count - 1))

    return "\n".join(compacted)


def bound_and_sanitize(text: str, max_chars: int = 32000, context_type: str = "text") -> Tuple[str, bool]:
    """
    Apply sanitization and enforce strict character bounds.
    Returns (sanitized_text, is_truncated).
    """
    if not text:
        return "", False

    sanitized = redact_secrets(text)
    if context_type == "logs":
        sanitized = compact_logs(sanitized)
    else:
        sanitized = strip_ansi(sanitized)

    if len(sanitized) > max_chars:
        truncated = sanitized[:max_chars] + f"\n\n[NOTICE: Input truncated to {max_chars} chars to protect token budget]"
        return truncated, True

    return sanitized, False
