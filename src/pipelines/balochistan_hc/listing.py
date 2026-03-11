"""Crawl Balochistan HC judgments via the portal.bhc.gov.pk JSON API.

Single responsibility: browser session bootstrap + API query -> list of JudgmentRecord.

The BHC portal (portal.bhc.gov.pk) is a Nuxt.js SPA that proxies API requests
to api.bhc.gov.pk. The main bhc.gov.pk domain is protected by Incapsula WAF,
which crawl4ai bypasses using stealth mode.

Strategy:
1. Open the judgments page with crawl4ai (stealth mode bypasses Incapsula WAF).
2. Wait for the Nuxt/Vue app to initialize and Vuex store to hydrate.
3. Dispatch Vuex actions to load reference data (courts, judges, categories).
4. Call the /v2/judgments API through the Nuxt $axios proxy.
5. Extract results from a hidden DOM element injected by our JS code.

The API supports three search modes:
- searchBy=1: Search by case ID
- searchBy=2: Search by court + category + date range
- searchBy=3: Search by judge + date range

API response fields per record:
  FILE_ID, FILE_FOLDER, FILE_NAME, FILE_EXT (for PDF download URL)
  CASE_ID, CASE_TITLE, REGISTER_NUMBER
  AUTHOR_JUDGE, TYPE_NAME, ORDER_DATE (dd/mm/yyyy)
"""

from __future__ import annotations

import html
import json
import logging
import re
from datetime import date

from pydantic import BaseModel

from .constants import API_JUDGMENTS_PATH, JUDGMENTS_URL, PORTAL_URL
from .errors import CrawlError

logger = logging.getLogger(__name__)


class JudgmentRecord(BaseModel):
    """A single judgment record from the BHC portal API."""

    file_id: int
    case_id: int
    case_number: str
    case_title: str
    author_judge: str
    type_name: str
    order_date: str
    order_date_parsed: date | None = None
    pdf_url: str
    source_url: str


class CrawlResult(BaseModel):
    """Result of a judgment crawl including auth info for PDF downloads."""

    records: list[JudgmentRecord]
    auth_token: str = ""
    api_base_url: str = ""


def _parse_date(raw: str) -> date | None:
    """Parse dd/mm/yyyy date string from the BHC API."""
    raw = raw.strip()
    if not raw:
        return None
    try:
        parts = raw.split("/")
        if len(parts) == 3:
            return date(int(parts[2]), int(parts[1]), int(parts[0]))
    except (ValueError, IndexError):
        pass
    logger.debug("Could not parse date: %s", raw)
    return None


def _clean_html_entities(text: str) -> str:
    """Decode HTML entities like &nbsp; in case titles."""
    return html.unescape(text).strip()


API_BASE_URL = "https://api.bhc.gov.pk"


def _build_pdf_url(record: dict) -> str:
    """Build the PDF download URL from API response fields.

    URL pattern: {API_BASE_URL}/v2/downloadpdf/{FILE_FOLDER}/{FILE_NAME}.{FILE_EXT}

    The download function in the portal uses FILE_FOLDER (year), not FILE_ID.
    Downloads require a Bearer token from the authenticated browser session.
    Despite .doc/.docx extensions, the API returns PDF content.
    """
    file_folder = record.get("FILE_FOLDER", "")
    file_name = record.get("FILE_NAME", "")
    file_ext = record.get("FILE_EXT", "")
    if not file_folder or not file_name:
        return ""
    return f"{API_BASE_URL}/v2/downloadpdf/{file_folder}/{file_name}.{file_ext}"


def parse_api_response(
    raw_records: list[dict],
    source_url: str,
) -> list[JudgmentRecord]:
    """Parse raw API response records into JudgmentRecord models.

    Args:
        raw_records: List of dicts from the /v2/judgments API response.
        source_url: Source URL for provenance tracking.
    """
    records = []
    for raw in raw_records:
        order_date_raw = raw.get("ORDER_DATE", "").strip()
        case_title = _clean_html_entities(raw.get("CASE_TITLE", ""))

        record = JudgmentRecord(
            file_id=int(raw.get("FILE_ID", 0) or 0),
            case_id=int(raw.get("CASE_ID", 0) or 0),
            case_number=raw.get("REGISTER_NUMBER", "").strip(),
            case_title=case_title,
            author_judge=raw.get("AUTHOR_JUDGE", "").strip(),
            type_name=raw.get("TYPE_NAME", "").strip(),
            order_date=order_date_raw,
            order_date_parsed=_parse_date(order_date_raw),
            pdf_url=_build_pdf_url(raw),
            source_url=source_url,
        )
        records.append(record)

    return records


