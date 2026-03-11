"""Islamabad High Court crawler pipeline.

Orchestrates the full flow: API search → metadata extraction → PDF download → text output.
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
from .listing import JudgmentRecord, crawl_all, crawl_all_judgments

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = Path(
    os.environ.get("IHC_OUTPUT_DIR", "data/islamabad_hc")
)

CHECKPOINT_INTERVAL = 25


async def crawl_full(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    limit: int | None = None,
    judgment_type: str | None = None,
) -> list[dict]:
    """Crawl IHC judgments and extract PDF text.

    Args:
        output_dir: Directory to save results and PDFs.
        limit: Max number of judgments to process. None for all.
        judgment_type: "reported", "important", or None for both.

    Returns:
        List of result dicts with metadata + extracted text.

    Raises:
        CrawlError: If the API cannot be reached.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir = output_dir / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    # Stage 1: Get judgment records from the API
    logger.info(
        "Stage 1: Fetching judgment listings (type=%s)...",
        judgment_type or "all",
    )
    if judgment_type:
        records = await crawl_all_judgments(judgment_type)
    else:
        records = await crawl_all()
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


async def _process_records(
    records: list[JudgmentRecord],
    pdf_dir: Path,
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
                "source": "islamabad_hc",
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
        "source": "islamabad_hc",
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

    by_type: dict[str, int] = {}
    for r in results:
        jtype = r.get("judgment_type", "unknown")
        by_type[jtype] = by_type.get(jtype, 0) + 1

    summary = {
        "total_records": len(results),
        "with_text": with_text,
        "empty_text": len(results) - with_text,
        "errors": errors,
        "by_judgment_type": by_type,
        "records": [
            {
                "case_number": r.get("case_number"),
                "judgment_type": r.get("judgment_type"),
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

    parser = argparse.ArgumentParser(description="Islamabad High Court Judgment Crawler")
    parser.add_argument(
        "--type", type=str, default=None,
        choices=["reported", "important"],
        help="Filter by judgment type (reported/important). Default: both.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max judgments to process")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    output_dir = Path(args.output)

    results = await crawl_full(
        output_dir=output_dir,
        limit=args.limit,
        judgment_type=args.type,
    )

    with_text = sum(1 for r in results if r["text"])
    errors = sum(1 for r in results if r.get("error"))
    logger.info("Done: %d records, %d with text, %d errors", len(results), with_text, errors)


if __name__ == "__main__":
    asyncio.run(main())
