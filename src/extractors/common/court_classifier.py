"""Classify Pakistani courts: name extraction, level, province, court code.

Single responsibility: raw text → standardized court identifiers.
Reused by all court-specific pipelines and Tier A extractors.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional


class CourtCode(str, Enum):
    """Standardized court codes used across Qdrant point IDs and payloads."""

    SC = "SC"
    LHC = "LHC"
    SHC = "SHC"
    IHC = "IHC"
    PHC = "PHC"
    BHC = "BHC"
    FSC = "FSC"
    ATC = "ATC"
    SESSIONS = "SESSIONS"
    DISTRICT = "DISTRICT"
    UNKNOWN = "UNKNOWN"


class CourtLevel(str, Enum):
    SUPREME_COURT = "supreme_court"
    HIGH_COURT = "high_court"
    SPECIAL_COURT = "special_court"
    FEDERAL_SHARIAT = "federal_shariat"
    ANTI_TERRORISM_COURT = "anti_terrorism_court"
    TRIAL_COURT = "trial_court"


class Province(str, Enum):
    PUNJAB = "punjab"
    SINDH = "sindh"
    KPK = "kpk"
    BALOCHISTAN = "balochistan"
    ISLAMABAD = "islamabad"
    FEDERAL = "federal"


# Court name patterns ordered by specificity
_COURT_NAMES = [
    "Supreme Court of Pakistan",
    "Lahore High Court",
    "Sindh High Court",
    "Islamabad High Court",
    "Peshawar High Court",
    "Balochistan High Court",
    "Federal Shariat Court",
    r"Anti[- ]Terrorism Court",
]

# Map normalized court names to codes
_NAME_TO_CODE: dict[str, CourtCode] = {
    "supreme court": CourtCode.SC,
    "lahore high court": CourtCode.LHC,
    "sindh high court": CourtCode.SHC,
    "islamabad high court": CourtCode.IHC,
    "peshawar high court": CourtCode.PHC,
    "balochistan high court": CourtCode.BHC,
    "federal shariat court": CourtCode.FSC,
    "anti-terrorism court": CourtCode.ATC,
    "anti terrorism court": CourtCode.ATC,
}


def extract_court_name(text: str) -> Optional[str]:
    """Extract court name from judgment header (first 2000 chars)."""
    header = text[:2000]
    for court in _COURT_NAMES:
        m = re.search(court, header, re.IGNORECASE)
        if m:
            return m.group(0)

    # Fallback: "IN THE SUPREME COURT" pattern
    m = re.search(
        r"IN\s+THE\s+([\w\s]+COURT[\w\s]*?)(?:\n|$)", header, re.IGNORECASE
    )
    if m:
        return m.group(1).strip()
    return None


def classify_court_code(court_name: Optional[str] = None, text: str = "") -> CourtCode:
    """Map court name or text to standardized court code.

    Args:
        court_name: Extracted court name (preferred).
        text: Full text to search if court_name is None.
    """
    source = (court_name or text).lower()
    for key, code in _NAME_TO_CODE.items():
        if key in source:
            return code

    if "session" in source:
        return CourtCode.SESSIONS
    if "district" in source:
        return CourtCode.DISTRICT
    return CourtCode.UNKNOWN


def classify_court_level(court_name: Optional[str] = None, text: str = "") -> Optional[CourtLevel]:
    """Classify court into hierarchy level."""
    source = (court_name or text).lower()
    if "supreme" in source:
        return CourtLevel.SUPREME_COURT
    if "high court" in source:
        return CourtLevel.HIGH_COURT
    if "anti" in source and "terrorism" in source:
        return CourtLevel.ANTI_TERRORISM_COURT
    if "shariat" in source:
        return CourtLevel.FEDERAL_SHARIAT
    if "session" in source or "trial" in source:
        return CourtLevel.TRIAL_COURT
    if "special" in source:
        return CourtLevel.SPECIAL_COURT
    return None


def classify_province(court_name: Optional[str] = None, text: str = "") -> Optional[Province]:
    """Classify province/jurisdiction from court name or text."""
    source = (court_name or text).lower()
    if "lahore" in source or "punjab" in source:
        return Province.PUNJAB
    if "sindh" in source or "karachi" in source:
        return Province.SINDH
    if "peshawar" in source or "kpk" in source or "khyber" in source:
        return Province.KPK
    if "balochistan" in source or "quetta" in source:
        return Province.BALOCHISTAN
    if "islamabad" in source:
        return Province.ISLAMABAD
    if "supreme" in source or "federal" in source:
        return Province.FEDERAL
    return None
