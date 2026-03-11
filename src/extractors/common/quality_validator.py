"""Pre-ingestion data quality validator for extracted judgments.

Single responsibility: extraction result → quality report with pass/fail.
Validates completeness, consistency, and data integrity before Qdrant upsert.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class QualityReport:
    """Result of quality validation on an extracted judgment."""

    case_number: str = ""
    passed: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    field_coverage: float = 0.0  # Percentage of non-null fields

    def fail(self, msg: str) -> None:
        self.passed = False
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


# Fields that MUST be present for a valid judgment
REQUIRED_FIELDS = {"case_number", "court_name"}

# Fields that SHOULD be present (warn if missing)
EXPECTED_FIELDS = {
    "judge_names", "date_judgment", "ppc_sections",
    "precedents_cited",
}

# Minimum text length for a real judgment (not a stub/error page)
MIN_TEXT_LENGTH = 500

# Minimum Tier A fill rate to consider extraction successful
MIN_TIER_A_COVERAGE = 15.0  # percent


def validate_extraction(
    text: str,
    payload: dict[str, Any] | None,
    case_number: str = "",
) -> QualityReport:
    """Validate an extraction result before Qdrant ingestion.

    Args:
        text: Full judgment text.
        payload: Flat dict from CriminalExtractionResult.to_qdrant_payload().
        case_number: Case number for logging.

    Returns:
        QualityReport with pass/fail status and error/warning lists.
    """
    report = QualityReport(case_number=case_number)

    if payload is None:
        report.fail("Payload is None — extraction likely failed completely")
        return report

    # 1. Text length check
    if not text or len(text.strip()) < MIN_TEXT_LENGTH:
        report.fail(
            f"Text too short ({len(text) if text else 0} chars, "
            f"minimum {MIN_TEXT_LENGTH})"
        )
        return report

    # 2. Required fields
    for field_name in REQUIRED_FIELDS:
        val = payload.get(field_name)
        if not val:
            report.fail(f"Missing required field: {field_name}")

    # 3. Expected fields (warn only)
    for field_name in EXPECTED_FIELDS:
        val = payload.get(field_name)
        if not val or (isinstance(val, list) and len(val) == 0):
            report.warn(f"Missing expected field: {field_name}")

    # 4. Field coverage
    total = len(payload)
    filled = sum(
        1 for v in payload.values()
        if v is not None and v != [] and v != ""
    )
    report.field_coverage = round(filled / max(total, 1) * 100, 1)

    if report.field_coverage < MIN_TIER_A_COVERAGE:
        report.warn(
            f"Low field coverage: {report.field_coverage}% "
            f"(expected >={MIN_TIER_A_COVERAGE}%)"
        )

    # 5. Cross-field consistency checks
    _check_consistency(payload, report)

    # 6. Log summary
    if not report.passed:
        logger.error(
            "Quality FAIL for %s: %d errors, %d warnings — %s",
            case_number, len(report.errors), len(report.warnings),
            "; ".join(report.errors),
        )
    elif report.warnings:
        logger.warning(
            "Quality PASS with %d warnings for %s: %s",
            len(report.warnings), case_number,
            "; ".join(report.warnings[:3]),
        )

    return report


def _check_consistency(payload: dict, report: QualityReport) -> None:
    """Cross-field consistency checks."""
    # If sentence_type exists but no judgment_type, that's suspicious
    if payload.get("sentence_type") and not payload.get("judgment_type"):
        report.warn("Has sentence_type but no judgment_type")

    # If appeal_outcome exists, court_level should be high_court or supreme_court
    appeal = payload.get("appeal_outcome")
    level = payload.get("court_level")
    if appeal and level and level == "trial_court":
        report.warn("appeal_outcome set but court_level is trial_court")

    # If diyat_compromise is True, judgment should be acquittal or case_type should indicate
    if payload.get("diyat_compromise") and payload.get("judgment_type") == "conviction":
        report.warn("diyat_compromise=True but judgment_type=conviction")

    # Duplicate precedents check
    precedents = payload.get("precedents_cited", [])
    if len(precedents) != len(set(precedents)):
        report.warn(
            f"Duplicate precedents: {len(precedents)} total, "
            f"{len(set(precedents))} unique"
        )
