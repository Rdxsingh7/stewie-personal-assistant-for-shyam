"""
Stewie Text Processing Utilities — Common text helpers.
"""

from __future__ import annotations

import re


def clean_text(text: str) -> str:
    """Remove excessive whitespace and normalize text."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def truncate(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """Truncate text to a maximum length."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def extract_numbers(text: str) -> list[int]:
    """Extract all integers from a text string."""
    return [int(n) for n in re.findall(r"\d+", text)]


def normalize_app_name(name: str) -> str:
    """
    Normalize an application name for matching.

    Strips common suffixes, lowercases, and removes extra whitespace.
    """
    name = name.lower().strip()
    # Remove common suffixes
    for suffix in [".exe", " app", " application"]:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return name.strip()
