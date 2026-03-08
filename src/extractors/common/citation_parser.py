"""Extract Pakistani legal citations from judgment text."""

from __future__ import annotations

import re

# Pakistani citation formats:
# PLD 2020 SC 456, PLD 2020 Lahore 123
# 2019 SCMR 789, 2020 SCMR 1234
# 2018 PCrLJ 567, 2019 CLC 890
# NLR 2020 Criminal 45
# PLJ 2019 SC 234

_CITATION_PATTERNS = [
    # PLD YEAR COURT PAGE — "PLD 2020 SC 456"
    re.compile(r"PLD\s+(\d{4})\s+(\w+(?:\s+\w+)?)\s+(\d+)", re.IGNORECASE),
    # YEAR REPORTER PAGE — "2019 SCMR 789"
    re.compile(
        r"(\d{4})\s+(SCMR|PCrLJ|CLC|PTD|PLC|CLD|YLR|MLD|PSC|PLJ|NLR)\s+(\d+)",
        re.IGNORECASE,
    ),
    # PLJ YEAR COURT PAGE — "PLJ 2019 SC 234"
    re.compile(r"PLJ\s+(\d{4})\s+(\w+(?:\s+\w+)?)\s+(\d+)", re.IGNORECASE),
    # NLR YEAR SECTION PAGE — "NLR 2020 Criminal 45"
    re.compile(r"NLR\s+(\d{4})\s+(\w+)\s+(\d+)", re.IGNORECASE),
]

# Constitutional articles: "Article 184(3)", "Article 10-A"
_ARTICLE_PAT = re.compile(
    r"Article\s+(\d+(?:-[A-Z])?(?:\(\d+\))?)", re.IGNORECASE
)

# PPC section numbers specifically: "302 PPC", "PPC 302"
_PPC_PAT = re.compile(
    r"(?:(\d+)\s+P\.?P\.?C\.?|P\.?P\.?C\.?\s+(\d+))", re.IGNORECASE
)

# Statute names: "Anti-Terrorism Act, 1997", "CNSA, 1997"
_STATUTE_PAT = re.compile(
    r"((?:[\w-]+\s+){1,5}(?:Act|Ordinance|Order|Rules|Regulation)[,.]?\s*\d{4})",
    re.IGNORECASE,
)

# Known CrPC sections that commonly appear in criminal judgments
# These must NEVER be attributed to PPC
_CRPC_SECTIONS = {
    154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164,
    173, 196, 200, 202, 203, 204, 241, 242, 249, 265,
    340, 341, 342, 345, 367, 369, 371, 374, 376, 377, 378,
    381, 382, 395, 396, 397, 399, 400, 401, 402, 403, 404,
    417, 418, 419, 423, 426, 435, 439, 491, 497, 498, 561,
}


def extract_citations(text: str) -> list[str]:
    """Extract all Pakistani case citations (PLD, SCMR, CLC, etc.)."""
    citations = set()
    for pat in _CITATION_PATTERNS:
        for m in pat.finditer(text):
            # Normalize internal whitespace (newlines → spaces)
            normalized = re.sub(r"\s+", " ", m.group(0)).strip()
            citations.add(normalized)
    return sorted(citations)


def extract_ppc_sections(text: str) -> list[int]:
    """Extract PPC section numbers from text.

    Only captures sections explicitly attributed to PPC/Pakistan Penal Code.
    Does NOT capture CrPC, ATA, CNSA, or other statute section numbers.
    """
    sections = set()

    # Pattern 1: "302 PPC" or "PPC 302" — explicitly PPC-qualified
    for m in _PPC_PAT.finditer(text):
        num = m.group(1) or m.group(2)
        if num:
            sections.add(int(num))

    # Pattern 2: "Section 302 of the Pakistan Penal Code" or "Section 302, PPC"
    for m in re.finditer(
        r"[Ss]ection\s+(\d+)\s+(?:of\s+)?(?:the\s+)?(?:P\.?P\.?C|Pakistan\s+Penal\s+Code)",
        text,
    ):
        sections.add(int(m.group(1)))

    # Pattern 3: "Sections 302/34 PPC" or "302, 34, 109 PPC"
    for m in re.finditer(r"[Ss]ections?\s+([\d,/\s]+)\s*(?:P\.?P\.?C|PPC)", text):
        for num in re.findall(r"\d+", m.group(1)):
            sections.add(int(num))

    # Pattern 4: "u/s 302 PPC" — only if PPC appears within 30 chars after
    for m in re.finditer(r"(?:u/s|under\s+[Ss]ection)\s+(\d+)", text):
        context_after = text[m.end():m.end() + 30]
        if re.search(r"P\.?P\.?C", context_after, re.IGNORECASE):
            sections.add(int(m.group(1)))

    # Pattern 5: "conviction under Section 302 read with Section 34 PPC"
    for m in re.finditer(
        r"(?:under|u/s)\s+[Ss]ections?\s+([\d,/\s]+(?:\s+read\s+with\s+[Ss]ections?\s+[\d,/\s]+)*)\s*(?:P\.?P\.?C|PPC)",
        text,
    ):
        for num in re.findall(r"\d+", m.group(1)):
            sections.add(int(num))

    # Safety: remove any known CrPC sections that leaked through
    sections -= _CRPC_SECTIONS

    return sorted(sections)


def extract_constitutional_articles(text: str) -> list[str]:
    """Extract constitutional article references."""
    articles = set()
    for m in _ARTICLE_PAT.finditer(text):
        articles.add(m.group(1))
    return sorted(articles)


def extract_statutes(text: str) -> list[str]:
    """Extract statute/act names mentioned in text."""
    statutes = set()
    for m in _STATUTE_PAT.finditer(text):
        # Normalize whitespace
        normalized = re.sub(r"\s+", " ", m.group(0)).strip().rstrip(",. ")
        statutes.add(normalized)
    return sorted(statutes)


def extract_fir_number(text: str) -> str | None:
    """Extract FIR number from text."""
    m = re.search(
        r"F\.?I\.?R\.?\s*(?:No\.?)?\s*(\d+(?:/\d+)?)",
        text, re.IGNORECASE,
    )
    if m:
        return re.sub(r"\s+", " ", m.group(0)).strip()
    return None
