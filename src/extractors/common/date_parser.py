"""Parse Pakistani legal date formats from judgment text."""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

# Pakistani judgments use many date formats:
# "1st January, 2023", "01.01.2023", "January 1, 2023", "1-1-2023",
# "dated 01-01-2023", "on 1.1.2023", "1st day of January 2023"

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9,
    "oct": 10, "nov": 11, "dec": 12,
}

# "1st January, 2023" or "1st day of January 2023"
_PAT_DMY_LONG = re.compile(
    r"(\d{1,2})(?:st|nd|rd|th)?\s+(?:day\s+of\s+)?(\w+)[,.]?\s+(\d{4})",
    re.IGNORECASE,
)

# "January 1, 2023"
_PAT_MDY_LONG = re.compile(
    r"(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?[,.]?\s+(\d{4})",
    re.IGNORECASE,
)

# "01.01.2023" or "01-01-2023" or "01/01/2023"
_PAT_NUMERIC = re.compile(
    r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})"
)

# "2023-01-01" (ISO)
_PAT_ISO = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})"
)


def parse_date(text: str) -> Optional[date]:
    """Try to parse a single date string into a date object."""
    text = text.strip()

    # ISO format
    m = _PAT_ISO.search(text)
    if m:
        return _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # "1st January, 2023"
    m = _PAT_DMY_LONG.search(text)
    if m:
        month = MONTHS.get(m.group(2).lower())
        if month:
            return _safe_date(int(m.group(3)), month, int(m.group(1)))

    # "January 1, 2023"
    m = _PAT_MDY_LONG.search(text)
    if m:
        month = MONTHS.get(m.group(1).lower())
        if month:
            return _safe_date(int(m.group(3)), month, int(m.group(2)))

    # "01.01.2023" — assume DD.MM.YYYY (Pakistani convention)
    m = _PAT_NUMERIC.search(text)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            return _safe_date(y, mo, d)

    return None


def find_all_dates(text: str) -> list[tuple[str, date]]:
    """Find all date strings in text with their parsed values."""
    results = []
    for pat in [_PAT_ISO, _PAT_DMY_LONG, _PAT_MDY_LONG, _PAT_NUMERIC]:
        for m in pat.finditer(text):
            parsed = parse_date(m.group(0))
            if parsed:
                results.append((m.group(0), parsed))
    return results


def _safe_date(year: int, month: int, day: int) -> Optional[date]:
    """Create date or return None if invalid."""
    try:
        return date(year, month, day)
    except ValueError:
        return None
