"""Generate SAC (Summary-Augmented Chunking) summaries for judgments.

Single responsibility: judgment text → short summary string (100-200 tokens).
The summary is prepended to every chunk to reduce Document-Level Retrieval
Mismatch by ~50% (per SAC research benchmarks).

Uses the shared LLM client from extractors.common.llm_client.
"""

from __future__ import annotations

import logging

from src.extractors.common.llm_client import call_llm_json  # noqa: absolute import — src is on sys.path

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a Pakistani legal case summarizer. Given a court judgment, produce a \
concise summary that captures the essential information a lawyer would need \
to decide if this case is relevant to their query.

Your summary MUST include (when available):
- Court and case type (criminal appeal, civil petition, etc.)
- Key legal issue(s) being decided
- Relevant statutes/sections cited
- The outcome/disposition

Respond with JSON: {"summary": "..."}
Keep the summary between 50-100 words. Use formal legal English."""

_USER_TEMPLATE = """\
Summarize this Pakistani court judgment:

{text}"""

# Truncate input to avoid token limits — first and last portions
MAX_INPUT_CHARS = 12000


def generate_summary(text: str) -> str:
    """Generate a SAC summary for a judgment.

    Returns the summary string, or empty string on failure.
    Never raises — failures are logged and return empty string so
    the chunking pipeline continues without a summary prefix.
    """
    if not text or len(text) < 200:
        return ""

    truncated = _truncate_for_summary(text)

    try:
        result = call_llm_json(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=_USER_TEMPLATE.format(text=truncated),
            temperature=0.0,
        )
        summary = result.get("summary", "").strip()
        if not summary:
            logger.warning(
                "SAC summary: LLM returned no 'summary' key. Keys: %s",
                list(result.keys()),
            )
            return ""
        logger.info("Generated SAC summary: %d chars", len(summary))
        return summary

    except Exception as e:
        logger.warning("SAC summary generation failed: %s: %s", type(e).__name__, e)
        return ""


def _truncate_for_summary(text: str) -> str:
    """Truncate long text for summary generation.

    Takes the first 8K + last 4K chars. The header and disposition
    carry the most summary-relevant information.
    """
    if len(text) <= MAX_INPUT_CHARS:
        return text

    head = text[:8000]
    tail = text[-4000:]
    return f"{head}\n\n[...middle truncated...]\n\n{tail}"
