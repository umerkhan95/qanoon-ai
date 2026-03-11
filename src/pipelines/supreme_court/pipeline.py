"""Supreme Court of Pakistan crawler pipeline.

Orchestrates the full flow: listing crawl → post visit → PDF download → text output.
Single responsibility: coordinate the pipeline stages with crash resilience.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path

from src.extractors.common.pdf_extract import download_and_extract

from .constants import COURT_CODE, REQUEST_DELAY_SECONDS
from .errors import SiteMaintenanceError
from .listing import (
    JudgmentRecord,
    check_site_status,
    crawl_all_listings,
    extract_pdf_from_post,
)

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = Path(
    os.environ.get("SC_OUTPUT_DIR", "data/supreme_court")
)

CHECKPOINT_INTERVAL = 25


async def crawl_full(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    limit: int | None = None,
    skip_site_check: bool = False,
) -> list[dict]:
    """Crawl Supreme Court judgments and extract PDF text.

    Args:
        output_dir: Directory to save results and PDFs.
        limit: Max number of judgments to process. None for all.
        skip_site_check: Skip the maintenance check (for testing).

    Returns:
        List of result dicts with metadata + extracted text.

    Raises:
        SiteMaintenanceError: If site is in maintenance mode.
        CrawlError: If the listing pages cannot be crawled.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir = output_dir / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    # Stage 0: Check if site is accessible
    if not skip_site_check:
        logger.info("Stage 0: Checking site accessibility...")
        site_status = await check_site_status()
        logger.info("Site status: %s", site_status["message"])

        if site_status["maintenance"]:
            raise SiteMaintenanceError(site_status["message"])

        if not site_status["accessible"]:
            raise SiteMaintenanceError(
                f"Site not accessible: {site_status['message']}"
            )

    # Stage 1: Crawl judgment listings
    logger.info("Stage 1: Crawling judgment listings...")
    records = await crawl_all_listings()
    logger.info("Found %d judgment records", len(records))

    if limit:
        records = records[:limit]
        logger.info("Limited to %d records", limit)

    # Stage 2: Enrich records with PDF links from individual posts
    records = await _enrich_pdf_links(records)

    # Stage 3: Download PDFs and extract text
    results = await _process_records(records, pdf_dir)

    # Save results
    _save_results(results, output_dir / "results.jsonl")
    _save_summary(results, output_dir / "summary.json")
    return results


async def _enrich_pdf_links(
    records: list[JudgmentRecord],
) -> list[JudgmentRecord]:
    """Visit individual post pages to find PDF links for records missing them."""
    enriched = 0
    for idx, record in enumerate(records):
        if record.pdf_url:
            continue

        if not record.post_url:
            continue

        logger.info(
            "[%d/%d] Enriching PDF link for: %s",
            idx + 1, len(records), record.case_number,
        )

        pdf_url = await extract_pdf_from_post(record.post_url)
        if pdf_url:
            record = record.model_copy(update={"pdf_url": pdf_url})
            records[idx] = record
            enriched += 1

        await asyncio.sleep(REQUEST_DELAY_SECONDS)

    if enriched:
        logger.info("Enriched %d records with PDF links", enriched)

    return records


