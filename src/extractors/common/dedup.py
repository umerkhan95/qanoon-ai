"""Cross-source deduplication for judgment texts.

Single responsibility: detect duplicate judgments across ingestion runs.
Uses SHA-256 of normalized text for exact-match dedup, plus case_number
matching for near-duplicates from different sources.
"""

from __future__ import annotations

import hashlib
import logging
import re



logger = logging.getLogger(__name__)


def text_hash(text: str) -> str:
    """Compute SHA-256 hash of normalized judgment text.

    Normalizes whitespace and lowercases before hashing so minor
    formatting differences between sources don't create false negatives.

    Raises ValueError for empty/whitespace-only text to prevent
    false duplicate collisions from failed extractions.
    """
    if not text or not text.strip():
        raise ValueError("Cannot hash empty text — likely a failed extraction")
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def normalize_case_number(case_number: str) -> str:
    """Normalize case number for cross-source matching.

    Different sources format the same case differently:
    - "Crl. A. 310/2006" vs "Criminal Appeal No. 310 of 2006"
    - "CRL.A.310_2006" vs "Crl.A. 310/2006"

    Normalizes to: uppercase letters + digits only, no spaces/punctuation.
    """
    if not case_number:
        return ""
    # Strip everything except alphanumeric
    stripped = re.sub(r"[^A-Za-z0-9]", "", case_number).upper()
    return stripped


def is_duplicate_text(
    text: str,
    existing_hashes: set[str],
) -> bool:
    """Check if judgment text is a duplicate of any previously ingested text.

    Args:
        text: Full judgment text.
        existing_hashes: Set of SHA-256 hashes from previously ingested judgments.

    Returns:
        True if text hash exists in the set.
    """
    h = text_hash(text)
    return h in existing_hashes


def is_duplicate_case(
    case_number: str,
    existing_case_numbers: set[str],
) -> bool:
    """Check if case number matches any previously ingested case.

    Uses normalized case numbers for fuzzy matching.
    """
    normalized = normalize_case_number(case_number)
    if not normalized:
        return False
    return normalized in existing_case_numbers


def find_near_duplicates(
    text: str,
    case_number: str,
    existing_hashes: set[str],
    existing_case_numbers: set[str],
) -> dict[str, bool]:
    """Check for both exact and near-duplicate matches.

    Returns:
        Dict with "exact_duplicate" and "case_number_match" booleans.
    """
    return {
        "exact_duplicate": is_duplicate_text(text, existing_hashes),
        "case_number_match": is_duplicate_case(case_number, existing_case_numbers),
    }
