"""Crawl Sindh HC caselaw database and extract judgment metadata.

Single responsibility: page load + DataTable HTML -> list of JudgmentRecord.

The SHC caselaw site (caselaw.shc.gov.pk) organizes judgments by judge.
Each judge has a public page listing all their judgments in a jQuery DataTable.

Data source: https://caselaw.shc.gov.pk/caselaw/public/rpt-afr
    - Lists all judges with judgment counts
    - Each judge links to: reported-judgements-detail-all/{judge_id}/-1

Table columns (0-indexed):
  0: S.No.
  1: Citation (e.g. "2023 SHC KHI 1139" or "Nil")
  2: Case No. (e.g. "Criminal Appeal 91/2023 (S.B.)")
  3: Case Type (e.g. "Original Side", "Criminal Appellate Jurisdictions")
  4: Case Year
  5: Parties (e.g. "Umair Qadeer v. Muhammad Nasir & Another")
  6: Order_Date (DD-MMM-YY format, e.g. "15-MAY-23")
  7: A.F.R (Yes/No)
  8: Head Notes/Tag Line
  9: Bench (judge names)
  10: Apex Court
  11: Apex Status

PDF links: Case No. column contains <a href="download-file.php?doc=...&citation=...">
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from urllib.parse import urljoin

from pydantic import BaseModel

from .constants import BASE_URL, JUDGE_JUDGMENTS_URL_TEMPLATE, JUDGES_REPORT_URL
from .errors import CrawlError

logger = logging.getLogger(__name__)


class JudgmentRecord(BaseModel):
    """A single judgment row extracted from the SHC caselaw DataTable."""

    serial: int
    citation: str
    case_number: str
    case_type: str
    case_year: str
    parties: str
    order_date: str
    order_date_parsed: date | None = None
    afr: str
    head_notes: str
    bench: str
    apex_court: str
    apex_status: str
    pdf_url: str
    judge_id: int
    judge_name: str
    source_url: str


def _parse_date(raw: str) -> date | None:
    """Parse DD-MMM-YY date string (e.g. '15-MAY-23')."""
    raw = raw.strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%d-%b-%y").date()
    except ValueError:
        pass
    # Try full year format DD-MMM-YYYY
    try:
        return datetime.strptime(raw, "%d-%b-%Y").date()
    except ValueError:
        pass
    logger.debug("Could not parse date: %s", raw)
    return None


def _parse_case_number(raw: str) -> str:
    """Clean case number text (strip whitespace, normalize spaces)."""
    return re.sub(r"\s+", " ", raw.strip())


def _resolve_pdf_url(relative_url: str) -> str:
    """Resolve a relative PDF download URL to absolute.

    The SHC caselaw site uses <base href="/caselaw/"> so all relative hrefs
    resolve from https://caselaw.shc.gov.pk/caselaw/.
    """
    if not relative_url:
        return ""
    relative_url = relative_url.strip()
    if relative_url.startswith("http"):
        return relative_url
    # Resolve relative to <base href="/caselaw/">
    return urljoin(BASE_URL + "/", relative_url)


# JsonCssExtractionStrategy schema for the SHC DataTable rows.
# Captures PDF links (as href attributes on case number <a> tags).
CSS_EXTRACTION_SCHEMA = {
    "name": "SHC Judgments",
    "baseSelector": ".hasDataTable tbody tr",
    "fields": [
        {"name": "serial", "selector": "td:nth-child(1)", "type": "text"},
        {"name": "citation", "selector": "td:nth-child(2)", "type": "text"},
        {"name": "case_number", "selector": "td:nth-child(3)", "type": "text"},
        {
            "name": "pdf_url",
            "selector": "td:nth-child(3) a",
            "type": "attribute",
            "attribute": "href",
        },
        {"name": "case_type", "selector": "td:nth-child(4)", "type": "text"},
        {"name": "case_year", "selector": "td:nth-child(5)", "type": "text"},
        {"name": "parties", "selector": "td:nth-child(6)", "type": "text"},
        {"name": "order_date", "selector": "td:nth-child(7)", "type": "text"},
        {"name": "afr", "selector": "td:nth-child(8)", "type": "text"},
        {"name": "head_notes", "selector": "td:nth-child(9)", "type": "text"},
        {"name": "bench", "selector": "td:nth-child(10)", "type": "text"},
        {"name": "apex_court", "selector": "td:nth-child(11)", "type": "text"},
        {"name": "apex_status", "selector": "td:nth-child(12)", "type": "text"},
    ],
}

# Schema for the judges report page (rpt-afr)
JUDGES_CSS_SCHEMA = {
    "name": "SHC Judges",
    "baseSelector": "table tbody tr",
    "fields": [
        {"name": "serial", "selector": "td:nth-child(1)", "type": "text"},
        {"name": "judge_name", "selector": "td:nth-child(2)", "type": "text"},
        {
            "name": "total_url",
            "selector": "td:nth-child(3) a",
            "type": "attribute",
            "attribute": "href",
        },
        {"name": "total", "selector": "td:nth-child(3)", "type": "text"},
        {
            "name": "afr_url",
            "selector": "td:nth-child(4) a",
            "type": "attribute",
            "attribute": "href",
        },
        {"name": "afr", "selector": "td:nth-child(4)", "type": "text"},
    ],
}


def parse_css_rows(
    raw_rows: list[dict],
    source_url: str,
    judge_id: int,
    judge_name: str,
) -> list[JudgmentRecord]:
    """Parse rows from JsonCssExtractionStrategy into JudgmentRecord models."""
    records = []
    for row in raw_rows:
        order_date_raw = row.get("order_date", "").strip()
        pdf_url_raw = row.get("pdf_url", "").strip()

        record = JudgmentRecord(
            serial=int(row.get("serial", 0) or 0),
            citation=row.get("citation", "").strip(),
            case_number=_parse_case_number(row.get("case_number", "")),
            case_type=row.get("case_type", "").strip(),
            case_year=row.get("case_year", "").strip(),
            parties=row.get("parties", "").strip(),
            order_date=order_date_raw,
            order_date_parsed=_parse_date(order_date_raw),
            afr=row.get("afr", "").strip(),
            head_notes=row.get("head_notes", "").strip(),
            bench=row.get("bench", "").strip(),
            apex_court=row.get("apex_court", "").strip(),
            apex_status=row.get("apex_status", "").strip(),
            pdf_url=_resolve_pdf_url(pdf_url_raw),
            judge_id=judge_id,
            judge_name=judge_name,
            source_url=source_url,
        )
        records.append(record)

    return records


def parse_judge_rows(raw_rows: list[dict]) -> list[dict]:
    """Parse the judges report table into judge info dicts.

    Returns list of dicts with keys: judge_id, judge_name, total, afr.
    """
    judges = []
    for row in raw_rows:
        # Extract judge_id from the total_url (pattern: .../{judge_id}/-1)
        total_url = row.get("total_url", "")
        match = re.search(r"/(\d+)/-1", total_url)
        if not match:
            continue

        judge_id = int(match.group(1))
        judge_name = row.get("judge_name", "").strip()
        total_str = row.get("total", "").strip().replace(",", "")
        afr_str = row.get("afr", "").strip().replace(",", "")

        judges.append({
            "judge_id": judge_id,
            "judge_name": judge_name,
            "total": int(total_str) if total_str.isdigit() else 0,
            "afr": int(afr_str) if afr_str.isdigit() else 0,
        })

    return judges


async def crawl_judges_list() -> list[dict]:
    """Crawl the judges report page to get all judge IDs and names.

    Returns list of dicts with keys: judge_id, judge_name, total, afr.

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
        schema=JUDGES_CSS_SCHEMA, verbose=False,
    )

    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_until="networkidle",
        wait_for="css:.hasDataTable",
        delay_before_return_html=2.0,
        extraction_strategy=extraction_strategy,
        page_timeout=60000,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=JUDGES_REPORT_URL, config=config)
        if not result.success:
            raise CrawlError(f"Failed to load judges report: {result.error_message}")

        if not result.extracted_content:
            raise CrawlError("No data extracted from judges report page")

        try:
            raw_rows = json.loads(result.extracted_content)
        except json.JSONDecodeError as e:
            raise CrawlError(f"Failed to parse judges JSON: {e}") from e

    judges = parse_judge_rows(raw_rows)
    logger.info("Found %d judges on SHC caselaw site", len(judges))
    return judges


