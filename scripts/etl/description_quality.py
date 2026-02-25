"""Description quality validation for ETL output items."""

from __future__ import annotations

import re


PLACEHOLDER_PATTERNS = [
    re.compile(r"-\s*technology\s+with\s+\d+\s+stars", re.IGNORECASE),
]


def is_valid_description(text: str | None) -> bool:
    """Validate description - relaxed to allow more items through"""
    if not text or not text.strip():
        return False

    value = text.strip()
    lowered = value.lower()
    if lowered in {"unknown", "n/a", "na", "none", "null"}:
        return False

    for pattern in PLACEHOLDER_PATTERNS:
        if pattern.search(value):
            return False

    # Relaxed: Only reject obvious placeholders, allow short/generic descriptions
    # A description is valid if it has at least 10 characters
    if len(value) < 10:
        return False

    return True
