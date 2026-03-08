"""Criminal judgment extraction pipeline — orchestrates three-tier extraction.

Usage:
    from src.extractors.criminal import extract_criminal_judgment
    result = extract_criminal_judgment(text, source_url="...")
    payload = result.to_qdrant_payload()
    vectors = result.to_vector_texts()
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from ..common.llm_client import LLMContentRefused, LLMError, LLMParsingError
from .reasoning_schema import ReasoningDecomposition
from .schema import CriminalExtractionResult, TierB, TierC
from .tier_a import extract_tier_a

logger = logging.getLogger(__name__)


def extract_criminal_judgment(
    text: str,
    source_url: str = "",
    skip_llm: bool = False,
) -> CriminalExtractionResult:
    """Run the full three-tier extraction pipeline on a criminal judgment.

    Args:
        text: Full judgment text.
        source_url: URL where judgment was sourced from.
        skip_llm: If True, only run Tier A (regex). Useful for testing.

    Returns:
        CriminalExtractionResult with all three tiers populated.
    """
    metadata: dict = {"text_length": len(text)}

    # ── Pass 1: Tier A (regex/NER) — fast, deterministic ──
    t0 = time.time()
    tier_a = extract_tier_a(text, source_url=source_url)
    metadata["tier_a_seconds"] = round(time.time() - t0, 3)
    logger.info(
        "Tier A extracted in %.3fs — case: %s",
        metadata["tier_a_seconds"],
        tier_a.case_number,
    )

    tier_b = TierB()
    tier_c = TierC()

    if not skip_llm:
        # ── Pass 2: Tier B (LLM classification) ──
        t0 = time.time()
        try:
            from .tier_b import extract_tier_b
            tier_b = extract_tier_b(text)
            metadata["tier_b_seconds"] = round(time.time() - t0, 3)
            logger.info("Tier B extracted in %.3fs", metadata["tier_b_seconds"])
        except LLMContentRefused as e:
            metadata["tier_b_error"] = f"content_refused: {e}"
            logger.warning("Tier B content refused: %s", e)
        except LLMParsingError as e:
            metadata["tier_b_error"] = f"parsing_failed: {e}"
            logger.error("Tier B JSON parsing failed after retries: %s", e)
        except LLMError as e:
            metadata["tier_b_error"] = f"llm_error: {e}"
            logger.error("Tier B LLM error (auth/config): %s", e)

        # ── Pass 3: Tier C (LLM reasoning points) ──
        t0 = time.time()
        try:
            from .tier_c import extract_tier_c
            tier_c = extract_tier_c(text)
            metadata["tier_c_seconds"] = round(time.time() - t0, 3)
            logger.info("Tier C extracted in %.3fs", metadata["tier_c_seconds"])
        except LLMContentRefused as e:
            metadata["tier_c_error"] = f"content_refused: {e}"
            logger.warning("Tier C content refused: %s", e)
        except LLMParsingError as e:
            metadata["tier_c_error"] = f"parsing_failed: {e}"
            logger.error("Tier C JSON parsing failed after retries: %s", e)
        except LLMError as e:
            metadata["tier_c_error"] = f"llm_error: {e}"
            logger.error("Tier C LLM error (auth/config): %s", e)

    # ── Pass 4: Reasoning Point Decomposition (LLM) ──
    reasoning_points_data: list = []
    if not skip_llm:
        t0 = time.time()
        try:
            from .reasoning_points import extract_reasoning_points
            decomposition = extract_reasoning_points(text)
            reasoning_points_data = decomposition.to_ingestable_texts()
            metadata["reasoning_seconds"] = round(time.time() - t0, 3)
            metadata["reasoning_point_count"] = len(reasoning_points_data)
            logger.info(
                "Reasoning decomposition in %.3fs — %d points",
                metadata["reasoning_seconds"],
                len(reasoning_points_data),
            )
        except LLMContentRefused as e:
            metadata["reasoning_error"] = f"content_refused: {e}"
            logger.warning("Reasoning decomposition content refused: %s", e)
        except LLMParsingError as e:
            metadata["reasoning_error"] = f"parsing_failed: {e}"
            logger.error("Reasoning decomposition JSON parsing failed: %s", e)
        except LLMError as e:
            metadata["reasoning_error"] = f"llm_error: {e}"
            logger.error("Reasoning decomposition LLM error: %s", e)

    result = CriminalExtractionResult(
        tier_a=tier_a,
        tier_b=tier_b,
        tier_c=tier_c,
        extraction_metadata=metadata,
        reasoning_points=reasoning_points_data,
    )

    coverage = result.field_coverage()
    metadata.update(coverage)
    logger.info(
        "Extraction complete — Tier A: %.1f%%, Tier B: %.1f%%, Tier C: %.1f%%",
        coverage["tier_a_pct"],
        coverage["tier_b_pct"],
        coverage["tier_c_pct"],
    )

    return result


def extract_batch(
    judgments: list[dict],
    skip_llm: bool = False,
    text_key: str = "text",
    id_key: str = "case_id",
) -> list[CriminalExtractionResult]:
    """Extract from a list of judgment dicts."""
    results = []
    for i, item in enumerate(judgments):
        text = item.get(text_key, "")
        source = item.get("source_url", "")
        logger.info("Processing %d/%d: %s", i + 1, len(judgments), item.get(id_key, "unknown"))
        result = extract_criminal_judgment(text, source_url=source, skip_llm=skip_llm)
        results.append(result)
    return results
