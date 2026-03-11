"""Sindh High Court crawler pipeline.

Orchestrates the full flow: judge listing → judgment extraction → PDF download → text output.
Single responsibility: coordinate the pipeline stages with crash resilience.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path

from src.extractors.common.pdf_extract import download_and_extract

from .constants import COURT_CODE, JUDGE_IDS
from .listing import JudgmentRecord, crawl_all_judges, crawl_judge_judgments

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = Path(
    os.environ.get("SHC_OUTPUT_DIR", "data/sindh_hc")
)

CHECKPOINT_INTERVAL = 25


async def crawl_full(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    limit: int | None = None,
    judge_id: int | None = None,
    afr_only: bool = False,
) -> list[dict]:
    """Crawl SHC caselaw judgments and extract PDF text.

    Args:
        output_dir: Directory to save results and PDFs.
        limit: Max number of judgments to process. None for all.
        judge_id: Crawl only this judge's judgments. None for all judges.
        afr_only: If True, only crawl AFR (approved for reporting) judgments.

    Returns:
        List of result dicts with metadata + extracted text.

    Raises:
        CrawlError: If the listing page cannot be crawled.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir = output_dir / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    # Stage 1: Get judgment records
    if judge_id is not None:
        judge_name = JUDGE_IDS.get(judge_id, f"Judge {judge_id}")
        logger.info(
            "Stage 1: Crawling judgments for judge %s (ID=%d)...",
            judge_name, judge_id,
        )
        records = await crawl_judge_judgments(
            judge_id=judge_id,
            judge_name=judge_name,
            afr_only=afr_only,
        )
    else:
        logger.info("Stage 1: Crawling judgments for ALL judges...")
        records = await crawl_all_judges()

    logger.info("Found %d judgment records", len(records))

    if limit:
        records = records[:limit]
        logger.info("Limited to %d records", limit)

    # Stage 2: Download PDFs and extract text
    results = await _process_records(records, pdf_dir)

    # Save results
    _save_results(results, output_dir / "results.jsonl")
    _save_summary(results, output_dir / "summary.json")
    return results


async def crawl_judge(
    judge_id: int,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    limit: int | None = None,
    afr_only: bool = False,
) -> list[dict]:
    """Crawl judgments for a single SHC judge."""
    return await crawl_full(
        output_dir=output_dir,
        limit=limit,
        judge_id=judge_id,
        afr_only=afr_only,
    )


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
                "source": "sindh_hc",
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
        "source": "sindh_hc",
        "court": COURT_CODE,
    }


def _save_results(results: list[dict], path: Path) -> None:
    """Save results as JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w") as f:
            for result in results:
                # Convert date objects to strings for JSON serialization
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

    by_case_type: dict[str, int] = {}
    for r in results:
        ct = r.get("case_type", "unknown")
        by_case_type[ct] = by_case_type.get(ct, 0) + 1

    by_judge: dict[str, int] = {}
    for r in results:
        jn = r.get("judge_name", "unknown")
        by_judge[jn] = by_judge.get(jn, 0) + 1

    summary = {
        "total_records": len(results),
        "with_text": with_text,
        "empty_text": len(results) - with_text,
        "errors": errors,
        "by_case_type": by_case_type,
        "by_judge": by_judge,
        "records": [
            {
                "case_number": r.get("case_number"),
                "citation": r.get("citation"),
                "case_type": r.get("case_type"),
                "order_date": r.get("order_date"),
                "judge_name": r.get("judge_name"),
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

    parser = argparse.ArgumentParser(description="Sindh High Court Judgment Crawler")
    parser.add_argument(
        "--judge-id", type=int, default=None,
        help="Crawl only this judge's judgments (numeric ID)",
    )
    parser.add_argument(
        "--afr-only", action="store_true",
        help="Only crawl AFR (approved for reporting) judgments",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max judgments to process")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    output_dir = Path(args.output)

    results = await crawl_full(
        output_dir=output_dir,
        limit=args.limit,
        judge_id=args.judge_id,
        afr_only=args.afr_only,
    )

    with_text = sum(1 for r in results if r["text"])
    errors = sum(1 for r in results if r.get("error"))
    logger.info("Done: %d records, %d with text, %d errors", len(results), with_text, errors)


if __name__ == "__main__":
    asyncio.run(main())
