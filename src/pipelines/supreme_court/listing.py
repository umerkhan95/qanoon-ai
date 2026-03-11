"""Crawl Supreme Court of Pakistan judgment listings and extract case metadata.

Single responsibility: WordPress category page crawl → list of JudgmentRecord.

The SC website is a WordPress site behind Akamai CDN. Judgments are listed as
blog posts under /category/judgements/ with standard WordPress pagination.

Uses crawl4ai with anti-bot features:
- BrowserConfig with enable_stealth for Akamai bypass
- CrawlerRunConfig with magic=True for enhanced evasion
- JsonCssExtractionStrategy for structured post extraction
- Maintenance detection before proceeding

Site was down for maintenance as of March 2026. The pipeline detects the
maintenance page and raises SiteMaintenanceError instead of silently failing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import date

from pydantic import BaseModel

from .constants import (
    BASE_URL,
    JUDGMENTS_URL,
    MAINTENANCE_MARKERS,
    MAX_PAGES,
    PAGINATION_TEMPLATE,
    REQUEST_DELAY_SECONDS,
)
from .errors import CrawlError, SiteMaintenanceError

logger = logging.getLogger(__name__)


class JudgmentRecord(BaseModel):
    """A single judgment post extracted from the SC website."""

    title: str
    case_number: str
    post_url: str
    pdf_url: str
    decision_date: str
    decision_date_parsed: date | None = None
    bench: str
    summary: str
    source_url: str


def _parse_case_number(title: str) -> str:
    """Extract case number from judgment post title.

    SC titles follow patterns like:
    - "Constitution Petition No. 39 of 2019"
    - "Civil Appeal No. 1234 of 2023"
    - "Criminal Appeal No. 567 of 2022"
    - "SMC No. 1 of 2024"
    """
    title = title.strip()
    match = re.match(
        r"^((?:Constitution\s+Petition|Civil\s+Appeal|Criminal\s+Appeal|"
        r"Cr(?:iminal)?\.?\s*(?:Appeal|Petition|Review)|"
        r"C(?:ivil)?\.?\s*(?:Appeal|Petition|Review)|"
        r"SMC|HRC|CPLA|CMA|CRP|"
        r"(?:Writ|W)\.?\s*P(?:etition)?|"
        r"(?:Human\s+Rights\s+Case)|"
        r"(?:Suo\s+Motu\s+Case)|"
        r"[A-Z][A-Za-z.]+)\s*"
        r"No\.?\s*\d+[-/]?\w*\s*(?:of|OF)\s*\d{4})",
        title,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    return title


def _parse_date(raw: str) -> date | None:
    """Parse date from various formats used on SC website.

    Handles:
    - "December 23, 2024" (WordPress default)
    - "23-12-2024" (dd-mm-yyyy)
    - "2024-12-23" (ISO)
    """
    raw = raw.strip()
    if not raw:
        return None

    # WordPress format: "Month Day, Year"
    import calendar

    month_names = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
    month_abbrs = {m.lower(): i for i, m in enumerate(calendar.month_abbr) if m}

    # Try "Month Day, Year"
    match = re.match(r"(\w+)\s+(\d{1,2}),?\s+(\d{4})", raw)
    if match:
        month_str, day, year = match.group(1).lower(), int(match.group(2)), int(match.group(3))
        month = month_names.get(month_str) or month_abbrs.get(month_str)
        if month:
            try:
                return date(year, month, day)
            except ValueError:
                pass

    # Try dd-mm-yyyy
    match = re.match(r"(\d{1,2})-(\d{1,2})-(\d{4})", raw)
    if match:
        try:
            return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        except ValueError:
            pass

    # Try ISO yyyy-mm-dd
    match = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", raw)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            pass

    logger.debug("Could not parse date: %s", raw)
    return None


def _is_maintenance_page(html: str) -> bool:
    """Check if the page content indicates site maintenance."""
    if not html:
        return False
    for marker in MAINTENANCE_MARKERS:
        if marker.lower() in html.lower():
            return True
    return False


# JsonCssExtractionStrategy schema for WordPress judgment posts.
# SC uses standard WordPress article markup under /category/judgements/.
CSS_EXTRACTION_SCHEMA = {
    "name": "SC Judgments",
    "baseSelector": "article.post, article.type-post, .post",
    "fields": [
        {"name": "title", "selector": "h2 a, h2.entry-title a, .entry-title a", "type": "text"},
        {
            "name": "post_url",
            "selector": "h2 a, h2.entry-title a, .entry-title a",
            "type": "attribute",
            "attribute": "href",
        },
        {"name": "date", "selector": "time, .entry-date, .posted-on time", "type": "text"},
        {
            "name": "date_attr",
            "selector": "time, .entry-date time",
            "type": "attribute",
            "attribute": "datetime",
        },
        {"name": "summary", "selector": ".entry-content, .entry-summary, .excerpt", "type": "text"},
        {
            "name": "pdf_url",
            "selector": ".entry-content a[href$='.pdf'], .entry-summary a[href$='.pdf']",
            "type": "attribute",
            "attribute": "href",
        },
    ],
}


def parse_listing_rows(raw_rows: list[dict], source_url: str) -> list[JudgmentRecord]:
    """Parse rows from JsonCssExtractionStrategy into JudgmentRecord models."""
    records = []
    for row in raw_rows:
        title = row.get("title", "").strip()
        if not title:
            continue

        case_number = _parse_case_number(title)

        # Prefer datetime attribute (ISO format) over text date
        date_raw = row.get("date_attr", "").strip() or row.get("date", "").strip()
        decision_date_parsed = _parse_date(date_raw)

        record = JudgmentRecord(
            title=title,
            case_number=case_number,
            post_url=row.get("post_url", "").strip(),
            pdf_url=row.get("pdf_url", "").strip(),
            decision_date=date_raw,
            decision_date_parsed=decision_date_parsed,
            bench="",  # Populated from individual post page if needed
            summary=row.get("summary", "").strip()[:500],
            source_url=source_url,
        )
        records.append(record)

    return records


async def check_site_status() -> dict:
    """Check if the Supreme Court website is accessible.

    Returns a status dict with:
    - accessible: bool
    - maintenance: bool
    - status_code: int or None
    - message: str
    """
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

    browser_config = BrowserConfig(
        headless=True,
        enable_stealth=True,
        extra_args=["--ignore-certificate-errors"],
    )
    run_config = CrawlerRunConfig(
        wait_until="load",
        page_timeout=30000,
    )

    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=BASE_URL, config=run_config)

            if not result.success:
                return {
                    "accessible": False,
                    "maintenance": False,
                    "status_code": result.status_code,
                    "message": f"Crawl failed: {result.error_message}",
                }

            if _is_maintenance_page(result.html or ""):
                return {
                    "accessible": True,
                    "maintenance": True,
                    "status_code": result.status_code,
                    "message": "Site is up but showing maintenance page",
                }

            return {
                "accessible": True,
                "maintenance": False,
                "status_code": result.status_code,
                "message": "Site is accessible",
            }
    except Exception as e:
        return {
            "accessible": False,
            "maintenance": False,
            "status_code": None,
            "message": f"Connection error: {e}",
        }


async def crawl_listing_page(page: int = 1) -> tuple[list[JudgmentRecord], bool]:
    """Crawl a single listing page of SC judgments.

    Uses crawl4ai stealth mode to handle Akamai CDN protection.

    Args:
        page: Page number (1-indexed).

    Returns:
        Tuple of (records, has_next_page).

    Raises:
        SiteMaintenanceError: If site is in maintenance mode.
        CrawlError: If crawl fails for other reasons.
    """
    from crawl4ai import (
        AsyncWebCrawler,
        BrowserConfig,
        CacheMode,
        CrawlerRunConfig,
        JsonCssExtractionStrategy,
    )

    url = JUDGMENTS_URL if page == 1 else PAGINATION_TEMPLATE.format(page=page)

    browser_config = BrowserConfig(
        headless=True,
        enable_stealth=True,
        extra_args=["--ignore-certificate-errors"],
    )

    extraction_strategy = JsonCssExtractionStrategy(
        schema=CSS_EXTRACTION_SCHEMA, verbose=False,
    )

    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_until="load",
        magic=True,
        delay_before_return_html=2.0,
        page_timeout=60000,
        extraction_strategy=extraction_strategy,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url, config=run_config)

        if not result.success:
            raise CrawlError(f"Page {page} crawl failed: {result.error_message}")

        # Check for maintenance
        if _is_maintenance_page(result.html or ""):
            raise SiteMaintenanceError(
                "Supreme Court website is currently down for maintenance"
            )

        # Parse records
        records = []
        if result.extracted_content:
            try:
                raw_rows = json.loads(result.extracted_content)
                records = parse_listing_rows(raw_rows, url)
            except json.JSONDecodeError as e:
                raise CrawlError(f"Failed to parse extracted JSON: {e}") from e

        # Check for next page link in HTML
        has_next = _has_next_page(result.html or "", page)

        logger.info("Page %d: extracted %d judgment records", page, len(records))
        return records, has_next


def _has_next_page(html: str, current_page: int) -> bool:
    """Check if there's a next page link in the pagination HTML."""
    next_page = current_page + 1
    # WordPress pagination: /page/N/
    patterns = [
        f"/page/{next_page}/",
        'class="next"',
        "next page-numbers",
    ]
    return any(p in html for p in patterns)


