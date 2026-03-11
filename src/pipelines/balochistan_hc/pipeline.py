"""Balochistan High Court crawler pipeline.

Orchestrates the full flow: API search -> record extraction -> PDF download -> text output.
Single responsibility: coordinate the pipeline stages with crash resilience.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path

from src.extractors.common.pdf_extract import download_and_extract

from .constants import COURT_CODE
from .listing import CrawlResult, JudgmentRecord, crawl_judgments_by_judge, load_metadata

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = Path(
    os.environ.get("BHC_OUTPUT_DIR", "data/balochistan_hc")
)

CHECKPOINT_INTERVAL = 25


async def crawl_full(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    limit: int | None = None,
    judge_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """Crawl BHC judgments and extract PDF text.

    Args:
        output_dir: Directory to save results and PDFs.
        limit: Max number of judgments to process. None for all.
        judge_id: Filter by specific judge ID. None for all judges.
        start_date: Start date in yyyy-mm-dd format.
        end_date: End date in yyyy-mm-dd format.

    Returns:
        List of result dicts with metadata + extracted text.

    Raises:
        CrawlError: If the portal cannot be accessed.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir = output_dir / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    # Stage 1: Get judgment records
    if judge_id is not None:
        logger.info(
            "Stage 1: Crawling judgments for judge_id=%d...", judge_id,
        )
        crawl_result = await crawl_judgments_by_judge(
            judge_id, start_date=start_date, end_date=end_date,
        )
    else:
        logger.info("Stage 1: Crawling judgments for all judges...")
        crawl_result = await _crawl_all_judges_with_dedup(
            start_date=start_date, end_date=end_date,
        )

    records = crawl_result.records
    logger.info("Found %d judgment records", len(records))

    if limit:
        records = records[:limit]
        logger.info("Limited to %d records", limit)

    # Build auth headers for PDF downloads from the BHC API
    pdf_headers = None
    if crawl_result.auth_token:
        pdf_headers = {
            "Authorization": crawl_result.auth_token,
            "Accept": "*/*",
        }
        logger.info("Using authenticated PDF downloads via api.bhc.gov.pk")

    # Stage 2: Download PDFs and extract text
    results = await _process_records(records, pdf_dir, pdf_headers=pdf_headers)

    # Save results
    _save_results(results, output_dir / "results.jsonl")
    _save_summary(results, output_dir / "summary.json")
    return results


async def _crawl_all_judges_with_dedup(
    start_date: str | None = None,
    end_date: str | None = None,
) -> CrawlResult:
    """Crawl all judges and deduplicate results."""
    metadata = await load_metadata()
    judges = metadata.get("judges", [])

    if not judges:
        logger.warning("No judges found in metadata")
        return CrawlResult(records=[])

    logger.info("Crawling judgments for %d judges...", len(judges))

    all_records: list[JudgmentRecord] = []
    seen_file_ids: set[int] = set()
    auth_token = ""
    api_base_url = ""

    for idx, judge in enumerate(judges):
        jid = judge["JUDGE_ID"]
        judge_name = judge["JUDGE_NAME"]

        logger.info(
            "[%d/%d] Judge: %s (ID=%d)",
            idx + 1, len(judges), judge_name, jid,
        )

        try:
            crawl_result = await crawl_judgments_by_judge(
                jid, start_date=start_date, end_date=end_date,
            )

            if crawl_result.auth_token:
                auth_token = crawl_result.auth_token
                api_base_url = crawl_result.api_base_url

            new_count = 0
            for record in crawl_result.records:
                if record.file_id not in seen_file_ids:
                    seen_file_ids.add(record.file_id)
                    all_records.append(record)
                    new_count += 1

            logger.info(
                "  -> %d records (%d new)",
                len(crawl_result.records), new_count,
            )
        except Exception as e:
            logger.error("  -> FAILED: %s", e)

    logger.info("Total: %d unique records", len(all_records))
    return CrawlResult(
        records=all_records,
        auth_token=auth_token,
        api_base_url=api_base_url,
    )


