"""Crawl Peshawar HC reported judgments and extract case metadata from the table.

Single responsibility: form submission + DataTable HTML → list of JudgmentRecord.

The PHC website uses a server-rendered HTML form (POST) that returns ALL matching
rows in a client-side jQuery DataTable (no server-side pagination).

Uses crawl4ai native features:
- session_id + js_only for multi-step form interaction
- JsonCssExtractionStrategy for row-level extraction with PDF href attributes

Table columns (0-indexed):
  0: S.No
  1: Case (case number + title)
  2: Remarks (headnote / summary)
  3: Other Citation (e.g. "2025 PLJ Pesh. 100")
  4: PHC Neutral Citation
  5: Decision Date (dd-mm-yyyy)
  6: S.C.Status
  7: Category (Criminal, Civil, etc.)
  8: Judgment (PDF link)
  9: SC Judgment (PDF link, if any)
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date

from pydantic import BaseModel

from .constants import JUDGMENTS_URL
from .errors import CrawlError

logger = logging.getLogger(__name__)


class JudgmentRecord(BaseModel):
    """A single judgment row extracted from the PHC DataTable."""

    serial: int
    case_number: str
    case_title: str
    remarks: str
    other_citation: str
    neutral_citation: str
    decision_date: str
    decision_date_parsed: date | None = None
    sc_status: str
    category: str
    pdf_url: str
    sc_pdf_url: str
    source_url: str


def _parse_case_field(raw: str) -> tuple[str, str]:
    """Split 'W.P No. 1395-M of 2019 Sayyed Mukammal Shah Vs Mst. Nasira' into number + title."""
    raw = raw.strip()
    match = re.match(
        r"^(.+?(?:of|OF)\s+\d{4})\s+(.+)$",
        raw,
    )
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return raw, ""


def _parse_date(raw: str) -> date | None:
    """Parse dd-mm-yyyy date string."""
    raw = raw.strip()
    if not raw:
        return None
    try:
        parts = raw.split("-")
        if len(parts) == 3:
            return date(int(parts[2]), int(parts[1]), int(parts[0]))
    except (ValueError, IndexError):
        pass
    logger.debug("Could not parse date: %s", raw)
    return None


# Column names matching the PHC table headers
TABLE_HEADERS = [
    "S.No", "Case", "Remarks", "Other Citation",
    "PHC Neutral Citation", "Decision Date", "S.C.Status",
    "Category", "Judgment", "SC Judgment",
]


def parse_table_data(table_data: dict, source_url: str) -> list[JudgmentRecord]:
    """Parse a crawl4ai table extraction result into JudgmentRecord models.

    Args:
        table_data: Dict with 'headers' and 'rows' from DefaultTableExtraction.
        source_url: Source URL for provenance tracking.
    """
    headers = table_data.get("headers", [])
    rows = table_data.get("rows", [])

    if not rows:
        return []

    records = []
    for row in rows:
        # Map by header position — handle variable header names
        row_dict = dict(zip(headers, row)) if headers else {}
        if not row_dict:
            # Fallback: use positional access
            if len(row) < 9:
                continue
            row_dict = dict(zip(TABLE_HEADERS, row))

        case_raw = row_dict.get("Case", "")
        case_number, case_title = _parse_case_field(case_raw)
        decision_date_raw = row_dict.get("Decision Date", "").strip()

        # The Judgment and SC Judgment columns contain HTML with <a> tags.
        # crawl4ai table extraction gives us the cell text, but we need the href.
        # We extract PDF URLs separately via JsonCssExtractionStrategy.
        record = JudgmentRecord(
            serial=int(row_dict.get("S.No", 0) or 0),
            case_number=case_number,
            case_title=case_title,
            remarks=row_dict.get("Remarks", "").strip(),
            other_citation=row_dict.get("Other Citation", "").strip(),
            neutral_citation=row_dict.get("PHC Neutral Citation", "").strip(),
            decision_date=decision_date_raw,
            decision_date_parsed=_parse_date(decision_date_raw),
            sc_status=row_dict.get("S.C.Status", "").strip(),
            category=row_dict.get("Category", "").strip(),
            pdf_url="",  # Populated by CSS extraction step
            sc_pdf_url="",  # Populated by CSS extraction step
            source_url=source_url,
        )
        records.append(record)

    return records


def parse_css_rows(raw_rows: list[dict], source_url: str) -> list[JudgmentRecord]:
    """Parse rows from JsonCssExtractionStrategy into JudgmentRecord models."""
    records = []
    for row in raw_rows:
        case_number, case_title = _parse_case_field(row.get("case", ""))
        decision_date_raw = row.get("decision_date", "").strip()

        record = JudgmentRecord(
            serial=int(row.get("serial", 0) or 0),
            case_number=case_number,
            case_title=case_title,
            remarks=row.get("remarks", "").strip(),
            other_citation=row.get("other_citation", "").strip(),
            neutral_citation=row.get("neutral_citation", "").strip(),
            decision_date=decision_date_raw,
            decision_date_parsed=_parse_date(decision_date_raw),
            sc_status=row.get("sc_status", "").strip(),
            category=row.get("category", "").strip(),
            pdf_url=row.get("pdf_url", "").strip(),
            sc_pdf_url=row.get("sc_pdf_url", "").strip(),
            source_url=source_url,
        )
        records.append(record)

    return records


# JsonCssExtractionStrategy schema for the PHC DataTable rows.
# This captures PDF links (as href attributes) which DefaultTableExtraction misses.
CSS_EXTRACTION_SCHEMA = {
    "name": "PHC Judgments",
    "baseSelector": "#employee_list tbody tr",
    "fields": [
        {"name": "serial", "selector": "td:nth-child(1)", "type": "text"},
        {"name": "case", "selector": "td:nth-child(2)", "type": "text"},
        {"name": "remarks", "selector": "td:nth-child(3)", "type": "text"},
        {"name": "other_citation", "selector": "td:nth-child(4)", "type": "text"},
        {"name": "neutral_citation", "selector": "td:nth-child(5)", "type": "text"},
        {"name": "decision_date", "selector": "td:nth-child(6)", "type": "text"},
        {"name": "sc_status", "selector": "td:nth-child(7)", "type": "text"},
        {"name": "category", "selector": "td:nth-child(8)", "type": "text"},
        {
            "name": "pdf_url",
            "selector": "td:nth-child(9) a",
            "type": "attribute",
            "attribute": "href",
        },
        {
            "name": "sc_pdf_url",
            "selector": "td:nth-child(10) a",
            "type": "attribute",
            "attribute": "href",
        },
    ],
}


def _build_submit_js(
    year: int | None = None,
    judge: str | None = None,
) -> str:
    """Build JavaScript to fill and submit the search form.

    The PHC form uses numeric option values, not text labels:
    - Year: "2024" (text matches value)
    - Judge: numeric IDs like "26", "25", etc.

    NOTE: Category filter is NOT set via form because the PHC server returns
    HTTP 500 for any category value other than 0 (all). Category filtering
    is done client-side in Python after extraction.
    """
    parts = []
    if year is not None:
        parts.append(f"document.querySelector('#year').value = '{year}';")
    if judge is not None:
        parts.append(f"document.querySelector('#judge').value = '{judge}';")
    parts.append("document.querySelector('input[type=\"submit\"]').click();")
    return "\n".join(parts)


async def crawl_judgments(
    year: int | None = None,
    category: str | None = None,
    judge: str | None = None,
) -> list[JudgmentRecord]:
    """Crawl PHC reported judgments by submitting the search form.

    Two-step crawl4ai session approach:
    1. Load form page, fill year/judge fields, submit (triggers navigation).
       crawl4ai's robust_execute_user_script handles the context-destroyed
       error from navigation automatically.
    2. On the results page (same session, js_only=True), expand DataTable
       to show all rows, then extract with JsonCssExtractionStrategy.

    Category filtering is done client-side because the PHC server returns
    HTTP 500 for any category value other than 0 (all).

    Args:
        year: Filter by year (2010-2026). None for all years.
        category: Filter by category (client-side). None for all.
        judge: Filter by judge name. None for all.

    Returns:
        List of JudgmentRecord extracted from the results table.

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

    # Script 1: Fill form and submit (triggers navigation to results page).
    # crawl4ai's robust_execute_user_script catches "context destroyed" from
    # the navigation and waits for the new page to load before continuing.
    submit_js = _build_submit_js(year, judge)

    # Script 2: Runs on the results page after navigation completes.
    # Polls for DataTable initialization (jQuery loads async), then shows all rows.
    expand_datatable_js = """
    (async () => {
        // Poll until jQuery DataTable is initialized (up to 15s)
        for (let i = 0; i < 30; i++) {
            if (typeof $ !== 'undefined' && $.fn.DataTable
                && $.fn.DataTable.isDataTable('#employee_list')) {
                const dt = $('#employee_list').DataTable();
                dt.page.len(-1).draw();
                await new Promise(r => setTimeout(r, 500));
                return;
            }
            await new Promise(r => setTimeout(r, 500));
        }
    })();
    """

    extraction_strategy = JsonCssExtractionStrategy(
        schema=CSS_EXTRACTION_SCHEMA, verbose=False,
    )

    session_id = "phc_session"

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Step 1: Load form page, fill, and submit. The form submit triggers
        # a full page navigation which crawl4ai handles automatically via
        # robust_execute_user_script's "context destroyed" handling.
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
            raise CrawlError(f"Form submission failed: {result.error_message}")

        # Step 2: On the results page (same session), expand DataTable and extract.
        step2_config = CrawlerRunConfig(
            session_id=session_id,
            cache_mode=CacheMode.BYPASS,
            js_only=True,
            js_code=expand_datatable_js,
            wait_for="css:#employee_list",
            delay_before_return_html=2.0,
            extraction_strategy=extraction_strategy,
            page_timeout=30000,
        )
        result = await crawler.arun(url=JUDGMENTS_URL, config=step2_config)

        if not result.success:
            raise CrawlError(f"Data extraction failed: {result.error_message}")

        # Parse extracted content
        records = []
        if result.extracted_content:
            try:
                raw_rows = json.loads(result.extracted_content)
                records = parse_css_rows(raw_rows, JUDGMENTS_URL)
            except json.JSONDecodeError as e:
                raise CrawlError(f"Failed to parse extracted JSON: {e}") from e

    # Client-side category filter (PHC server returns 500 for category != 0)
    if category and records:
        before = len(records)
        records = [r for r in records if r.category.lower() == category.lower()]
        logger.info(
            "Category filter '%s': %d → %d records",
            category, before, len(records),
        )

    if not records:
        logger.warning(
            "No records found for year=%s category=%s judge=%s",
            year, category, judge,
        )

    logger.info(
        "Crawled %d judgment records (year=%s, category=%s)",
        len(records), year, category,
    )
    return records


async def crawl_all_years() -> list[JudgmentRecord]:
    """Crawl all reported judgments (all years, all categories)."""
    return await crawl_judgments(year=None, category=None)


async def crawl_by_year(year: int) -> list[JudgmentRecord]:
    """Crawl reported judgments for a specific year."""
    return await crawl_judgments(year=year, category=None)
