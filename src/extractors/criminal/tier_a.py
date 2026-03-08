"""Tier A: Regex/pattern-based extraction for directly extractable fields.

Extracts ~85 fields from criminal judgment text using regex, pattern matching,
and simple heuristics. No LLM calls — fast and deterministic.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date
from typing import Optional

from ..common.citation_parser import (
    extract_citations,
    extract_constitutional_articles,
    extract_fir_number,
    extract_ppc_sections,
    extract_statutes,
)
from ..common.date_parser import parse_date
from .schema import (
    CaseType,
    CourtLevel,
    Province,
    TierA,
)

# Life imprisonment = 25 years in Pakistan (PPC Section 45)
LIFE_IMPRISONMENT_MONTHS = 300


def extract_tier_a(text: str, source_url: str = "") -> TierA:
    """Run all Tier A extractors on judgment text."""
    if not text or len(text.strip()) < 100:
        return TierA()

    result = TierA()

    # Core identification
    result.case_number = _extract_case_number(text)
    result.case_title = _extract_case_title(text)
    result.case_type = _classify_case_type(text, result.case_number)
    result.court_name = _extract_court_name(text)
    result.court_level = _classify_court_level(result.court_name or text)
    result.judge_names = _extract_judge_names(text)
    result.jurisdiction_province = _classify_province(result.court_name or text)
    result.date_judgment = _extract_judgment_date(text)
    result.date_incident = _extract_incident_date(text)
    result.date_fir = _extract_fir_date(text)
    result.date_filed = _extract_filing_date(text)

    # Offense & Charges (pattern-extractable only)
    result.ppc_sections = extract_ppc_sections(text)
    result.section_34_applied = _detect_ppc_section(text, 34)
    result.forum_category = _classify_forum(result.ppc_sections)

    # Parties
    result.accused_name = _extract_accused_name(text)
    result.victim_name = _extract_victim_name(text)
    result.complainant_name = _extract_complainant_name(text)
    result.fir_number = extract_fir_number(text)
    result.police_station = _extract_police_station(text)
    result.prosecutor_name = _extract_counsel(text, "prosecution")
    result.defense_counsel = _extract_counsel(text, "defense")

    # Evidence indicators (keyword-matchable only)
    result.weapon_recovered = _bool_search(text, r"(?:weapon|pistol|rifle|gun|knife|dagger|hatchet)\s+(?:was\s+)?recovered")
    result.dna_tested = _bool_search(text, r"DNA\s+(?:test|report|analysis|examination)")
    result.dna_matched_accused = _bool_search(text, r"DNA\s+(?:matched|confirmed|established)")
    result.ballistics_matched = _bool_search(text, r"(?:ballistic|forensic)\s+(?:report|evidence)\s+(?:confirmed|matched|established)")
    result.post_mortem_done = _bool_search(text, r"(?:post[\s-]?mortem|autopsy|PM)\s+(?:report|examination|conducted)")
    result.medical_evidence_present = _bool_search(text, r"(?:medical|medico[\s-]?legal)\s+(?:evidence|report|certificate|examination)")
    result.dying_declaration_exists = _bool_search(text, r"dying\s+declaration")

    # Witness summary (count-based and keyword-matchable)
    result.prosecution_witness_count = _extract_witness_count(text, "prosecution")
    result.defense_witness_count = _extract_witness_count(text, "defense")
    result.eyewitness_count = _extract_witness_count(text, "eye")
    result.hostile_witness_declared = _bool_search(text, r"hostile\s+witness")

    # Procedural
    result.fir_delay_hours = _extract_fir_delay(text)
    result.police_malpractice_alleged = _bool_search(text, r"(?:police\s+malpractice|mala\s+fide|fabricated|planted)")
    result.torture_allegations = _bool_search(text, r"(?:torture|coercion|duress|forced\s+confession)")
    result.section_161_recorded = _bool_search(text, r"[Ss]ection\s+161\s+Cr")
    result.section_164_recorded = _bool_search(text, r"[Ss]ection\s+164\s+Cr")
    result.search_warrant_obtained = _bool_search(text, r"(?:search\s+warrant|warrant\s+(?:of|for)\s+(?:search|arrest))")
    result.alibi_raised = _bool_search(text, r"alibi")

    # Sentencing — mechanical pattern extraction only
    operative_text = text[-2000:]
    result.sentence_total_months = _extract_sentence_months(operative_text)
    result.fine_amount_pkr = _extract_fine(text)
    result.diyat_compromise = _bool_search(text, r"(?:diyat|diyya|compromise|compounded)")
    result.section_382b_benefit = _bool_search(text, r"[Ss]ection\s+382[\s-]?[Bb]")
    result.sentence_modified_to = _extract_sentence_modification(text)

    # Appeal linkage (pattern-extractable)
    result.lower_court_case_number = _extract_lower_court_case(text)
    result.lower_court_name = _extract_lower_court_name(text)
    result.precedents_cited = extract_citations(text)
    result.statutes_discussed = extract_statutes(text)
    result.constitutional_articles = extract_constitutional_articles(text)
    result.source_url = source_url or None

    # Generate case_id last (depends on extracted fields)
    result.case_id = _generate_case_id(result.court_name, result.case_number, result.date_judgment)

    return result


# ── Core Identification ───────────────────────────────────────────────────

def _extract_case_number(text: str) -> str | None:
    """Extract primary case number like 'Cr. Appeal No. 123/2023'."""
    # Search only in header (first 2000 chars)
    header = text[:2000]
    patterns = [
        r"(CRIMINAL\s+APPEAL\s+NO\.?\s*\d+(?:\s+OF\s+\d{4})?)",
        r"(Crl?\.?\s*(?:Appeal|Petition|Application|Misc\.?\s*App(?:lication)?|O\.?P\.?)\s*No\.?\s*\d+(?:-\w+)?(?:/\d+)?(?:\s+(?:of|OF)\s+\d{4})?)",
        r"(Criminal\s+(?:Appeal|Petition|Application)\s+No\.?\s*\d+(?:/\d+)?(?:\s+of\s+\d{4})?)",
        r"((?:CRL|Crl)\.?\s*(?:A|P|MA|OP)\.?\s*(?:No\.?)?\s*\d+(?:-[A-Z])?(?:/\d+)?(?:\s+of\s+\d{4})?)",
        r"(S\.M\.C\.?\s*No\.?\s*\d+(?:/\d+)?)",
        r"(H\.R\.C\.?\s*No\.?\s*\d+(?:/\d+)?)",
        r"(Suo\s+Motu\s+Case\s+No\.?\s*\d+(?:/\d+)?)",
    ]
    for pat in patterns:
        m = re.search(pat, header, re.IGNORECASE)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()
    return None


_PROCEDURAL_LABELS = {
    "appellant", "appellants", "petitioner", "petitioners",
    "respondent", "respondents", "applicant", "applicants",
    "convict", "accused", "complainant",
}


def _extract_case_title(text: str) -> str | None:
    """Extract case title like 'Amjad Shah v. The State'."""
    header = re.sub(r"\s+", " ", text[:3000])
    patterns = [
        r"([\w\s\.]+?)\s+(?:Versus|vs?\.?|V/S)\s+([\w\s\.]+?)(?:\s*\.{3}|\s*…|\s+For\b|\s+\n|$)",
    ]
    for pat in patterns:
        m = re.search(pat, header, re.IGNORECASE)
        if m:
            plaintiff = _clean_party_name(m.group(1).strip()[:100])
            defendant = _clean_party_name(m.group(2).strip()[:100])
            if plaintiff and defendant:
                return f"{plaintiff} v. {defendant}"
    return None


def _clean_party_name(name: str) -> str | None:
    """Remove procedural labels from party names."""
    # Remove trailing dots, ellipsis, whitespace
    name = name.rstrip(". …\t\n")
    # If the entire name is a procedural label, skip
    if name.lower().strip() in _PROCEDURAL_LABELS:
        return None
    # Remove leading/trailing procedural labels
    parts = name.split()
    while parts and parts[-1].lower().rstrip(".") in _PROCEDURAL_LABELS:
        parts.pop()
    while parts and parts[0].lower().rstrip(".") in _PROCEDURAL_LABELS:
        parts.pop(0)
    cleaned = " ".join(parts).strip()
    return cleaned if len(cleaned) > 2 else None


def _classify_case_type(text: str, case_num: str | None) -> CaseType | None:
    if case_num:
        cn = case_num.lower()
        if "appeal" in cn or "crl.a" in cn or "cr. appeal" in cn or "crl. a" in cn:
            return CaseType.APPEAL
        if "petition" in cn or "p.l.a" in cn or "cpla" in cn:
            return CaseType.PETITION
        if "revision" in cn or "crp" in cn:
            return CaseType.REVISION
        if "reference" in cn:
            return CaseType.REFERENCE
        if "s.m.c" in cn or "suo motu" in cn:
            return CaseType.SUO_MOTU
        if "contempt" in cn or "o.p" in cn:
            return CaseType.CONTEMPT
    # Fallback: only check first 500 chars (court header) to avoid false positives
    header = text[:500].lower()
    if "suo motu" in header:
        return CaseType.SUO_MOTU
    if "contempt" in header:
        return CaseType.CONTEMPT
    return None


def _extract_court_name(text: str) -> str | None:
    """Extract court name from header."""
    courts = [
        "Supreme Court of Pakistan",
        "Lahore High Court",
        "Sindh High Court",
        "Islamabad High Court",
        "Peshawar High Court",
        "Balochistan High Court",
        "Federal Shariat Court",
        "Anti[- ]Terrorism Court",
    ]
    header = text[:2000]
    for court in courts:
        m = re.search(court, header, re.IGNORECASE)
        if m:
            return m.group(0)

    # Try "IN THE SUPREME COURT" pattern
    m = re.search(r"IN\s+THE\s+([\w\s]+COURT[\w\s]*?)(?:\n|$)", header, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def _classify_court_level(court_or_text: str) -> CourtLevel | None:
    lower = court_or_text.lower()
    if "supreme" in lower:
        return CourtLevel.SUPREME_COURT
    if "high court" in lower:
        return CourtLevel.HIGH_COURT
    if "anti" in lower and "terrorism" in lower:
        return CourtLevel.ANTI_TERRORISM_COURT
    if "shariat" in lower:
        return CourtLevel.FEDERAL_SHARIAT
    if "session" in lower or "trial" in lower:
        return CourtLevel.TRIAL_COURT
    if "special" in lower:
        return CourtLevel.SPECIAL_COURT
    return None


_JUDGE_STOP_WORDS = {"Mr", "Mrs", "Ms", "Criminal", "Civil", "Appeal", "Petition",
                     "Application", "Case", "No", "Original", "Suo", "Motu",
                     "Appeals", "Cr", "Crl", "The", "And", "In", "For", "Of"}


def _extract_judge_names(text: str) -> list[str]:
    """Extract judge names from 'PRESENT: Mr. Justice X, Mr. Justice Y'."""
    judges = set()
    header = re.sub(r"\s+", " ", text[:3000])

    for m in re.finditer(
        r"(?:Mr\.|Mrs\.|Ms\.)?\s*Justice\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,5})",
        header,
    ):
        name = _clean_judge_name(m.group(1).strip())
        if name:
            judges.add(name)

    # "PRESENT: ..." block
    present_block = re.search(r"PRESENT[:\s]+(.+?)(?:\n\n|\n[A-Z])", text[:3000], re.DOTALL | re.IGNORECASE)
    if present_block:
        normalized = re.sub(r"\s+", " ", present_block.group(1))
        for m in re.finditer(r"Justice\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,5})", normalized):
            name = _clean_judge_name(m.group(1).strip())
            if name:
                judges.add(name)

    return sorted(judges)


def _clean_judge_name(name: str) -> str | None:
    parts = name.split()
    while parts and parts[-1] in _JUDGE_STOP_WORDS:
        parts.pop()
    if len(parts) < 2:
        return None
    return " ".join(parts)


def _classify_province(court_or_text: str) -> Province | None:
    lower = court_or_text.lower()
    if "lahore" in lower or "punjab" in lower:
        return Province.PUNJAB
    if "sindh" in lower or "karachi" in lower:
        return Province.SINDH
    if "peshawar" in lower or "kpk" in lower or "khyber" in lower:
        return Province.KPK
    if "balochistan" in lower or "quetta" in lower:
        return Province.BALOCHISTAN
    if "islamabad" in lower:
        return Province.ISLAMABAD
    if "supreme" in lower or "federal" in lower:
        return Province.FEDERAL
    return None


def _extract_judgment_date(text: str) -> Optional[date]:
    """Extract judgment pronouncement date.

    Priority: footer date (where courts stamp the pronouncement) > header date.
    Restricts header to first 1500 chars to avoid picking up lower court dates.
    """
    # Priority 1: Footer — "Islamabad, 01.02.2016" or "Announced on 01.02.2016"
    footer = text[-2000:]
    for pat in [
        r"(?:Announced|Decided|Dated|Islamabad|Lahore|Karachi|Peshawar|Quetta)[,.]?\s*\n?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{4})",
        r"(?:Announced|Decided|Dated)\s+(?:on\s+)?(?:this\s+)?(.{10,40})",
    ]:
        m = re.search(pat, footer, re.IGNORECASE)
        if m:
            d = parse_date(m.group(1))
            if d:
                return d

    # Priority 2: Header (first 1500 chars only — avoids lower court date references)
    header = text[:1500]
    for pat in [
        r"Date\s+of\s+(?:Judgment|Decision|Order|Hearing)\s*[:\s]*(.{10,40})",
        r"(?:announced\s+on|decided\s+on|judgment\s+(?:dated|on))\s*[:\s]*(.{10,40})",
    ]:
        m = re.search(pat, header, re.IGNORECASE)
        if m:
            d = parse_date(m.group(1))
            if d:
                return d

    return None


def _extract_incident_date(text: str) -> Optional[date]:
    for pat in [
        r"(?:incident|occurrence|crime|offence|murder)\s+(?:took\s+place|occurred|happened|committed)\s+on\s+(.{10,40})",
        r"(?:on|dated)\s+(.{10,40})\s+(?:the\s+)?(?:incident|occurrence|murder)",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            d = parse_date(m.group(1))
            if d:
                return d
    return None


def _extract_fir_date(text: str) -> Optional[date]:
    for pat in [
        r"F\.?I\.?R\.?\s+(?:No\.?\s*\d+[/\s]*\d*\s+)?(?:was\s+)?(?:lodged|registered|recorded)\s+on\s+(.{10,40})",
        r"(?:lodged|registered)\s+(?:the\s+)?F\.?I\.?R\.?\s+on\s+(.{10,40})",
        r"F\.?I\.?R\.?\s+(?:No\.?\s*\d+[/\s]*\d*\s+)?dated\s+(.{10,40})",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            d = parse_date(m.group(1))
            if d:
                return d
    return None


def _extract_filing_date(text: str) -> Optional[date]:
    for pat in [
        r"leave\s+to\s+appeal\s+was\s+granted\s+(?:by\s+this\s+Court\s+)?on\s+(.{10,40})",
        r"(?:appeal|petition)\s+(?:was\s+)?(?:filed|instituted|preferred)\s+on\s+(.{10,40})",
    ]:
        m = re.search(pat, text[:5000], re.IGNORECASE)
        if m:
            d = parse_date(m.group(1))
            if d:
                return d
    return None


def _generate_case_id(court: str | None, case_num: str | None, dt: object | None) -> str | None:
    if not case_num:
        return None
    raw = f"{court or 'unknown'}:{case_num}:{dt or 'unknown'}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _detect_ppc_section(text: str, section: int) -> bool | None:
    """Detect if a specific PPC section was charged — requires PPC context."""
    pattern = rf"(?:[Ss]ection\s+{section}\s+P\.?P\.?C|{section}\s+P\.?P\.?C|P\.?P\.?C\.?\s+{section}|[Ss]ection\s+{section}\s+read\s+with)"
    return True if re.search(pattern, text, re.IGNORECASE) else False


def _classify_forum(sections: list[int]) -> str | None:
    ss = set(sections)
    if ss & {302, 303, 304, 307, 308, 309, 310, 311, 316, 319, 320, 321, 322, 323, 324, 325}:
        return "murder"
    if ss & {376, 375, 377}:
        return "sexual_assault"
    if ss & {378, 379, 380, 381, 382, 392, 393, 394, 395, 396, 397}:
        return "theft"
    return None


# ── Parties ───────────────────────────────────────────────────────────────

def _extract_accused_name(text: str) -> str | None:
    header = re.sub(r"\s+", " ", text[:5000])
    patterns = [
        r"(?:accused|appellant|convict|petitioner)\s+(?:namely\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})",
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})\s+(?:accused|appellant|convict)",
    ]
    for pat in patterns:
        m = re.search(pat, header)
        if m:
            name = m.group(1).strip()
            if name.lower() not in ("the state", "state", "government", "the crown"):
                return name
    return None


def _extract_victim_name(text: str) -> str | None:
    patterns = [
        r"(?:victim|deceased|murdered|killed)\s+(?:namely\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})",
        r"(?:murder|death|killing)\s+of\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})",
    ]
    for pat in patterns:
        m = re.search(pat, text[:8000])
        if m:
            return m.group(1).strip()
    return None


def _extract_complainant_name(text: str) -> str | None:
    m = re.search(
        r"(?:complainant|informant)\s+(?:namely\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})",
        text[:8000],
    )
    return m.group(1).strip() if m else None


def _extract_police_station(text: str) -> str | None:
    m = re.search(
        r"(?:Police\s+Station|P\.S\.?|PS)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})",
        text[:8000],
    )
    return m.group(1).strip() if m else None


def _extract_counsel(text: str, side: str) -> str | None:
    header = re.sub(r"\s+", " ", text[:4000])
    if side == "prosecution":
        patterns = [
            r"(?:for\s+the\s+)?(?:State|Prosecution|Complainant)\s*[:\s]+(?:Mr\.|Mrs\.|Ms\.)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})",
            r"(?:Prosecutor|APG|AG|Advocate[\s-]General)\s*[:\s]+(?:Mr\.|Mrs\.|Ms\.)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})",
        ]
    else:
        patterns = [
            r"(?:for\s+the\s+)?(?:Accused|Appellant|Petitioner|Defence|Defense)\s*[:\s]+(?:Mr\.|Mrs\.|Ms\.)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})",
            r"(?:Defence|Defense)\s+Counsel\s*[:\s]+(?:Mr\.|Mrs\.|Ms\.)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})",
        ]
    for pat in patterns:
        m = re.search(pat, header, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


# ── Witnesses ─────────────────────────────────────────────────────────────

def _extract_witness_count(text: str, kind: str) -> int | None:
    if kind == "prosecution":
        patterns = [
            r"(\d+)\s+(?:prosecution\s+)?(?:PWs?|prosecution\s+witness)",
            r"prosecution\s+(?:examined|produced)\s+(\d+)\s+witness",
        ]
    elif kind == "defense":
        patterns = [
            r"(\d+)\s+(?:defence|defense)\s+witness",
            r"(?:defence|defense)\s+(?:examined|produced)\s+(\d+)\s+witness",
        ]
    else:  # eyewitness
        patterns = [
            r"(\d+)\s+eye[\s-]?witness",
        ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return int(m.group(1))
    # Count PW-1, PW-2, etc.
    if kind == "prosecution":
        pws = re.findall(r"PW[\s-]*(\d+)", text)
        if pws:
            return max(int(n) for n in pws)
    return None


# ── Sentencing ────────────────────────────────────────────────────────────

def _extract_sentence_months(operative_text: str) -> int | None:
    lower = operative_text.lower()
    if "imprisonment for life" in lower or "life imprisonment" in lower:
        return LIFE_IMPRISONMENT_MONTHS
    if re.search(r"sentence\s+of\s+death\s+.*?(?:altered|commuted)\s+to\s+.*?life", lower):
        return LIFE_IMPRISONMENT_MONTHS
    m = re.search(r"(\d+)\s+years?\s+(?:rigorous\s+)?imprisonment", lower)
    if m:
        return int(m.group(1)) * 12
    m = re.search(r"(\d+)\s+months?\s+(?:rigorous\s+)?imprisonment", lower)
    if m:
        return int(m.group(1))
    return None


def _extract_fine(text: str) -> int | None:
    # Search in broader text — fine amounts appear in various places
    m = re.search(r"(?:fine|fined)\s+(?:of\s+|with\s+)?(?:Rs\.?|PKR)\s*([0-9,]+)", text, re.IGNORECASE)
    if m:
        return int(m.group(1).replace(",", ""))
    return None


def _extract_sentence_modification(text: str) -> str | None:
    lower = text[-5000:].lower()
    if re.search(r"sentence\s+of\s+death\s+.*?(?:altered|commuted|reduced)\s+to\s+.*?life", lower):
        return "death_to_life"
    if "death" in lower and "life" in lower and ("reduced" in lower or "commuted" in lower or "altered" in lower):
        return "death_to_life"
    if "life" in lower and re.search(r"(\d+)\s+years?", lower) and ("reduced" in lower or "modified" in lower):
        m = re.search(r"(\d+)\s+years?", lower)
        if m:
            return f"life_to_{m.group(1)}years"
    return None


# ── Appeal Linkage ────────────────────────────────────────────────────────

def _extract_lower_court_case(text: str) -> str | None:
    patterns = [
        r"(?:Sessions?\s+(?:Case|Trial)\s+No\.?)\s*(\d+(?:/\d+)?(?:\s+of\s+\d{4})?)",
        r"(?:Trial\s+No\.?|Case\s+No\.?)\s*(\d+(?:/\d+)?)",
    ]
    for pat in patterns:
        m = re.search(pat, text[:8000], re.IGNORECASE)
        if m:
            return m.group(0).strip()
    return None


def _extract_lower_court_name(text: str) -> str | None:
    """Extract lower court name — stops at 'vide', 'dated', 'in' to avoid trailing garbage."""
    m = re.search(
        r"(?:learned\s+)?(?:Additional\s+)?(?:Sessions?\s+Judge|Trial\s+Court|Magistrate)\s*,?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})?",
        text[:8000],
        re.IGNORECASE,
    )
    if m:
        # Take just the court type + location, not trailing phrases
        result = m.group(0).strip()
        # Cut at common trailing phrases
        for stopper in ["vide", "dated", "in case", "upon conviction", "whereby"]:
            idx = result.lower().find(stopper)
            if idx > 0:
                result = result[:idx].strip().rstrip(",. ")
        return result
    return None


def _extract_fir_delay(text: str) -> int | None:
    m = re.search(r"(?:delay|gap)\s+of\s+(\d+)\s+hours?\s+(?:in\s+)?(?:lodging|registering|filing)\s+(?:the\s+)?(?:FIR|F\.I\.R)", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r"F\.?I\.?R\.?\s+was\s+(?:lodged|registered)\s+(?:with\s+a\s+)?delay\s+of\s+(\d+)\s+(?:hours?|days?)", text, re.IGNORECASE)
    if m:
        val = int(m.group(1))
        if "day" in m.group(0).lower():
            return val * 24
        return val
    return None


# ── Helpers ───────────────────────────────────────────────────────────────

def _bool_search(text: str, pattern: str) -> bool:
    """Return True if pattern found, False if not."""
    return bool(re.search(pattern, text, re.IGNORECASE))