def _build_search_js(
    search_by: int,
    judge_id: int | None = None,
    court_id: int | None = None,
    category_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """Build JavaScript to search via Nuxt $axios and dump results to DOM.

    The JS code:
    1. Waits for the Nuxt app and Vuex store to be ready.
    2. Dispatches actions to load reference data (courts, judges).
    3. Calls /v2/judgments via the Nuxt $axios proxy.
    4. Writes JSON results into a hidden DOM element for extraction.
    """
    # Default date range: 2001-01-01 to today + 1 day
    if not start_date:
        start_date = "2001-01-01"
    if not end_date:
        end_date = "2026-12-31"

    form_obj = {
        "searchBy": search_by,
        "sDate": start_date,
        "eDate": end_date,
    }
    if judge_id is not None:
        form_obj["judgeId"] = judge_id
    if court_id is not None:
        form_obj["courtId"] = court_id
    if category_id is not None:
        form_obj["categoryId"] = category_id

    form_json = json.dumps(form_obj)

    return f"""
    (async () => {{
        // Wait for Nuxt/Vue to be ready
        for (let i = 0; i < 40; i++) {{
            if (window.$nuxt && window.$nuxt.$store) break;
            await new Promise(r => setTimeout(r, 500));
        }}

        const resultDiv = document.createElement('div');
        resultDiv.id = 'bhc-api-result';
        resultDiv.style.display = 'none';

        if (!window.$nuxt || !window.$nuxt.$store) {{
            resultDiv.textContent = JSON.stringify({{error: 'Nuxt store not available'}});
            document.body.appendChild(resultDiv);
            return;
        }}

        const axios = window.$nuxt.$axios;
        const authToken = (axios.defaults.headers.common || {{}}).Authorization || '';
        const apiBaseUrl = axios.defaults.baseURL || '';

        try {{
            const result = await axios.$post(
                '/v2/judgments',
                {form_json}
            );
            resultDiv.textContent = JSON.stringify({{
                success: true,
                count: result.length,
                records: result,
                auth_token: authToken,
                api_base_url: apiBaseUrl,
            }});
        }} catch(e) {{
            resultDiv.textContent = JSON.stringify({{
                error: e.message || 'API call failed',
                status: e.response ? e.response.status : null,
            }});
        }}
        document.body.appendChild(resultDiv);
    }})();
    """


def _build_load_metadata_js() -> str:
    """Build JavaScript to load reference data (courts, judges, categories)."""
    return """
    (async () => {
        for (let i = 0; i < 40; i++) {
            if (window.$nuxt && window.$nuxt.$store) break;
            await new Promise(r => setTimeout(r, 500));
        }

        const resultDiv = document.createElement('div');
        resultDiv.id = 'bhc-api-result';
        resultDiv.style.display = 'none';

        if (!window.$nuxt || !window.$nuxt.$store) {
            resultDiv.textContent = JSON.stringify({error: 'Nuxt store not available'});
            document.body.appendChild(resultDiv);
            return;
        }

        const store = window.$nuxt.$store;
        try {
            await store.dispatch('repository/LOAD_COURTS');
        } catch(e) {}
        try {
            await store.dispatch('repository/LOAD_JUDGES');
        } catch(e) {}
        await new Promise(r => setTimeout(r, 1000));

        const state = store.state.repository;
        const courts = state.courts || [];
        const judges = state.judges || [];

        resultDiv.textContent = JSON.stringify({
            success: true,
            courts: courts.filter(c => {
                const t = parseInt(c.COURT_TYPE, 10);
                return t === 21 || t === 31;
            }),
            judges: judges.filter(j => parseInt(j.TOTAL_ORDERS, 10) > 0),
            categories: state.categories || [],
        });
        document.body.appendChild(resultDiv);
    })();
    """


def _extract_api_result(html_content: str) -> dict:
    """Extract the API result JSON from the hidden DOM element."""
    match = re.search(r'id="bhc-api-result"[^>]*>([^<]+)', html_content)
    if not match:
        raise CrawlError("Could not find API result element in page HTML")
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as e:
        raise CrawlError(f"Failed to parse API result JSON: {e}") from e


async def load_metadata() -> dict:
    """Load reference data (courts, judges, categories) from the BHC portal.

    Returns:
        Dict with 'courts', 'judges', and 'categories' lists.

    Raises:
        CrawlError: If the portal cannot be accessed or data loading fails.
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
        wait_until="networkidle",
        delay_before_return_html=12.0,
        page_timeout=90000,
        magic=True,
        js_code=_build_load_metadata_js(),
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=JUDGMENTS_URL, config=run_config)
        if not result.success:
            raise CrawlError(f"Failed to load portal: {result.error_message}")

        data = _extract_api_result(result.html)
        if "error" in data:
            raise CrawlError(f"Metadata load failed: {data['error']}")

        logger.info(
            "Loaded metadata: %d courts, %d judges, %d categories",
            len(data.get("courts", [])),
            len(data.get("judges", [])),
            len(data.get("categories", [])),
        )
        return data


async def crawl_judgments_by_judge(
    judge_id: int,
    start_date: str | None = None,
    end_date: str | None = None,
) -> CrawlResult:
    """Crawl BHC judgments for a specific judge.

    Args:
        judge_id: Judge ID from the BHC portal.
        start_date: Start date in yyyy-mm-dd format. Defaults to 2001-01-01.
        end_date: End date in yyyy-mm-dd format. Defaults to 2026-12-31.

    Returns:
        CrawlResult with records and auth info for PDF downloads.

    Raises:
        CrawlError: If the API call fails.
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

    js_code = _build_search_js(
        search_by=3,
        judge_id=judge_id,
        start_date=start_date,
        end_date=end_date,
    )

    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_until="networkidle",
        delay_before_return_html=15.0,
        page_timeout=90000,
        magic=True,
        js_code=js_code,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=JUDGMENTS_URL, config=run_config)
        if not result.success:
            raise CrawlError(f"Crawl failed: {result.error_message}")

        data = _extract_api_result(result.html)
        if "error" in data:
            raise CrawlError(f"API error: {data['error']}")

        raw_records = data.get("records", [])
        records = parse_api_response(raw_records, JUDGMENTS_URL)

        logger.info(
            "Crawled %d judgment records for judge_id=%d",
            len(records), judge_id,
        )
        return CrawlResult(
            records=records,
            auth_token=data.get("auth_token", ""),
            api_base_url=data.get("api_base_url", ""),
        )


