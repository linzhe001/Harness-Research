"""Shared redaction helpers for external model review tooling."""

from __future__ import annotations

import re
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"sk-[A-Za-z0-9_-]{12,}"), "sk-<redacted>"),
    (
        re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)([\"'])[^\"'\n]*([\"'])"),
        r"\1\2<redacted>\3",
    ),
    (
        re.compile(
            r"(?i)(api[_-]?key\s*[:=]\s*)"
            r"(?!str\b|none\b|field\b|_|\(|os\.|getenv\b)"
            r"([A-Za-z0-9][A-Za-z0-9._~+/-]*"
            r"(?:secret|token|key|sk-)"
            r"[A-Za-z0-9._~+/-]*)"
        ),
        r"\1<redacted>",
    ),
    (
        re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[A-Za-z0-9._~+/-]+"),
        r"\1<redacted>",
    ),
)

DENIED_PATH_PARTS = {
    ".git",
    ".harness_hooks",
    ".auto_iterate",
}
DENIED_SUFFIXES = (
    ".pem",
    ".key",
    ".p12",
    ".pfx",
)
DENIED_FILENAME_PATTERNS = (
    ".env",
    ".env.*",
    "*config*.json",
    "*copilot*",
    "*.local.*",
    "providers.local.yaml",
    "providers.local.yml",
)


def redact_secrets(text: str) -> str:
    """Redact common API-key shapes from external review artifacts."""
    redacted = text
    for pattern, replacement in SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def redact_json(value: Any) -> Any:
    """Recursively redact string values in JSON-like artifacts."""
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, list):
        return [redact_json(item) for item in value]
    if isinstance(value, dict):
        return {str(key): redact_json(item) for key, item in value.items()}
    return value


def denied_review_path_reason(rel_path: str) -> str | None:
    """Return why a relative path should not be sent to external reviewers."""
    parts = set(Path(rel_path).parts)
    if parts & DENIED_PATH_PARTS:
        return "path is not reviewable"
    name = Path(rel_path).name
    if (
        any(fnmatchcase(name, pattern) for pattern in DENIED_FILENAME_PATTERNS)
        or rel_path.endswith(DENIED_SUFFIXES)
    ):
        return "path may contain local secrets"
    return None
