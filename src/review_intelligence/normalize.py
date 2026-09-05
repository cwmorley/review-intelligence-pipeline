"""Deterministic value normalization with no inferred sentiment."""

from __future__ import annotations

import re
from typing import Any


LETTER_GRADES = {
    "A+": 1.00,
    "A": 0.95,
    "A-": 0.90,
    "B+": 0.87,
    "B": 0.83,
    "B-": 0.80,
    "C+": 0.77,
    "C": 0.73,
    "C-": 0.70,
    "D+": 0.67,
    "D": 0.63,
    "D-": 0.60,
    "F": 0.50,
}


def normalize_rating(value: Any, scale: Any = None) -> float | None:
    """Return a rating on [0, 1], or None when the value is not explicit."""
    if value is None or value == "":
        return None

    if isinstance(value, str):
        text = value.strip().upper()
        if text in LETTER_GRADES:
            return LETTER_GRADES[text]
        percent = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)\s*%", text)
        if percent:
            return _bounded(float(percent.group(1)) / 100.0)
        ratio = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)\s*/\s*([+-]?\d+(?:\.\d+)?)", text)
        if ratio:
            denominator = float(ratio.group(2))
            return None if denominator <= 0 else _bounded(float(ratio.group(1)) / denominator)
        try:
            value = float(text)
        except ValueError:
            return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if scale not in (None, ""):
        try:
            denominator = float(scale)
        except (TypeError, ValueError):
            return None
        return None if denominator <= 0 else _bounded(number / denominator)

    # A bare decimal in [0, 1] is already normalized. Larger bare values are
    # intentionally rejected because 4 could mean 4/5, 4/10, or four stars.
    return _bounded(number) if 0 <= number <= 1 else None


def is_favorable(normalized_rating: float | None, threshold: float = 0.8) -> bool | None:
    if normalized_rating is None:
        return None
    return normalized_rating >= threshold


def parse_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n"}:
        return False
    return None


def _bounded(value: float) -> float | None:
    return value if 0.0 <= value <= 1.0 else None

