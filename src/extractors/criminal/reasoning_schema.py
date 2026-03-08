"""Schema for atomic reasoning points decomposed from judgments.

Each judgment is decomposed into N independent reasoning points — one per
legal issue, per argument, per evidence item. Each point is independently
searchable in Qdrant with rich metadata.

This is separate from TierC (17 fixed fields). Reasoning points are
variable-count, hierarchical, and issue-specific.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ReasoningPointType(str, Enum):
    """Types of atomic reasoning points from a judgment."""

    FACTS = "facts"
    ISSUE = "issue"
    PETITIONER_ARGUMENT = "petitioner_argument"
    RESPONDENT_ARGUMENT = "respondent_argument"
    EVIDENCE = "evidence"
    COURT_REASONING = "court_reasoning"
    RATIO_DECIDENDI = "ratio_decidendi"
    OBITER_DICTA = "obiter_dicta"
    FINAL_ORDER = "final_order"
    DISSENT = "dissent"


class ReasoningPoint(BaseModel):
    """A single atomic reasoning point extracted from a judgment.

    Each point is independently searchable and carries enough metadata
    to be useful without loading the full judgment.
    """

    point_type: ReasoningPointType
    text: str = Field(min_length=10)
    sequence: int = Field(ge=0)

    # Context within the judgment
    source_paragraphs: list[int] = Field(default_factory=list)
    issue_addressed: Optional[str] = None

    # Legal references within THIS point
    sections_cited: list[str] = Field(default_factory=list)
    precedents_cited: list[str] = Field(default_factory=list)

    # For ratio/obiter
    scope: Optional[str] = None
    limitations: Optional[str] = None

    # For evidence points
    evidence_type: Optional[str] = None
    admissibility_ruling: Optional[str] = None
    weight_given: Optional[str] = None

    # For argument points
    strength_assessment: Optional[str] = None

    # For dissent
    dissenting_judge: Optional[str] = None

    # Extraction quality
    extraction_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ReasoningDecomposition(BaseModel):
    """Complete decomposition of a judgment into reasoning points."""

    points: list[ReasoningPoint] = Field(default_factory=list)
    total_issues: int = 0
    extraction_metadata: dict = Field(default_factory=dict)

    def to_ingestable_texts(self) -> list[dict]:
        """Convert to list of {sequence, point_type, text, payload} for ingestion.

        Returns list of dicts ready for embedding and Qdrant upsert.
        Each dict has:
            - sequence: int (point index)
            - point_type: str (enum value)
            - text: str (the reasoning text to embed)
            - payload: dict (point-specific metadata, namespaced to avoid
              collisions with base judgment payload)

        Note: point_type and sequence are excluded from payload because they
        are stored as separate top-level fields in the Qdrant point.
        """
        result = []
        for point in self.points:
            payload = point.model_dump(
                mode="json",
                exclude={"text", "sequence", "point_type"},
            )
            result.append({
                "sequence": point.sequence,
                "point_type": point.point_type.value,
                "text": point.text,
                "payload": payload,
            })
        return result
