"""Parse Pakistani Supreme Court judgments into structural sections.

Single responsibility: raw judgment text → list of JudgmentSection objects.
Uses regex-based heuristics tuned to Pakistani SC judgment structure:
  Header → ORDER/JUDGMENT marker → Body (numbered paragraphs) → Disposition

Pakistani SC judgments have NO explicit section headings. Structure is conveyed
through numbered paragraphs and narrative flow. The ORDER/JUDGMENT marker is
the most reliable boundary (found in 10/10 sample documents).
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class SectionType(str, Enum):
    HEADER = "header"
    BODY = "body"
    DISPOSITION = "disposition"


class JudgmentSection(BaseModel):
    """A structural section of a parsed judgment."""

    section_type: SectionType
    text: str
    paragraph_numbers: list[int] = []
    start_char: int = 0
    end_char: int = 0


# Regex patterns for structural markers
_JUDGMENT_MARKER = re.compile(
    r"^\s*(?:J\s*U\s*D\s*G\s*M\s*E\s*N\s*T|O\s*R\s*D\s*E\s*R|JUDGMENT|ORDER)\s*$",
    re.MULTILINE,
)

# Numbered paragraph: "2.", "2.\t", "12. " at start of line
_NUMBERED_PARA = re.compile(r"^\s*(\d{1,3})\.\s", re.MULTILINE)

# Disposition markers — common phrases signaling the end of reasoning
_DISPOSITION_MARKERS = [
    r"(?:appeal|petition|application|case)\s+is\s+(?:hereby\s+)?(?:dismissed|allowed|disposed)",
    r"ordered\s+accordingly",
    r"these?\s+are\s+(?:the\s+)?reasons",
    r"(?:mfr|m\.?f\.?r\.?)\s*[-–—]\s*(?:islamabad|approved|office)",
    r"(?:chief\s+justice|judge)\s*$",
]
_DISPOSITION_RE = re.compile(
    "|".join(_DISPOSITION_MARKERS), re.IGNORECASE | re.MULTILINE
)


def parse_judgment(text: str) -> list[JudgmentSection]:
    """Parse a judgment into structural sections.

    Returns a list of 1-3 sections: [header], body, [disposition].
    Header and disposition are optional — body is always present.
    """
    if not text or not text.strip():
        return []

    text = text.strip()
    marker_start, marker_end = _find_judgment_marker(text)
    disposition_start = _find_disposition(text, marker_end)

    sections: list[JudgmentSection] = []

    # Header section (everything up to and including JUDGMENT/ORDER marker)
    if marker_start > 0:
        header_text = text[:marker_end].strip()
        if header_text:
            sections.append(JudgmentSection(
                section_type=SectionType.HEADER,
                text=header_text,
                start_char=0,
                end_char=marker_end,
            ))

    # Body section (main reasoning, starts after the marker)
    body_start = marker_end
    body_end = disposition_start if disposition_start else len(text)
    body_text = text[body_start:body_end].strip()
    if body_text:
        para_nums = _extract_paragraph_numbers(body_text)
        sections.append(JudgmentSection(
            section_type=SectionType.BODY,
            text=body_text,
            paragraph_numbers=para_nums,
            start_char=body_start,
            end_char=body_end,
        ))

    # Disposition section (final orders)
    if disposition_start and disposition_start < len(text):
        disp_text = text[disposition_start:].strip()
        if disp_text:
            sections.append(JudgmentSection(
                section_type=SectionType.DISPOSITION,
                text=disp_text,
                start_char=disposition_start,
                end_char=len(text),
            ))

    # Fallback: if no sections found, treat entire text as body
    if not sections:
        sections.append(JudgmentSection(
            section_type=SectionType.BODY,
            text=text,
            paragraph_numbers=_extract_paragraph_numbers(text),
            start_char=0,
            end_char=len(text),
        ))

    return sections


def _find_judgment_marker(text: str) -> tuple[int, int]:
    """Find the JUDGMENT/ORDER marker that separates header from body.

    Returns (header_end, body_start). If no marker found, returns (0, 0).
    """
    match = _JUDGMENT_MARKER.search(text)
    if match:
        return match.start(), match.end()

    # Fallback: look for judge attribution pattern "Name, J.:" or "Name, J.—"
    judge_pattern = re.search(
        r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*J\.?\s*[:—–-]",
        text,
    )
    if judge_pattern:
        return judge_pattern.start(), judge_pattern.start()

    return 0, 0


def _find_disposition(text: str, search_from: int) -> Optional[int]:
    """Find the start of the disposition section.

    Looks for disposition markers in the last 30% of the text (dispositions
    are always at the end). Returns char offset or None.
    """
    text_len = len(text)
    # Only search the last 30% of the document
    search_start = max(search_from, int(text_len * 0.7))
    search_text = text[search_start:]

    match = _DISPOSITION_RE.search(search_text)
    if not match:
        return None

    # Walk back to the start of the paragraph containing the match
    abs_pos = search_start + match.start()
    para_start = text.rfind("\n", search_from, abs_pos)
    if para_start == -1:
        para_start = search_from

    return para_start


def _extract_paragraph_numbers(text: str) -> list[int]:
    """Extract all numbered paragraph numbers from text."""
    return sorted(set(int(m.group(1)) for m in _NUMBERED_PARA.finditer(text)))