async def _process_records(
    records: list[JudgmentRecord],
    pdf_dir: Path,
) -> list[dict]:
    """Download PDFs and extract text for each judgment record.

    Per-record error isolation so one failure doesn't kill the batch.
    Checkpoint saves every CHECKPOINT_INTERVAL records.
    """
    results: list[dict] = []
    seen_urls: set[str] = set()
    checkpoint_path = pdf_dir.parent / "checkpoint.jsonl"
    failed_count = 0

    for idx, record in enumerate(records):
        # Deduplicate by PDF URL
        if record.pdf_url and record.pdf_url in seen_urls:
            logger.debug("Skipping duplicate PDF: %s", record.pdf_url)
            continue
        if record.pdf_url:
            seen_urls.add(record.pdf_url)

        try:
            result = await _process_single_record(record, pdf_dir)
            results.append(result)

            if result["text"]:
                logger.info(
                    "[%d/%d] OK: %s — %d chars",
                    idx + 1, len(records),
                    record.case_number or "?",
                    result["text_length"],
                )
            else:
                logger.warning(
                    "[%d/%d] EMPTY: %s — no text extracted",
                    idx + 1, len(records),
                    record.case_number or record.post_url,
                )

        except Exception as e:
            failed_count += 1
            logger.error(
                "[%d/%d] FAILED: %s: %s",
                idx + 1, len(records), record.case_number, e,
                exc_info=True,
            )
            results.append({
                **record.model_dump(),
                "text": "",
                "text_length": 0,
                "error": str(e),
                "source": "supreme_court",
                "court": COURT_CODE,
            })

        # Checkpoint save
        if len(results) % CHECKPOINT_INTERVAL == 0 and results:
            _save_results(results, checkpoint_path)
            logger.info("Checkpoint: %d results saved", len(results))

    with_text = sum(1 for r in results if r["text"])
    logger.info(
        "Processed %d records: %d with text, %d empty, %d failed",
        len(results), with_text, len(results) - with_text - failed_count, failed_count,
    )
    return results


async def _process_single_record(
    record: JudgmentRecord,
    pdf_dir: Path,
) -> dict:
    """Download PDF and extract text for a single judgment record."""
    text = ""
    if record.pdf_url:
        text = await download_and_extract(record.pdf_url, pdf_dir)
    else:
        logger.warning("No PDF URL for %s", record.case_number)

    return {
        **record.model_dump(),
        "text": text,
        "text_length": len(text),
        "source": "supreme_court",
        "court": COURT_CODE,
    }


def _save_results(results: list[dict], path: Path) -> None:
    """Save results as JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w") as f:
            for result in results:
                row = {}
                for k, v in result.items():
                    if hasattr(v, "isoformat"):
                        row[k] = v.isoformat()
                    else:
                        row[k] = v
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        logger.info("Saved %d results to %s", len(results), path)
    except (OSError, TypeError) as e:
        logger.error("Failed to save results to %s: %s", path, e)
        raise


def _save_summary(results: list[dict], path: Path) -> None:
    """Save a summary of the crawl run."""
    with_text = sum(1 for r in results if r.get("text"))
    errors = sum(1 for r in results if r.get("error"))

    summary = {
        "total_records": len(results),
        "with_text": with_text,
        "empty_text": len(results) - with_text,
        "errors": errors,
        "records": [
            {
                "case_number": r.get("case_number"),
                "title": r.get("title"),
                "decision_date": r.get("decision_date"),
                "text_length": r.get("text_length", 0),
                "error": r.get("error"),
            }
            for r in results
        ],
    }
    try:
        with open(path, "w") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
    except (OSError, TypeError) as e:
        logger.error("Failed to save summary to %s: %s", path, e)


async def main():
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    import argparse

    parser = argparse.ArgumentParser(
        description="Supreme Court of Pakistan Judgment Crawler"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Max judgments to process",
    )
    parser.add_argument(
        "--output", type=str, default=str(DEFAULT_OUTPUT_DIR),
    )
    parser.add_argument(
        "--check-only", action="store_true",
        help="Only check if the site is accessible, don't crawl",
    )
    args = parser.parse_args()

    if args.check_only:
        result = await check_site_status()
        logger.info("Status: %s", result)
        return

    output_dir = Path(args.output)

    try:
        results = await crawl_full(output_dir=output_dir, limit=args.limit)
        with_text = sum(1 for r in results if r["text"])
        errors = sum(1 for r in results if r.get("error"))
        logger.info(
            "Done: %d records, %d with text, %d errors",
            len(results), with_text, errors,
        )
    except SiteMaintenanceError as e:
        logger.error("Cannot crawl: %s", e)
        logger.info(
            "The Supreme Court website is currently under maintenance. "
            "Try again later or use --check-only to monitor status."
        )


if __name__ == "__main__":
    asyncio.run(main())
