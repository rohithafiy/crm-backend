"""
Phone normalization helper

Provides a simple normalization function used for duplicate detection and
indexing. Normalization removes all non-digit characters and returns the
digits-only string or None when empty.
"""
import re
from typing import Optional


_NON_DIGIT = re.compile(r"\D+")


def normalize_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    s = str(phone).strip()
    if not s:
        return None
    digits = _NON_DIGIT.sub("", s)
    return digits or None
