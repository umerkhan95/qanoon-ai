"""Crawl Federal Shariat Court judgments and extract case metadata.

Single responsibility: page load + HTML extraction → list of JudgmentRecord.

The FSC website (post-redesign) has two judgment pages:
1. /en/leading-judgements/ — curated table with S.No, Title/Reference, Date, Download link
2. /en/judgments/ — search form (case number, party name, judge)

The leading judgments page is a static table (no DataTable/AJAX), making it the
more reliable extraction target. The search page requires form interaction.

Table columns on /en/leading-judgements/:
  0: S.No
  1: Title Reference with Date of Decision
  2: Download Judgment (PDF link)

PDF URL pattern: /Judgments/{case-file-name}.pdf
Case number pattern: "Cr.App.No.15.I.of.2018" or "Shariat Petition No. 10-I of 2023"
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date

from pydantic import BaseModel

from .constants import BASE_URL, JUDGMENTS_URL, LEADING_JUDGMENTS_URL
from .errors import CrawlError

logger = logging.getLogger(__name__)


class JudgmentRecord(BaseModel):
    """A single judgment record extracted from the FSC website."""

    serial: int
    case_number: str
    case_title: str
    case_type: str
    decision_date: str
    decision_date_parsed: date | None = None
    pdf_url: str
    source_url: str


def _parse_date(raw: str) -> date | None:
    """Parse various date formats found in FSC records.

    Handles:
    - dd.mm.yyyy (e.g., "19.03.2025")
    - dd-mm-yyyy (e.g., "19-03-2025")
    - dd/mm/yyyy (e.g., "19/03/2025")
    """
    raw = raw.strip()
    if not raw:
        return None
    try:
        # Normalize separators
        normalized = raw.replace("/", "-").replace(".", "-")
        parts = normalized.split("-")
        if len(parts) == 3:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            # Handle 2-digit years
            if year < 100:
                year += 1900 if year > 50 else 2000
            return date(year, month, day)
    except (ValueError, IndexError):
        pass
    logger.debug("Could not parse date: %s", raw)
    return None


def _extract_date_from_title(title: str) -> str:
    """Extract date string from title text.

    FSC titles often include the date like:
    "... dated 19.03.2025" or "Decision Date: 19-03-2025"
    or just a date at the end in parentheses "(19.03.2025)"
    """
    # Pattern: "dated DD.MM.YYYY" or "dated DD-MM-YYYY"
    match = re.search(
        r"(?:dated|decision\s+date[:\s]*)\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        title,
        re.IGNORECASE,
    )
    if match:
        return match.group(1)

    # Pattern: date in parentheses at end
    match = re.search(r"\((\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\)\s*$", title)
    if match:
        return match.group(1)

    # Pattern: standalone date (DD.MM.YYYY) anywhere
    match = re.search(r"(\d{1,2}[./-]\d{1,2}[./-]\d{4})", title)
    if match:
        return match.group(1)

    return ""


def _extract_case_number(title: str) -> str:
    """Extract case number from the title text.

    Examples:
    - "Shariat Petition No. 10-I of 2023" → "Shariat Petition No. 10-I of 2023"
    - "Cr.App.No.15.I.of.2018" → "Cr.App.No.15.I.of.2018"
    - "Criminal Appeal No. 23 - Q - of 2005" → "Criminal Appeal No. 23 - Q - of 2005"
    """
    # Pattern: Various case number formats with "No." and "of YYYY"
    match = re.search(
        r"((?:Cr\.?\s*(?:App|Rev|M)|J\.?Cr\.?A|Sh\.?P|S\.?P|R\.?Sr\.?P|W\.?P|"
        r"Shariat\s+Petition|Criminal\s+(?:Appeal|Revision|Miscellaneous)|"
        r"Jail\s+Criminal\s+Appeal|Review\s+Shariat\s+Petition|"
        r"Writ\s+Petition)"
        r"[.\s]*No\.?\s*[\d]+[\s.\-]*[A-Z]?[\s.\-]*(?:of|OF)\s*\d{4})",
        title,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()

    # Simpler pattern: "No. X-Y of YYYY"
    match = re.search(
        r"([\w.\s]+No\.?\s*[\d]+[\s\-]*[\w]*[\s\-]*(?:of|OF)\s*\d{4})",
        title,
    )
    if match:
        return match.group(1).strip()

    return title.strip()


def _classify_case_type(case_number: str) -> str:
    """Classify the case type from the case number prefix."""
    lower = case_number.lower()
    if "shariat petition" in lower or "sh.p" in lower or "s.p" in lower:
        if "review" in lower or "r.sr.p" in lower:
            return "Review Shariat Petition"
        return "Shariat Petition"
    if "jail" in lower or "j.cr" in lower:
        return "Jail Criminal Appeal"
    if "cr.app" in lower or "criminal appeal" in lower or "cr.a" in lower:
        return "Criminal Appeal"
    if "cr.rev" in lower or "criminal revision" in lower:
        return "Criminal Revision"
    if "cr.m" in lower or "criminal miscellaneous" in lower:
        return "Criminal Miscellaneous"
    if "w.p" in lower or "writ petition" in lower:
        return "Writ Petition"
    return "Other"


def _normalize_pdf_url(raw_url: str) -> str:
    """Normalize a PDF URL to absolute form."""
    raw_url = raw_url.strip()
    if not raw_url:
        return ""
    if raw_url.startswith("http"):
        return raw_url
    if raw_url.startswith("/"):
        return BASE_URL + raw_url
    return BASE_URL + "/" + raw_url


def parse_leading_judgments_rows(
    raw_rows: list[dict],
    source_url: str,
) -> list[JudgmentRecord]:
    """Parse rows from JsonCssExtractionStrategy for the leading judgments page."""
    records = []
    for row in raw_rows:
        title = row.get("title", "").strip()
        if not title:
            continue

        case_number = _extract_case_number(title)
        case_type = _classify_case_type(case_number)
        date_str = _extract_date_from_title(title)
        pdf_url = _normalize_pdf_url(row.get("pdf_url", ""))

        # Case title is the full title text minus the case number
        case_title = title.replace(case_number, "").strip(" -–—().,")

        record = JudgmentRecord(
            serial=int(row.get("serial", 0) or 0),
            case_number=case_number,
            case_title=case_title if case_title else title,
            case_type=case_type,
            decision_date=date_str,
            decision_date_parsed=_parse_date(date_str),
            pdf_url=pdf_url,
            source_url=source_url,
        )
        records.append(record)

    return records


def parse_judgment_search_rows(
    raw_rows: list[dict],
    source_url: str,
) -> list[JudgmentRecord]:
    """Parse rows from the judgment search results page."""
    records = []
    for row in raw_rows:
        case_number = row.get("case_number", "").strip()
        title = row.get("title", "").strip()
        date_str = row.get("decision_date", "").strip()
        pdf_url = _normalize_pdf_url(row.get("pdf_url", ""))

        if not case_number and not title:
            continue

        if not case_number:
            case_number = _extract_case_number(title)

        case_type = _classify_case_type(case_number)

        record = JudgmentRecord(
            serial=int(row.get("serial", 0) or 0),
            case_number=case_number,
            case_title=title,
            case_type=case_type,
            decision_date=date_str,
            decision_date_parsed=_parse_date(date_str),
            pdf_url=pdf_url,
            source_url=source_url,
        )
        records.append(record)

    return records


# JsonCssExtractionStrategy schema for the FSC leading judgments table.
# The table has 3 columns: S.No, Title/Reference with Date, Download link.
CSS_LEADING_JUDGMENTS_SCHEMA = {
    "name": "FSC Leading Judgments",
    "baseSelector": "table tbody tr",
    "fields": [
        {"name": "serial", "selector": "td:nth-child(1)", "type": "text"},
        {"name": "title", "selector": "td:nth-child(2)", "type": "text"},
        {
            "name": "pdf_url",
            "selector": "td:nth-child(3) a, td:nth-child(2) a",
            "type": "attribute",
            "attribute": "href",
        },
    ],
}

# Schema for the judgment search results page.
# Structure may vary — this is a best-effort schema based on recon.
CSS_JUDGMENT_SEARCH_SCHEMA = {
    "name": "FSC Judgment Search Results",
    "baseSelector": "table tbody tr",
    "fields": [
        {"name": "serial", "selector": "td:nth-child(1)", "type": "text"},
        {"name": "case_number", "selector": "td:nth-child(2)", "type": "text"},
        {"name": "title", "selector": "td:nth-child(3)", "type": "text"},
        {"name": "decision_date", "selector": "td:nth-child(4)", "type": "text"},
        {
            "name": "pdf_url",
            "selector": "td a[href*='.pdf'], td a[href*='Judgment']",
            "type": "attribute",
            "attribute": "href",
        },
    ],
}


async def crawl_leading_judgments() -> list[JudgmentRecord]:
    """Crawl the FSC leading judgments page.

    The leading judgments page is a static table (no AJAX/DataTable),
    so a single page load + CSS extraction suffices.

    Returns:
        List of JudgmentRecord extracted from the leading judgments table.

    Raises:
        CrawlError: If the page cannot be loaded or extraction fails.
    """
    from crawl4ai import (
        AsyncWebCrawler,
        BrowserConfig,
        CacheMode,
        CrawlerRunConfig,
        JsonCssExtractionStrategy,
    )

    browser_config = BrowserConfig(
        headless=True,
        extra_args=["--ignore-certificate-errors"],
    )

    extraction_strategy = JsonCssExtractionStrategy(
        schema=CSS_LEADING_JUDGMENTS_SCHEMA, verbose=False,
    )

    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_until="networkidle",
        delay_before_return_html=3.0,
        page_timeout=90000,
        extraction_strategy=extraction_strategy,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=LEADING_JUDGMENTS_URL, config=config)

        if not result.success:
            raise CrawlError(
                f"Failed to load leading judgments page: {result.error_message}"
            )

        records = []
        if result.extracted_content:
            try:
                raw_rows = json.loads(result.extracted_content)
                records = parse_leading_judgments_rows(
                    raw_rows, LEADING_JUDGMENTS_URL,
                )
            except json.JSONDecodeError as e:
                raise CrawlError(
                    f"Failed to parse extracted JSON: {e}"
                ) from e

    if not records:
        logger.warning("No records found on leading judgments page")

    logger.info("Crawled %d leading judgment records", len(records))
    return records


async def crawl_judgment_search(
    case_number: str | None = None,
    party_name: str | None = None,
    judge_name: str | None = None,
) -> list[JudgmentRecord]:
    """Crawl the FSC judgment search page by submitting search criteria.

    The search page accepts case number, party name, or judge name.
    Uses a two-step crawl4ai session approach:
    1. Load search page and submit form with search criteria.
    2. Extract results from the response table.

    Args:
        case_number: Search by case number.
        party_name: Search by party name.
        judge_name: Search by judge name.

    Returns:
        List of JudgmentRecord extracted from search results.

    Raises:
        CrawlError: If the page cannot be loaded or extraction fails.
    """
    from crawl4ai import (
        AsyncWebCrawler,
        BrowserConfig,
        CacheMode,
        CrawlerRunConfig,
        JsonCssExtractionStrategy,
    )

    browser_config = BrowserConfig(
        headless=True,
        extra_args=["--ignore-certificate-errors"],
    )

    # Build form submission JavaScript
    fill_parts = []
    if case_number:
        fill_parts.append(
            f"const caseInput = document.querySelector('input[name*=\"case\"], "
            f"input[placeholder*=\"case\" i]');"
            f"if (caseInput) caseInput.value = '{case_number}';"
        )
    if party_name:
        fill_parts.append(
            f"const partyInput = document.querySelector('input[name*=\"party\"], "
            f"input[placeholder*=\"party\" i]');"
            f"if (partyInput) partyInput.value = '{party_name}';"
        )
    if judge_name:
        fill_parts.append(
            f"const judgeInput = document.querySelector('input[name*=\"judge\"], "
            f"select[name*=\"judge\"]');"
            f"if (judgeInput) judgeInput.value = '{judge_name}';"
        )
    fill_parts.append(
        "const submitBtn = document.querySelector("
        "'input[type=\"submit\"], button[type=\"submit\"]');"
        "if (submitBtn) submitBtn.click();"
    )
    submit_js = "\n".join(fill_parts)

    extraction_strategy = JsonCssExtractionStrategy(
        schema=CSS_JUDGMENT_SEARCH_SCHEMA, verbose=False,
    )

    session_id = "fsc_search_session"

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Step 1: Load search page and submit form
        step1_config = CrawlerRunConfig(
            session_id=session_id,
            cache_mode=CacheMode.BYPASS,
            wait_until="networkidle",
            js_code=submit_js,
            delay_before_return_html=5.0,
            page_timeout=90000,
        )
        result = await crawler.arun(url=JUDGMENTS_URL, config=step1_config)
        if not result.success:
            raise CrawlError(
                f"Search form submission failed: {result.error_message}"
            )

        # Step 2: Extract results from the loaded page
        step2_config = CrawlerRunConfig(
            session_id=session_id,
            cache_mode=CacheMode.BYPASS,
            js_only=True,
            delay_before_return_html=2.0,
            extraction_strategy=extraction_strategy,
            page_timeout=30000,
        )
        result = await crawler.arun(url=JUDGMENTS_URL, config=step2_config)

        if not result.success:
            raise CrawlError(
                f"Search result extraction failed: {result.error_message}"
            )

        records = []
        if result.extracted_content:
            try:
                raw_rows = json.loads(result.extracted_content)
                records = parse_judgment_search_rows(raw_rows, JUDGMENTS_URL)
            except json.JSONDecodeError as e:
                raise CrawlError(
                    f"Failed to parse extracted JSON: {e}"
                ) from e

    if not records:
        logger.warning(
            "No records found for case_number=%s party=%s judge=%s",
            case_number, party_name, judge_name,
        )

    logger.info(
        "Crawled %d judgment records (case=%s, party=%s, judge=%s)",
        len(records), case_number, party_name, judge_name,
    )
    return records