async def crawl_judge(
    judge_id: int,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    limit: int | None = None,
) -> list[dict]:
    """Crawl judgments for a single BHC judge."""
    return await crawl_full(
        output_dir=output_dir, limit=limit, judge_id=judge_id,
    )


async def _process_records(
    records: list[JudgmentRecord],
    pdf_dir: Path,
    pdf_headers: dict | None = None,
) -> list[dict]:
    """Download PDFs and extract text for each judgment record.

    Per-record error isolation so one failure does not kill the batch.
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
            result = await _process_single_record(record, pdf_dir, pdf_headers)
            results.append(result)

            if result["text"]:
                logger.info(
                    "[%d/%d] OK: %s - %d chars",
                    idx + 1, len(records),
                    record.case_number or "?",
                    result["text_length"],
                )
            else:
                logger.warning(
                    "[%d/%d] EMPTY: %s - no text extracted",
                    idx + 1, len(records),
                    record.case_number or record.pdf_url,
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
                "source": "balochistan_hc",
                "court": COURT_CODE,
            })

        # Checkpoint save
        if len(results) % CHECKPOINT_INTERVAL == 0 and results:
            _save_results(results, checkpoint_path)
            logger.info("Checkpoint: %d results saved", len(results))

    with_text = sum(1 for r in results if r["text"])
    logger.info(
        "Processed %d records: %d with text, %d empty, %d failed",
        len(results), with_text,
        len(results) - with_text - failed_count, failed_count,
    )
    return results


async def _process_single_record(
    record: JudgmentRecord,
    pdf_dir: Path,
    pdf_headers: dict | None = None,
) -> dict:
    """Download PDF and extract text for a single judgment record.

    The BHC API requires a Bearer token for PDF downloads. The pdf_headers
    dict contains the Authorization header from the authenticated browser session.
    """
    text = ""
    if record.pdf_url:
        text = await download_and_extract(
            record.pdf_url, pdf_dir, headers=pdf_headers,
        )
    else:
        logger.warning("No PDF URL for %s", record.case_number)

    return {
        **record.model_dump(),
        "text": text,
        "text_length": len(text),
        "source": "balochistan_hc",
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

    by_type: dict[str, int] = {}
    for r in results:
        t = r.get("type_name", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    by_judge: dict[str, int] = {}
    for r in results:
        j = r.get("author_judge", "unknown")
        by_judge[j] = by_judge.get(j, 0) + 1

    summary = {
        "total_records": len(results),
        "with_text": with_text,
        "empty_text": len(results) - with_text,
        "errors": errors,
        "by_type": by_type,
        "by_judge": by_judge,
        "records": [
            {
                "case_number": r.get("case_number"),
                "type_name": r.get("type_name"),
                "order_date": r.get("order_date"),
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


async def main() -> None:
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    import argparse

    parser = argparse.ArgumentParser(
        description="Balochistan High Court Judgment Crawler",
    )
    parser.add_argument(
        "--judge-id", type=int, default=None,
        help="Filter by judge ID",
    )
    parser.add_argument(
        "--start-date", type=str, default=None,
        help="Start date (yyyy-mm-dd)",
    )
    parser.add_argument(
        "--end-date", type=str, default=None,
        help="End date (yyyy-mm-dd)",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Max judgments to process",
    )
    parser.add_argument(
        "--output", type=str, default=str(DEFAULT_OUTPUT_DIR),
    )
    args = parser.parse_args()

    output_dir = Path(args.output)

    results = await crawl_full(
        output_dir=output_dir,
        limit=args.limit,
        judge_id=args.judge_id,
        start_date=args.start_date,
        end_date=args.end_date,
    )

    with_text = sum(1 for r in results if r["text"])
    errors = sum(1 for r in results if r.get("error"))
    logger.info(
        "Done: %d records, %d with text, %d errors",
        len(results), with_text, errors,
    )


if __name__ == "__main__":
    asyncio.run(main())
