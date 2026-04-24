"""Shared secret-pattern regexes, reused by several rules."""

from __future__ import annotations

import re

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Anthropic API key", re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")),
    ("OpenAI API key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")),
    ("Stripe live key", re.compile(r"sk_live_[A-Za-z0-9]{24,}")),
    ("Slack bot token", re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}")),
    ("SendGrid API key", re.compile(r"SG\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}")),
    ("Google API key", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("HuggingFace token", re.compile(r"hf_[A-Za-z0-9]{30,}")),
    ("Twilio auth token", re.compile(r"SK[0-9a-fA-F]{32}")),
    ("generic PEM block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
)

PLACEHOLDER_SUBSTRINGS = (
    "your-api-key",
    "your-key-here",
    "your_api_key",
    "your_key_here",
    "your-token-here",
    "replace-me",
    "replace_me",
    "placeholder",
    "xxxxxxxx",
    "<your",
    "<api-key>",
    "<api_key>",
    "<token>",
)


def looks_like_secret(value: str) -> str | None:
    """Return a human label for the kind of secret if one is detected, else None."""
    if not isinstance(value, str):
        return None
    for label, pattern in SECRET_PATTERNS:
        if pattern.search(value):
            return label
    return None


def looks_like_placeholder(value: str) -> bool:
    if not isinstance(value, str):
        return False
    lower = value.strip().lower()
    return any(substr in lower for substr in PLACEHOLDER_SUBSTRINGS)