async def crawl_all_listings(max_pages: int = MAX_PAGES) -> list[JudgmentRecord]:
    """Crawl all paginated listing pages for SC judgments.

    Args:
        max_pages: Safety limit on number of pages to crawl.

    Returns:
        Combined list of JudgmentRecord from all pages.

    Raises:
        SiteMaintenanceError: If site is in maintenance mode.
        CrawlError: If crawl fails.
    """
    all_records: list[JudgmentRecord] = []
    seen_urls: set[str] = set()

    for page in range(1, max_pages + 1):
        records, has_next = await crawl_listing_page(page)

        # Deduplicate by post URL
        for record in records:
            if record.post_url and record.post_url not in seen_urls:
                seen_urls.add(record.post_url)
                all_records.append(record)

        if not has_next or not records:
            logger.info("Pagination ended at page %d", page)
            break

        # Respect rate limits
        await asyncio.sleep(REQUEST_DELAY_SECONDS)

    logger.info("Total: %d unique judgment records from %d pages", len(all_records), page)
    return all_records


async def extract_pdf_from_post(post_url: str) -> str:
    """Visit an individual judgment post page and extract the PDF link.

    Some judgment posts may not have PDF links in the listing excerpt.
    This function visits the full post page to find PDF download links.

    Args:
        post_url: Full URL to the judgment post page.

    Returns:
        PDF URL if found, empty string otherwise.
    """
    from crawl4ai import (
        AsyncWebCrawler,
        BrowserConfig,
        CacheMode,
        CrawlerRunConfig,
    )

    browser_config = BrowserConfig(
        headless=True,
        enable_stealth=True,
        extra_args=["--ignore-certificate-errors"],
    )

    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_until="load",
        magic=True,
        delay_before_return_html=1.0,
        page_timeout=30000,
    )

    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=post_url, config=run_config)

            if not result.success:
                logger.warning("Failed to load post: %s", post_url)
                return ""

            # Find PDF links in the page HTML
            pdf_links = re.findall(
                r'href=["\']([^"\']*\.pdf)["\']',
                result.html or "",
                re.IGNORECASE,
            )

            if pdf_links:
                # Return the first PDF link, make absolute if relative
                pdf_url = pdf_links[0]
                if pdf_url.startswith("/"):
                    pdf_url = BASE_URL + pdf_url
                return pdf_url

    except Exception as e:
        logger.error("Error extracting PDF from %s: %s", post_url, e)

    return ""
