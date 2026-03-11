"""Crawl Islamabad HC judgments via the JSON API and extract case metadata.

Single responsibility: API requests → list of JudgmentRecord.

The IHC website exposes a .NET ASMX web service at mis.ihc.gov.pk/ihc.asmx
with JSON endpoints. No browser rendering is required — pure HTTP POST calls
return structured JSON with all judgment metadata including PDF paths.

Two main search strategies:
1. srchDecisionClms — per-judge search for "reported" (AFR=1) and "important"
   judgments. PJUG=0 only works for important; reported requires per-judge iteration.
2. srchDecision1 — keyword search across all judgments.

API fields returned per judgment:
  O_ID, CASENO, PARTIES, DDATE, ATTACHMENTS, BENCHNAME, AUTHOR_JUDGES,
  O_CITATION, O_AFR, O_SUBJECT, O_REMARKS, O_UNDERSECTION, O_IHC_HEADNOTE,
  O_SC_STATUS, O_SC_ATTACHMENTS, ISLANDMARK, CASECODE, etc.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date
from urllib.parse import quote

import httpx
from pydantic import BaseModel

from .constants import (
    JUDGES_ENDPOINT,
    KEYWORD_SEARCH_ENDPOINT,
    PDF_BASE_URL,
    SEARCH_ENDPOINT,
)
from .errors import CrawlError

logger = logging.getLogger(__name__)

# Browser-like headers for the API
_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


class JudgmentRecord(BaseModel):
    """A single judgment record from the IHC API."""

    o_id: int
    case_number: str
    case_title: str
    parties: str
    decision_date: str
    decision_date_parsed: date | None = None
    bench: str
    author_judge: str
    citation: str
    subject: str
    remarks: str
    under_section: str
    headnote: str
    is_approved_for_reporting: bool
    is_landmark: bool
    sc_status: str
    sc_citation: str
    sc_pdf_url: str
    pdf_url: str
    case_code: int
    source_url: str
    judgment_type: str  # "reported" or "important"


def _parse_date(raw: str) -> date | None:
    """Parse IHC date format: DD-MMM-YYYY (e.g. '28-JAN-2026')."""
    raw = raw.strip()
    if not raw:
        return None

    month_map = {
        "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
        "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
    }

    try:
        parts = raw.split("-")
        if len(parts) == 3:
            day = int(parts[0])
            month = month_map.get(parts[1].upper())
            year = int(parts[2])
            if month:
                return date(year, month, day)
    except (ValueError, IndexError):
        pass

    logger.debug("Could not parse date: %s", raw)
    return None


def _build_pdf_url(attachment_path: str) -> str:
    """Build full PDF URL from the ATTACHMENTS field path.

    The ATTACHMENTS field contains a relative path like:
    /attachments/judgements/78510/1/filename.pdf

    These paths often contain special characters (parentheses, brackets)
    that need URL-encoding for reliable downloads.
    """
    if not attachment_path or attachment_path == "-":
        return ""

    # Split path into segments, URL-encode the filename part
    parts = attachment_path.rsplit("/", 1)
    if len(parts) == 2:
        directory, filename = parts
        encoded_path = directory + "/" + quote(filename, safe="")
    else:
        encoded_path = quote(attachment_path, safe="/")

    return f"{PDF_BASE_URL}{encoded_path}"


def _clean_text(raw: str | None) -> str:
    """Clean text field from API response."""
    if not raw or raw == "-":
        return ""
    return raw.strip().replace("\r\n", " ").replace("\r", " ")


def _parse_case_number(raw: str) -> tuple[str, str]:
    """Parse IHC case number format: 'Writ Petition-1410-2024' into a
    standardized case number and extract the raw format.

    Returns (case_number, case_title) where case_title comes from PARTIES.
    """
    return raw.strip(), ""


def parse_api_records(
    records: list[dict],
    judgment_type: str,
    source_url: str,
) -> list[JudgmentRecord]:
    """Parse raw API JSON records into JudgmentRecord models.

    Args:
        records: List of dicts from the IHC API response.
        judgment_type: "reported" or "important".
        source_url: Source URL for provenance tracking.
    """
    parsed = []
    for rec in records:
        decision_date_raw = rec.get("DDATE", "").strip()
        attachment = rec.get("ATTACHMENTS", "")
        sc_attachment = rec.get("O_SC_ATTACHMENTS", "")

        record = JudgmentRecord(
            o_id=int(rec.get("O_ID", 0)),
            case_number=rec.get("CASENO", "").strip(),
            case_title=rec.get("TITLE", "").strip(),
            parties=rec.get("PARTIES", "").strip(),
            decision_date=decision_date_raw,
            decision_date_parsed=_parse_date(decision_date_raw),
            bench=rec.get("BENCHNAME", "").strip(),
            author_judge=rec.get("AUTHOR_JUDGES", "").strip(),
            citation=_clean_text(rec.get("O_CITATION")),
            subject=_clean_text(rec.get("O_SUBJECT")),
            remarks=_clean_text(rec.get("O_REMARKS")),
            under_section=_clean_text(rec.get("O_UNDERSECTION")),
            headnote=_clean_text(rec.get("O_IHC_HEADNOTE")),
            is_approved_for_reporting=bool(rec.get("O_AFR")),
            is_landmark=bool(rec.get("ISLANDMARK")),
            sc_status=_clean_text(rec.get("O_SC_STATUS")),
            sc_citation=_clean_text(rec.get("O_SC_CITATION")),
            sc_pdf_url=_build_pdf_url(sc_attachment),
            pdf_url=_build_pdf_url(attachment),
            case_code=int(rec.get("CASECODE", 0)),
            source_url=source_url,
            judgment_type=judgment_type,
        )
        parsed.append(record)

    return parsed


async def _post_json(url: str, payload: dict) -> list[dict]:
    """Make a POST request to the IHC ASMX API and return parsed records.

    The API wraps responses in {"d": "<json_string>"} where the inner
    string is either "empty" or a JSON array of records.

    Raises:
        CrawlError: If the request fails or returns an error.
    """
    async with httpx.AsyncClient(
        verify=False,
        follow_redirects=True,
        timeout=httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0),
    ) as client:
        try:
            response = await client.post(url, json=payload, headers=_HEADERS)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise CrawlError(f"API request failed: {e}") from e

    try:
        data = response.json()
    except json.JSONDecodeError as e:
        raise CrawlError(f"Invalid JSON response: {e}") from e

    raw_d = data.get("d", "")

    # The 'd' field is a JSON-encoded string
    if isinstance(raw_d, str):
        try:
            inner = json.loads(raw_d)
        except json.JSONDecodeError as e:
            raise CrawlError(f"Failed to parse inner JSON: {e}") from e
    else:
        inner = raw_d

    # "empty" string means no results
    if inner == "empty" or not inner:
        return []

    if not isinstance(inner, list):
        raise CrawlError(f"Unexpected API response type: {type(inner)}")

    return inner


async def fetch_judges() -> list[dict]:
    """Fetch the list of IHC judges with their IDs.

    Returns list of dicts with JUDGE_ID, JUG_REALNAME, ISRETIRED, etc.
    """
    payload = {"_params": {"jgs": "1"}}
    return await _post_json(JUDGES_ENDPOINT, payload)


async def crawl_judgments_for_judge(
    judge_id: int,
    judgment_type: str = "reported",
) -> list[JudgmentRecord]:
    """Crawl judgments for a specific judge.

    Args:
        judge_id: The IHC judge ID.
        judgment_type: "reported" (AFR=1, LANDMARK=1) or "important" (AFR=0, LANDMARK=0).
    """
    if judgment_type == "reported":
        pafr, plandmark = "1", "1"
    else:
        pafr, plandmark = "0", "0"

    payload = {
        "PCASENO": "0",
        "PJUG": str(judge_id),
        "PADV": "0",
        "PYEAR": "0",
        "pPrty": "",
        "PDDATE": "01/01/1900",
        "PLANDMARK": plandmark,
        "PAFR": pafr,
    }

    raw_records = await _post_json(SEARCH_ENDPOINT, payload)
    records = parse_api_records(raw_records, judgment_type, SEARCH_ENDPOINT)

    logger.info(
        "Judge %d (%s): %d records",
        judge_id, judgment_type, len(records),
    )
    return records


async def crawl_all_judgments(
    judgment_type: str = "reported",
) -> list[JudgmentRecord]:
    """Crawl all judgments of a given type across all judges.

    For "important" judgments, PJUG=0 returns all at once.
    For "reported" judgments, we must iterate per judge because PJUG=0 returns empty.

    Args:
        judgment_type: "reported" or "important".

    Returns:
        Deduplicated list of JudgmentRecord.
    """
    if judgment_type == "important":
        # PJUG=0 works for important judgments
        payload = {
            "PCASENO": "0",
            "PJUG": "0",
            "PADV": "0",
            "PYEAR": "0",
            "pPrty": "",
            "PDDATE": "01/01/1900",
            "PLANDMARK": "0",
            "PAFR": "0",
        }
        raw_records = await _post_json(SEARCH_ENDPOINT, payload)
        records = parse_api_records(raw_records, judgment_type, SEARCH_ENDPOINT)
        logger.info("All important judgments: %d records", len(records))
        return records

    # For reported judgments, iterate per judge
    judges = await fetch_judges()
    all_records: list[JudgmentRecord] = []
    seen_ids: set[int] = set()

    for judge in judges:
        judge_id = judge.get("JUDGE_ID")
        judge_name = judge.get("JUG_REALNAME", "Unknown")
        if not judge_id:
            continue

        records = await crawl_judgments_for_judge(judge_id, "reported")
        new_count = 0
        for rec in records:
            if rec.o_id not in seen_ids:
                seen_ids.add(rec.o_id)
                all_records.append(rec)
                new_count += 1

        if new_count:
            logger.info(
                "Judge %s (ID=%d): %d new reported judgments",
                judge_name, judge_id, new_count,
            )

    logger.info(
        "Total reported judgments across all judges: %d (deduplicated)",
        len(all_records),
    )
    return all_records


async def crawl_all() -> list[JudgmentRecord]:
    """Crawl all available judgments (both reported and important), deduplicated."""
    reported = await crawl_all_judgments("reported")
    important = await crawl_all_judgments("important")

    # Deduplicate by O_ID, preferring reported over important
    seen_ids = {r.o_id for r in reported}
    combined = list(reported)
    for rec in important:
        if rec.o_id not in seen_ids:
            seen_ids.add(rec.o_id)
            combined.append(rec)

    logger.info(
        "Combined: %d reported + %d important = %d total "
        "(%d unique after dedup)",
        len(reported), len(important), len(reported) + len(important),
        len(combined),
    )
    return combined


async def search_by_keyword(
    keyword: str,
    year: int | None = None,
) -> list[JudgmentRecord]:
    """Search judgments by keyword using the srchDecision1 endpoint.

    Args:
        keyword: Search term (minimum 5 characters on the website).
        year: Filter by year. None or 0 for all years.
    """
    payload = {
        "PKYWRD": keyword,
        "PCSEKWYR": str(year) if year else "0",
        "PAFR": "0",
        "PISSWS": "0",
    }

    raw_records = await _post_json(KEYWORD_SEARCH_ENDPOINT, payload)
    records = parse_api_records(raw_records, "keyword_search", KEYWORD_SEARCH_ENDPOINT)

    logger.info(
        "Keyword search '%s' (year=%s): %d records",
        keyword, year, len(records),
    )
    return records
