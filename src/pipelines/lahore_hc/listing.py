"""Crawl Lahore HC reported judgments and extract case metadata.

Single responsibility: form/search page → list of JudgmentRecord.

The LHC website at data.lhc.gov.pk serves reported judgments via:
1. A search form at /reported_judgments/judgments_approved_for_reporting
2. A dynamic PHP endpoint at /dynamic/approved_judgments_result_new.php?year=
3. PDFs hosted at sys.lhc.gov.pk/appjudgments/{year}LHC{number}.pdf

The site is behind FortiGuard IPS which blocks access from outside Pakistan.
When accessible, it uses a jQuery DataTable for results display.

Uses crawl4ai native features:
- session_id for multi-step form interaction
- JsonCssExtractionStrategy for structured row extraction
- wait_until="networkidle" for reliability

Expected table columns (based on similar LHC court interfaces):
  0: S.No (serial number)
  1: Case No (case number)
  2: Case Title (parties)
  3: Judge Name (deciding judge)
  4: LHC Citation (e.g. "2024 LHC 4177")
  5: Other Citation (PLD, CLC, etc.)
  6: Category (Criminal, Civil, etc.)
  7: Decision Date (dd-mm-yyyy or dd/mm/yyyy)
  8: Judgment (PDF link)
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date

from pydantic import BaseModel

from .constants import JUDGMENTS_URL, PDF_BASE_URL
from .errors import CrawlError

logger = logging.getLogger(__name__)


class JudgmentRecord(BaseModel):
    """A single judgment row extracted from the LHC DataTable."""

    serial: int
    case_number: str
    case_title: str
    judge_name: str
    lhc_citation: str
    other_citation: str
    category: str
    decision_date: str
    decision_date_parsed: date | None = None
    pdf_url: str
    source_url: str


def _parse_date(raw: str) -> date | None:
    """Parse date string in dd-mm-yyyy or dd/mm/yyyy format."""
    raw = raw.strip()
    if not raw:
        return None
    try:
        # Handle both dd-mm-yyyy and dd/mm/yyyy
        parts = re.split(r"[-/]", raw)
        if len(parts) == 3:
            return date(int(parts[2]), int(parts[1]), int(parts[0]))
    except (ValueError, IndexError):
        pass
    logger.debug("Could not parse date: %s", raw)
    return None


def _normalize_pdf_url(raw_url: str) -> str:
    """Normalize a PDF URL to ensure it's absolute and well-formed.

    LHC PDFs are hosted at sys.lhc.gov.pk/appjudgments/ with the pattern
    {year}LHC{number}.pdf (e.g. 2024LHC4177.pdf).
    """
    raw_url = raw_url.strip()
    if not raw_url:
        return ""

    # Already absolute
    if raw_url.startswith("http://") or raw_url.startswith("https://"):
        return raw_url

    # Relative path — prepend base URL
    if raw_url.startswith("/"):
        return f"https://sys.lhc.gov.pk{raw_url}"

    # Just a filename like "2024LHC4177.pdf"
    if raw_url.endswith(".pdf"):
        return f"{PDF_BASE_URL}/{raw_url}"

    return raw_url


def _extract_pdf_url_from_html(html_snippet: str) -> str:
    """Extract PDF URL from an HTML snippet containing an <a> tag."""
    match = re.search(r'href=["\']([^"\']*\.pdf[^"\']*)["\']', html_snippet, re.I)
    if match:
        return _normalize_pdf_url(match.group(1))
    return ""


# Column names matching the expected LHC table headers
TABLE_HEADERS = [
    "S.No", "Case No", "Case Title", "Judge Name",
    "LHC Citation", "Other Citation", "Category",
    "Decision Date", "Judgment",
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
        row_dict = dict(zip(headers, row)) if headers else {}
        if not row_dict:
            if len(row) < 8:
                continue
            row_dict = dict(zip(TABLE_HEADERS, row))

        decision_date_raw = row_dict.get("Decision Date", "").strip()

        record = JudgmentRecord(
            serial=int(row_dict.get("S.No", 0) or 0),
            case_number=row_dict.get("Case No", "").strip(),
            case_title=row_dict.get("Case Title", "").strip(),
            judge_name=row_dict.get("Judge Name", "").strip(),
            lhc_citation=row_dict.get("LHC Citation", "").strip(),
            other_citation=row_dict.get("Other Citation", "").strip(),
            category=row_dict.get("Category", "").strip(),
            decision_date=decision_date_raw,
            decision_date_parsed=_parse_date(decision_date_raw),
            pdf_url=_extract_pdf_url_from_html(
                row_dict.get("Judgment", "")
            ),
            source_url=source_url,
        )
        records.append(record)

    return records


def parse_css_rows(raw_rows: list[dict], source_url: str) -> list[JudgmentRecord]:
    """Parse rows from JsonCssExtractionStrategy into JudgmentRecord models."""
    records = []
    for row in raw_rows:
        decision_date_raw = row.get("decision_date", "").strip()

        record = JudgmentRecord(
            serial=int(row.get("serial", 0) or 0),
            case_number=row.get("case_number", "").strip(),
            case_title=row.get("case_title", "").strip(),
            judge_name=row.get("judge_name", "").strip(),
            lhc_citation=row.get("lhc_citation", "").strip(),
            other_citation=row.get("other_citation", "").strip(),
            category=row.get("category", "").strip(),
            decision_date=decision_date_raw,
            decision_date_parsed=_parse_date(decision_date_raw),
            pdf_url=_normalize_pdf_url(row.get("pdf_url", "").strip()),
            source_url=source_url,
        )
        records.append(record)

    return records


# JsonCssExtractionStrategy schema for the LHC DataTable rows.
# The exact CSS selectors may need adjustment after verifying the live site
# structure from within Pakistan (site is geo-blocked by FortiGuard).
# These selectors follow the standard DataTable pattern used by Pakistani
# court websites (same infrastructure as PHC).
CSS_EXTRACTION_SCHEMA = {
    "name": "LHC Judgments",
    "baseSelector": "table tbody tr",
    "fields": [
        {"name": "serial", "selector": "td:nth-child(1)", "type": "text"},
        {"name": "case_number", "selector": "td:nth-child(2)", "type": "text"},
        {"name": "case_title", "selector": "td:nth-child(3)", "type": "text"},
        {"name": "judge_name", "selector": "td:nth-child(4)", "type": "text"},
        {"name": "lhc_citation", "selector": "td:nth-child(5)", "type": "text"},
        {"name": "other_citation", "selector": "td:nth-child(6)", "type": "text"},
        {"name": "category", "selector": "td:nth-child(7)", "type": "text"},
        {"name": "decision_date", "selector": "td:nth-child(8)", "type": "text"},
        {
            "name": "pdf_url",
            "selector": "td:nth-child(9) a",
            "type": "attribute",
            "attribute": "href",
        },
    ],
}


def _build_submit_js(year: int | None = None) -> str:
    """Build JavaScript to fill and submit the search form.

    The LHC form uses a year dropdown filter. Additional filters (judge,
    category) may be available but require live site verification.
    """
    parts = []
    if year is not None:
        # Try multiple common selector patterns for the year dropdown
        parts.append(f"""
        (function() {{
            var selectors = ['#year', '#ddlYear', 'select[name="year"]', 'select[name="ddlYear"]'];
            for (var i = 0; i < selectors.length; i++) {{
                var el = document.querySelector(selectors[i]);
                if (el) {{
                    el.value = '{year}';
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    break;
                }}
            }}
        }})();
        """)
    # Try multiple submit button selector patterns
    parts.append("""
    (function() {
        var selectors = [
            'input[type="submit"]', 'button[type="submit"]',
            '#btnSearch', '#btnSubmit', '.btn-primary',
            'input[value="Search"]', 'button:contains("Search")'
        ];
        for (var i = 0; i < selectors.length; i++) {
            var el = document.querySelector(selectors[i]);
            if (el) {
                el.click();
                break;
            }
        }
    })();
    """)
    return "\n".join(parts)


async def crawl_judgments(
    year: int | None = None,
    category: str | None = None,
) -> list[JudgmentRecord]:
    """Crawl LHC reported judgments by submitting the search form.

    Two-step crawl4ai session approach:
    1. Load form page, fill year field, submit (triggers navigation).
       crawl4ai handles the navigation automatically.
    2. On the results page (same session, js_only=True), expand DataTable
       to show all rows, then extract with JsonCssExtractionStrategy.

    The LHC site is behind FortiGuard IPS which blocks access from outside
    Pakistan. The crawler will raise CrawlError with a clear message if
    the site is unreachable or returns 403.

    Args:
        year: Filter by year (2010-2026). None for all years.
        category: Filter by category (client-side). None for all.

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

    submit_js = _build_submit_js(year)

    # Script 2: Expand DataTable to show all rows after results load
    expand_datatable_js = """
    (async () => {
        // Poll until jQuery DataTable is initialized (up to 15s)
        for (let i = 0; i < 30; i++) {
            if (typeof $ !== 'undefined' && $.fn.DataTable) {
                var tables = $('table').filter(function() {
                    return $.fn.DataTable.isDataTable(this);
                });
                if (tables.length > 0) {
                    var dt = tables.first().DataTable();
                    dt.page.len(-1).draw();
                    await new Promise(r => setTimeout(r, 500));
                    return;
                }
            }
            await new Promise(r => setTimeout(r, 500));
        }
    })();
    """

    extraction_strategy = JsonCssExtractionStrategy(
        schema=CSS_EXTRACTION_SCHEMA, verbose=False,
    )

    session_id = "lhc_session"

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Step 1: Load form page, fill, and submit
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
            # Check for FortiGuard / geo-block
            if result.status_code == 403:
                raise CrawlError(
                    "LHC site returned 403 Forbidden. The site is behind "
                    "FortiGuard IPS and may only be accessible from within "
                    "Pakistan. Error: " + (result.error_message or "")
                )
            raise CrawlError(f"Form submission failed: {result.error_message}")

        # Check for FortiGuard block in successful response
        if result.status_code == 403:
            raise CrawlError(
                "LHC site returned 403 Forbidden (FortiGuard IPS block). "
                "The site may only be accessible from within Pakistan."
            )

        # Step 2: Expand DataTable and extract data
        step2_config = CrawlerRunConfig(
            session_id=session_id,
            cache_mode=CacheMode.BYPASS,
            js_only=True,
            js_code=expand_datatable_js,
            wait_for="css:table",
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

    # Client-side category filter
    if category and records:
        before = len(records)
        records = [r for r in records if r.category.lower() == category.lower()]
        logger.info(
            "Category filter '%s': %d → %d records",
            category, before, len(records),
        )

    if not records:
        logger.warning(
            "No records found for year=%s category=%s",
            year, category,
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
