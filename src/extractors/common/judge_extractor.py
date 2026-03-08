"""Extract and normalize Pakistani judge names from judgment text.

Single responsibility: judgment text → list of judge names.
Handles "PRESENT: Mr. Justice X" blocks and "Hon'ble" patterns.
"""

from __future__ import annotations

import re


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
    judges: set[str] = set()
    header = re.sub(r"\s+", " ", text[:3000])

    # Pattern 1: "Mr./Mrs./Ms. Justice <Name>"
    for m in re.finditer(
        r"(?:Mr\.|Mrs\.|Ms\.)?\s*Justice\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,5})",
        header,
    ):
        name = _clean_name(m.group(1).strip())
        if name:
            judges.add(name)

    # Pattern 2: "PRESENT: ..." block
    present_block = re.search(
        r"PRESENT[:\s]+(.+?)(?:\n\n|\n[A-Z])",
        text[:3000],
        re.DOTALL | re.IGNORECASE,
    )
    if present_block:
        normalized = re.sub(r"\s+", " ", present_block.group(1))
        for m in re.finditer(
            r"Justice\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,5})", normalized
        ):
            name = _clean_name(m.group(1).strip())
            if name:
                judges.add(name)

    # Pattern 3: "Hon'ble Justice <Name>"
    for m in re.finditer(
        r"Hon['\u2019]?ble\s+(?:Mr\.\s+)?Justice\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,5})",
        header,
    ):
        name = _clean_name(m.group(1).strip())
        if name:
            judges.add(name)

    return sorted(judges)


def _clean_name(name: str) -> str | None:
    """Remove trailing stop words and validate minimum length."""
    parts = name.split()
    while parts and parts[-1] in _STOP_WORDS:
        parts.pop()
    if len(parts) < 2:
        return None
    return " ".join(parts)
