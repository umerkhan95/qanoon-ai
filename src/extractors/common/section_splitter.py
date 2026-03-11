"""Split Pakistani judgments into logical sections.

Single responsibility: full judgment text → dict of named sections.
Handles varied formatting across courts (SC, HC, ATC, etc.).

Sections identified:
- header: Court name, case number, parties, judges, dates
- facts: Factual background / prosecution story
- issues: Points of determination / legal questions framed
- petitioner_arguments: Arguments by appellant/petitioner counsel
- respondent_arguments: Arguments by respondent/state counsel
- evidence: Evidence discussion, witness examination
- reasoning: Court's analysis and reasoning
- order: Operative order / final decision
- full_text: Always present — the complete text
"""

from __future__ import annotations

import re
import logging

logger = logging.getLogger(__name__)

# Section markers commonly found in Pakistani judgments (case-insensitive)
# Order matters — first match wins for overlapping patterns
_SECTION_MARKERS = [
    # Facts / Background
    ("facts", [
        r"(?:brief\s+)?facts\s+(?:of\s+the\s+case|leading\s+to)",
        r"factual\s+(?:background|matrix|narrative)",
        r"prosecution\s+(?:case|story|version)\s+(?:in\s+brief|as\s+set)",
        r"(?:the\s+)?(?:brief|relevant)\s+facts",
    ]),
    # Issues framed
    ("issues", [
        r"points?\s+(?:of|for)\s+determination",
        r"(?:the\s+)?issues?\s+(?:framed|to\s+be\s+determined|for\s+consideration)",
        r"questions?\s+(?:of\s+law|for\s+consideration|that\s+arise)",
    ]),
    # Petitioner/Appellant arguments
    ("petitioner_arguments", [
        r"(?:learned\s+)?counsel\s+for\s+(?:the\s+)?(?:appellant|petitioner|accused)",
        r"arguments?\s+(?:on\s+behalf\s+)?(?:of|by)\s+(?:the\s+)?(?:appellant|petitioner)",
        r"(?:the\s+)?(?:appellant|petitioner)(?:'s)?\s+(?:case|arguments?|submissions?|contentions?)",
    ]),
    # Respondent/State arguments
    ("respondent_arguments", [
        r"(?:learned\s+)?counsel\s+for\s+(?:the\s+)?(?:respondent|state|complainant|prosecution)",
        r"arguments?\s+(?:on\s+behalf\s+)?(?:of|by)\s+(?:the\s+)?(?:respondent|state)",
        r"(?:the\s+)?(?:respondent|state|prosecution)(?:'s)?\s+(?:case|arguments?|submissions?|contentions?)",
    ]),
    # Evidence discussion
    ("evidence", [
        r"(?:the\s+)?evidence\s+(?:on\s+record|produced|adduced)",
        r"appraisal\s+of\s+evidence",
        r"(?:the\s+)?(?:prosecution|ocular|documentary)\s+evidence",
        r"examination\s+of\s+(?:witnesses|evidence)",
    ]),
    # Court reasoning
    ("reasoning", [
        r"(?:we\s+have\s+)?(?:heard|considered|examined)\s+(?:the\s+)?(?:learned\s+)?counsel",
        r"(?:our|my)\s+(?:analysis|reasoning|consideration|examination)",
        r"(?:after\s+)?(?:hearing|considering)\s+(?:the\s+)?(?:arguments|submissions)",
        r"(?:I|we)\s+have\s+(?:carefully\s+)?(?:gone\s+through|perused|examined)",
    ]),
    # Operative order
    ("order", [
        r"(?:in\s+the\s+)?(?:result|light\s+of\s+(?:the\s+)?above|upshot)",
        r"(?:the\s+)?appeal\s+is\s+(?:accordingly\s+)?(?:allowed|dismissed|disposed)",
        r"(?:for\s+the\s+)?(?:foregoing|above(?:\s+mentioned)?)\s+reasons",
        r"operative\s+(?:part|order|portion)",
        r"order\s*$",
    ]),
]


def split_judgment(text: str) -> dict[str, str]:
    """Split a judgment into named sections.

    Returns a dict with section names as keys and text content as values.
    Always includes "full_text" and "header". Other sections are included
    only if detected.

    If no section markers are found, returns just "full_text" and "header".
    """
    result: dict[str, str] = {"full_text": text}

    if not text or len(text.strip()) < 200:
        result["header"] = text.strip() if text else ""
        return result

    # Header is always the first ~15% of the judgment (court info, parties, etc.)
    header_end = min(len(text) // 7, 3000)
    result["header"] = text[:header_end].strip()

    # Find all section boundaries
    boundaries: list[tuple[int, str]] = []

    for section_name, patterns in _SECTION_MARKERS:
        for pattern in patterns:
            for m in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                # Only accept matches that start near a line beginning
                # (within 5 chars of a newline) to avoid mid-sentence matches
                line_start = text.rfind("\n", max(0, m.start() - 50), m.start())
                if line_start == -1:
                    line_start = 0
                prefix = text[line_start:m.start()].strip()

                # Accept if near start of line (numbered paragraphs ok)
                if len(prefix) < 30:
                    boundaries.append((m.start(), section_name))
                    break  # Take first match per pattern group
            else:
                continue
            break  # Found a match for this section_name, stop trying patterns

    if not boundaries:
        logger.info("No section markers found — returning full text only")
        return result

    # Sort by position
    boundaries.sort(key=lambda x: x[0])

    # Extract text between boundaries
    for i, (pos, name) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
        section_text = text[pos:end].strip()
        if section_text and len(section_text) > 50:
            # If we already have this section, append (multiple evidence sections etc.)
            if name in result and name != "header":
                result[name] += "\n\n" + section_text
            else:
                result[name] = section_text

    detected = [k for k in result if k not in ("full_text", "header")]
    logger.info(
        "Split judgment into %d sections: %s",
        len(detected), ", ".join(detected) if detected else "none",
    )

    return result
