"""Reasoning Point Decomposition — judgment → atomic searchable points.

Single responsibility: Extract structured reasoning points from a judgment
via LLM. Each judgment produces 5-50+ points depending on complexity.

This is a separate extraction pass from Tier C (which extracts 17 fixed fields).
Reasoning points are variable-count and issue-specific.
"""

from __future__ import annotations

import logging
from typing import Optional

from ..common.llm_client import call_llm_json
from .reasoning_schema import (
    ReasoningDecomposition,
    ReasoningPoint,
    ReasoningPointType,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Pakistani legal expert specializing in judgment analysis. Your task is to decompose a criminal judgment into independent, atomic reasoning points.

Each reasoning point must be self-contained — a reader should understand it without reading the full judgment.

Extract the following point types:

1. FACTS (exactly 1): Summary of the factual narrative. Include key events, dates, parties, and disputed facts.

2. ISSUE (1 per legal question): Each distinct legal question the court addressed. Examples: "Whether the prosecution proved guilt beyond reasonable doubt", "Whether the confession was voluntary".

3. PETITIONER_ARGUMENT (1 per distinct argument): Each argument made by the petitioner/appellant's counsel. Include supporting precedents cited.

4. RESPONDENT_ARGUMENT (1 per distinct argument): Each argument by the respondent/state. Include supporting precedents cited.

5. EVIDENCE (1 per key evidence item): Each significant piece of evidence the court assessed. Include: type (oral/documentary/forensic/expert/confession), admissibility ruling, and weight given.

6. COURT_REASONING (1 per issue): The court's analysis for each legal issue. This is the most important type — capture the full reasoning chain, not just the conclusion.

7. RATIO_DECIDENDI (0-1): The binding legal principle established. Include scope and limitations if stated.

8. OBITER_DICTA (0-N): Non-binding observations the court made. Only extract if clearly distinct from ratio.

9. FINAL_ORDER (exactly 1): The court's actual order — conviction/acquittal/remand/sentence modification.

10. DISSENT (0-1): Dissenting opinion if any. Include the dissenting judge's name and reasoning.

Rules:
- Each point must have 50-500 words of substantive text
- Extract sections_cited (e.g., "Section 302 PPC", "Article 164-A QSO") found IN THAT POINT
- Extract precedents_cited (e.g., "PLD 2020 SC 1", "2019 SCMR 100") found IN THAT POINT
- For source_paragraphs, list the paragraph numbers from the judgment that this point draws from
- Set extraction_confidence: 1.0 for direct quotes, 0.8 for clear paraphrases, 0.5 for inferred
- For ISSUE points, set issue_addressed to the legal question text
- For EVIDENCE points, set evidence_type, admissibility_ruling, weight_given
- For argument points, set strength_assessment ("strong", "moderate", "weak") based on court's reception
- Use null for optional fields that don't apply to the point type

Return ONLY valid JSON in this exact format:
{
  "points": [
    {
      "point_type": "facts|issue|petitioner_argument|respondent_argument|evidence|court_reasoning|ratio_decidendi|obiter_dicta|final_order|dissent",
      "text": "Substantive text of this reasoning point...",
      "source_paragraphs": [1, 2, 3],
      "issue_addressed": "The legal question (for issue/reasoning types)",
      "sections_cited": ["Section 302 PPC"],
      "precedents_cited": ["PLD 2020 SC 1"],
      "scope": "Scope of the principle (for ratio)",
      "limitations": "Limitations stated (for ratio)",
      "evidence_type": "oral|documentary|forensic|expert|confession|fir",
      "admissibility_ruling": "admitted|excluded|challenged",
      "weight_given": "relied_upon|discredited|corroborative",
      "strength_assessment": "strong|moderate|weak",
      "dissenting_judge": "Justice name (for dissent)",
      "extraction_confidence": 0.8
    }
  ],
  "total_issues": 2
}"""


def extract_reasoning_points(text: str) -> ReasoningDecomposition:
    """Decompose a judgment into atomic reasoning points via LLM.

    Args:
        text: Full judgment text.

    Returns:
        ReasoningDecomposition with list of ReasoningPoint objects.

    Raises:
        LLMContentRefused: If the LLM refuses to process the content.
        LLMParsingError: If the LLM response cannot be parsed as JSON.
        LLMError: For other non-recoverable LLM failures.
    """
    if not text or not text.strip():
        logger.warning("Empty text for reasoning point extraction")
        return ReasoningDecomposition()

    truncated = _truncate_for_extraction(text)

    raw = call_llm_json(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=f"Decompose this Pakistani criminal judgment into atomic reasoning points:\n\n{truncated}",
    )

    return _parse_decomposition(raw)


def _truncate_for_extraction(text: str) -> str:
    """Truncate long judgments for LLM context window.

    Keeps first 18K + last 12K chars to preserve both the header/facts
    and the disposition/order sections.
    """
    if len(text) <= 30000:
        return text

    head = text[:18000]
    tail = text[-12000:]
    separator = "\n\n[...MIDDLE SECTION OMITTED FOR LENGTH...]\n\n"
    result = head + separator + tail
    logger.info(
        "Truncated judgment from %d to %d chars for reasoning extraction",
        len(text), len(result),
    )
    return result


def _parse_decomposition(raw: dict) -> ReasoningDecomposition:
    """Parse raw LLM JSON into ReasoningDecomposition.

    Validates each point individually — invalid points are logged and skipped
    rather than failing the entire decomposition.
    """
    if not isinstance(raw, dict):
        logger.error("LLM returned non-dict response: %s", type(raw).__name__)
        return ReasoningDecomposition(
            extraction_metadata={"error": f"Expected dict, got {type(raw).__name__}"},
        )

    raw_points = raw.get("points", [])
    total_issues = raw.get("total_issues", 0)

    if not isinstance(raw_points, list):
        logger.error(
            "LLM returned non-list 'points' field: %s", type(raw_points).__name__
        )
        return ReasoningDecomposition(
            extraction_metadata={"error": "points field is not a list"},
        )

    valid_types = {t.value for t in ReasoningPointType}
    points: list[ReasoningPoint] = []
    skipped = 0

    for i, raw_point in enumerate(raw_points):
        if not isinstance(raw_point, dict):
            logger.warning("Skipping non-dict point at index %d", i)
            skipped += 1
            continue

        point_type_str = raw_point.get("point_type", "")
        if point_type_str not in valid_types:
            logger.warning(
                "Skipping point %d with invalid type: %r", i, point_type_str
            )
            skipped += 1
            continue

        text = raw_point.get("text", "")
        if not text or not isinstance(text, str) or len(text.strip()) < 10:
            logger.warning(
                "Skipping point %d (%s): text too short (%d chars)",
                i, point_type_str, len(text) if text else 0,
            )
            skipped += 1
            continue

        try:
            point = ReasoningPoint(
                point_type=ReasoningPointType(point_type_str),
                text=text.strip(),
                sequence=len(points),  # Sequential index among valid points
                source_paragraphs=_safe_int_list(raw_point.get("source_paragraphs")),
                issue_addressed=_safe_str(raw_point.get("issue_addressed")),
                sections_cited=_safe_str_list(raw_point.get("sections_cited")),
                precedents_cited=_safe_str_list(raw_point.get("precedents_cited")),
                scope=_safe_str(raw_point.get("scope")),
                limitations=_safe_str(raw_point.get("limitations")),
                evidence_type=_safe_str(raw_point.get("evidence_type")),
                admissibility_ruling=_safe_str(raw_point.get("admissibility_ruling")),
                weight_given=_safe_str(raw_point.get("weight_given")),
                strength_assessment=_safe_str(raw_point.get("strength_assessment")),
                dissenting_judge=_safe_str(raw_point.get("dissenting_judge")),
                extraction_confidence=_safe_float(
                    raw_point.get("extraction_confidence"), default=0.5
                ),
            )
            points.append(point)
        except Exception as e:
            logger.warning(
                "Skipping point %d (%s): validation failed: %s",
                i, point_type_str, e,
            )
            skipped += 1

    if skipped:
        logger.warning(
            "Reasoning extraction: %d valid points, %d skipped out of %d raw",
            len(points), skipped, len(raw_points),
        )

    # Validate expected structure
    _validate_decomposition(points)

    return ReasoningDecomposition(
        points=points,
        total_issues=total_issues if isinstance(total_issues, int) else 0,
        extraction_metadata={
            "raw_count": len(raw_points),
            "valid_count": len(points),
            "skipped_count": skipped,
        },
    )


def _validate_decomposition(points: list[ReasoningPoint]) -> None:
    """Log warnings for structurally incomplete decompositions."""
    type_counts: dict[str, int] = {}
    for p in points:
        type_counts[p.point_type.value] = type_counts.get(p.point_type.value, 0) + 1

    if "facts" not in type_counts:
        logger.warning("Decomposition missing FACTS point")
    if "final_order" not in type_counts:
        logger.warning("Decomposition missing FINAL_ORDER point")
    if "court_reasoning" not in type_counts:
        logger.warning("Decomposition missing COURT_REASONING point")

    issue_count = type_counts.get("issue", 0)
    reasoning_count = type_counts.get("court_reasoning", 0)
    if issue_count > 0 and reasoning_count > 0 and issue_count != reasoning_count:
        logger.warning(
            "Issue/reasoning count mismatch: %d issues vs %d reasoning points",
            issue_count, reasoning_count,
        )


def _safe_str(val: object) -> Optional[str]:
    """Convert to string or None. Filters empty/null values."""
    if val is None:
        return None
    s = str(val).strip()
    return s if len(s) > 0 else None


def _safe_str_list(val: object) -> list[str]:
    """Convert to list of strings. Handles None and non-list gracefully."""
    if not val or not isinstance(val, list):
        return []
    return [str(v).strip() for v in val if v and str(v).strip()]


def _safe_int_list(val: object) -> list[int]:
    """Convert to list of ints. Handles None and mixed types gracefully."""
    if not val or not isinstance(val, list):
        return []
    result = []
    for v in val:
        try:
            result.append(int(v))
        except (ValueError, TypeError):
            pass
    return result


def _safe_float(val: object, default: float = 0.5) -> float:
    """Convert to float in [0, 1] range. Returns default on failure."""
    if val is None:
        return default
    try:
        f = float(str(val))
        return max(0.0, min(1.0, f))
    except (ValueError, TypeError):
        return default