async def crawl_all_judges() -> CrawlResult:
    """Crawl all BHC judgments by iterating through all judges.

    This is the most reliable approach because the API returns all results
    for a given judge without pagination limits.

    Returns:
        CrawlResult with deduplicated records and auth info.

    Raises:
        CrawlError: If metadata loading fails.
    """
    metadata = await load_metadata()
    judges = metadata.get("judges", [])

    if not judges:
        raise CrawlError("No judges found in metadata")

    logger.info("Crawling judgments for %d judges...", len(judges))

    all_records: list[JudgmentRecord] = []
    seen_file_ids: set[int] = set()
    auth_token = ""
    api_base_url = ""

    for idx, judge in enumerate(judges):
        judge_id = judge["JUDGE_ID"]
        judge_name = judge["JUDGE_NAME"]
        total_orders = judge.get("TOTAL_ORDERS", 0)

        logger.info(
            "[%d/%d] Judge: %s (ID=%d, expected=%d orders)",
            idx + 1, len(judges), judge_name, judge_id, total_orders,
        )

        try:
            crawl_result = await crawl_judgments_by_judge(judge_id)

            # Keep the latest auth token (refreshed each browser session)
            if crawl_result.auth_token:
                auth_token = crawl_result.auth_token
                api_base_url = crawl_result.api_base_url

            # Deduplicate by file_id
            new_count = 0
            for record in crawl_result.records:
                if record.file_id not in seen_file_ids:
                    seen_file_ids.add(record.file_id)
                    all_records.append(record)
                    new_count += 1

            logger.info(
                "  -> %d records (%d new, %d duplicates)",
                len(crawl_result.records), new_count,
                len(crawl_result.records) - new_count,
            )
        except CrawlError as e:
            logger.error(
                "  -> FAILED: %s (continuing with next judge)", e,
            )

    logger.info(
        "Total: %d unique judgment records from %d judges",
        len(all_records), len(judges),
    )
    return CrawlResult(
        records=all_records,
        auth_token=auth_token,
        api_base_url=api_base_url,
    )
