"""Extract and normalize Pakistani judge names from judgment text.

Single responsibility: judgment text → list of judge names.
Handles "PRESENT: Mr. Justice X" blocks and "Hon'ble" patterns.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


_STOP_WORDS = {
    "Mr", "Mrs", "Ms", "Criminal", "Civil", "Appeal", "Petition",
    "Application", "Case", "No", "Original", "Suo", "Motu",
    "Appeals", "Cr", "Crl", "The", "And", "In", "For", "Of",
    "Chief", "Acting", "Ad", "Hoc",
}


def extract_judge_names(text: str) -> list[str]:
    """Extract judge names from judgment header.

    Searches first 3000 chars for:
    - "Mr. Justice <Name>" patterns
    - "PRESENT: ..." blocks
    - "Hon'ble Justice <Name>" patterns

    Returns sorted, deduplicated list of cleaned names.
    """
    if not text:
        return []
    judges: set[str] = set()
    header = re.sub(r"\s+", " ", text[:3000])

    # Name token: matches Title Case ("Iftikhar") and ALL CAPS ("IFTIKHAR")
    _NAME_TOKEN = r"[A-Z][a-zA-Z]+"
    _NAME_SEQ = rf"{_NAME_TOKEN}(?:\s+{_NAME_TOKEN}){{1,5}}"

    # Pattern 1: "Mr./MR./Mrs./Ms. Justice <Name>"
    for m in re.finditer(
        rf"(?:MR\.|Mr\.|MRS\.|Mrs\.|MS\.|Ms\.)?\s*(?:JUSTICE|Justice)\s+({_NAME_SEQ})",
        header,
    ):
        name = _clean_name(_title_case(m.group(1).strip()))
        if name:
            judges.add(name)

    # Pattern 2: "PRESENT: ..." block (end at double newline, section start, or end of text)
    present_block = re.search(
        r"PRESENT[:\s]+(.+?)(?:\n\n|\n[A-Z]|$)",
        text[:3000],
        re.DOTALL | re.IGNORECASE,
    )
    if present_block:
        normalized = re.sub(r"\s+", " ", present_block.group(1))
        for m in re.finditer(
            rf"(?:JUSTICE|Justice)\s+({_NAME_SEQ})", normalized
        ):
            name = _clean_name(_title_case(m.group(1).strip()))
            if name:
                judges.add(name)

    # Pattern 3: "Hon'ble Justice <Name>"
    for m in re.finditer(
        rf"Hon['\u2019]?ble\s+(?:(?:Mr|MR)\.\s+)?(?:JUSTICE|Justice)\s+({_NAME_SEQ})",
        header,
    ):
        name = _clean_name(_title_case(m.group(1).strip()))
        if name:
            judges.add(name)

    if not judges and len(text) > 500:
        logger.info("No judge names found in %d-char text: %.80s", len(text), header[:80])
    return sorted(judges)


def _title_case(name: str) -> str:
    """Normalize ALL CAPS names to Title Case for consistent dedup."""
    if name.isupper():
        return name.title()
    return name


def _clean_name(name: str) -> str | None:
    """Remove trailing stop words and validate minimum length."""
    parts = name.split()
    while parts and parts[-1] in _STOP_WORDS:
        parts.pop()
    if len(parts) < 2:
        return None
    return " ".join(parts)