async def crawl_judge_judgments(
    judge_id: int,
    judge_name: str,
    afr_only: bool = False,
) -> list[JudgmentRecord]:
    """Crawl all judgments for a specific judge.

    The SHC caselaw site loads ALL judgments for a judge on a single page
    in a jQuery DataTable. We need to expand the table to show all rows
    before extracting.

    Args:
        judge_id: Numeric judge identifier.
        judge_name: Judge's display name for record metadata.
        afr_only: If True, only crawl AFR (approved for reporting) judgments.

    Returns:
        List of JudgmentRecord extracted from the judge's page.

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

    filter_value = "AFR/AFR" if afr_only else "-1"
    url = JUDGE_JUDGMENTS_URL_TEMPLATE.format(
        judge_id=judge_id, filter=filter_value,
    )

    browser_config = BrowserConfig(
        headless=True,
        extra_args=["--ignore-certificate-errors"],
    )

    # JavaScript to expand DataTable to show all rows.
    # The table uses jQuery DataTable with length menu [10, 25, 50, "All"].
    # We set page length to -1 (all) and redraw.
    expand_datatable_js = """
    (async () => {
        // Poll until DataTable is initialized (up to 15s)
        for (let i = 0; i < 30; i++) {
            if (typeof $ !== 'undefined' && $.fn.DataTable
                && $.fn.DataTable.isDataTable('.hasDataTable')) {
                const dt = $('.hasDataTable').DataTable();
                dt.page.len(-1).draw();
                await new Promise(r => setTimeout(r, 1000));
                return;
            }
            await new Promise(r => setTimeout(r, 500));
        }
    })();
    """

    extraction_strategy = JsonCssExtractionStrategy(
        schema=CSS_EXTRACTION_SCHEMA, verbose=False,
    )

    session_id = f"shc_judge_{judge_id}"

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Step 1: Load the page and wait for DataTable
        step1_config = CrawlerRunConfig(
            session_id=session_id,
            cache_mode=CacheMode.BYPASS,
            wait_until="networkidle",
            wait_for="css:.hasDataTable",
            delay_before_return_html=3.0,
            page_timeout=90000,
        )
        result = await crawler.arun(url=url, config=step1_config)
        if not result.success:
            raise CrawlError(
                f"Failed to load judge page {judge_id}: {result.error_message}"
            )

        # Step 2: Expand DataTable to show all rows and extract
        step2_config = CrawlerRunConfig(
            session_id=session_id,
            cache_mode=CacheMode.BYPASS,
            js_only=True,
            js_code=expand_datatable_js,
            delay_before_return_html=3.0,
            extraction_strategy=extraction_strategy,
            page_timeout=60000,
        )
        result = await crawler.arun(url=url, config=step2_config)

        if not result.success:
            raise CrawlError(
                f"Data extraction failed for judge {judge_id}: {result.error_message}"
            )

        records = []
        if result.extracted_content:
            try:
                raw_rows = json.loads(result.extracted_content)
                records = parse_css_rows(raw_rows, url, judge_id, judge_name)
            except json.JSONDecodeError as e:
                raise CrawlError(f"Failed to parse extracted JSON: {e}") from e

    if not records:
        logger.warning(
            "No records found for judge %s (ID=%d)", judge_name, judge_id,
        )

    logger.info(
        "Crawled %d judgment records for judge %s (ID=%d)",
        len(records), judge_name, judge_id,
    )
    return records


async def crawl_all_judges() -> list[JudgmentRecord]:
    """Crawl judgments for all judges listed on the SHC caselaw site.

    First fetches the judges list, then crawls each judge's page sequentially.
    """
    judges = await crawl_judges_list()
    all_records: list[JudgmentRecord] = []

    for judge in judges:
        try:
            records = await crawl_judge_judgments(
                judge_id=judge["judge_id"],
                judge_name=judge["judge_name"],
            )
            all_records.extend(records)
            logger.info(
                "Judge %s: %d records (running total: %d)",
                judge["judge_name"], len(records), len(all_records),
            )
        except CrawlError as e:
            logger.error(
                "Failed to crawl judge %s (ID=%d): %s",
                judge["judge_name"], judge["judge_id"], e,
            )

    logger.info("Total: %d judgment records from %d judges", len(all_records), len(judges))
    return all_records
