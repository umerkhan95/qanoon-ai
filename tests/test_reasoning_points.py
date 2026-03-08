"""Tests for Reasoning Point Decomposition (ticket #25).

Unit tests (no network, no LLM) for schema validation, parsing,
edge cases, and data quality.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extractors.criminal.reasoning_schema import (
    ReasoningDecomposition,
    ReasoningPoint,
    ReasoningPointType,
)
from src.extractors.criminal.reasoning_points import (
    _parse_decomposition,
    _safe_float,
    _safe_int_list,
    _safe_str,
    _safe_str_list,
    _truncate_for_extraction,
    _validate_decomposition,
)
from src.qdrant.point_id import PointType, make_reasoning_id


# ── Schema Tests ───────────────────────────────────────────────────


def test_reasoning_point_type_values():
    """All 10 point types must exist."""
    types = {t.value for t in ReasoningPointType}
    expected = {
        "facts", "issue", "petitioner_argument", "respondent_argument",
        "evidence", "court_reasoning", "ratio_decidendi", "obiter_dicta",
        "final_order", "dissent",
    }
    assert types == expected


def test_reasoning_point_minimum_text():
    """Text must be at least 10 chars."""
    import pytest
    with pytest.raises(Exception):
        ReasoningPoint(
            point_type=ReasoningPointType.FACTS,
            text="short",
            sequence=0,
        )


def test_reasoning_point_valid():
    rp = ReasoningPoint(
        point_type=ReasoningPointType.FACTS,
        text="The accused was charged under Section 302 PPC for murder.",
        sequence=0,
        source_paragraphs=[1, 2, 3],
        sections_cited=["Section 302 PPC"],
        extraction_confidence=0.9,
    )
    assert rp.point_type == ReasoningPointType.FACTS
    assert rp.sequence == 0
    assert len(rp.sections_cited) == 1
    assert rp.extraction_confidence == 0.9


def test_reasoning_point_serialization():
    rp = ReasoningPoint(
        point_type=ReasoningPointType.RATIO_DECIDENDI,
        text="The binding principle is that lack of motive is a mitigating factor.",
        sequence=5,
        scope="Murder cases under Section 302 PPC",
        limitations="Only applicable where motive is not alleged by prosecution",
    )
    data = rp.model_dump(mode="json")
    assert data["point_type"] == "ratio_decidendi"
    assert data["scope"] == "Murder cases under Section 302 PPC"
    assert data["limitations"] is not None


def test_reasoning_point_confidence_clamped():
    """Confidence must be 0.0-1.0."""
    import pytest
    with pytest.raises(Exception):
        ReasoningPoint(
            point_type=ReasoningPointType.FACTS,
            text="Some valid text here for testing.",
            sequence=0,
            extraction_confidence=1.5,
        )


def test_decomposition_to_ingestable_texts():
    decomp = ReasoningDecomposition(
        points=[
            ReasoningPoint(
                point_type=ReasoningPointType.FACTS,
                text="The accused murdered the victim with a pistol.",
                sequence=0,
                sections_cited=["Section 302 PPC"],
            ),
            ReasoningPoint(
                point_type=ReasoningPointType.FINAL_ORDER,
                text="The appeal is dismissed and conviction is maintained.",
                sequence=1,
            ),
        ],
        total_issues=1,
    )
    result = decomp.to_ingestable_texts()
    assert len(result) == 2
    assert result[0]["point_type"] == "facts"
    assert result[0]["sequence"] == 0
    assert "accused murdered" in result[0]["text"]
    assert result[0]["payload"]["sections_cited"] == ["Section 302 PPC"]
    assert result[1]["point_type"] == "final_order"
    assert result[1]["sequence"] == 1


def test_decomposition_empty():
    decomp = ReasoningDecomposition()
    assert decomp.points == []
    assert decomp.to_ingestable_texts() == []


# ── Parsing Tests ──────────────────────────────────────────────────


def test_parse_valid_decomposition():
    raw = {
        "points": [
            {
                "point_type": "facts",
                "text": "The accused Muhammad Shah was charged under Section 302 PPC for the murder of deceased.",
                "source_paragraphs": [1, 2],
                "sections_cited": ["Section 302 PPC"],
                "extraction_confidence": 0.9,
            },
            {
                "point_type": "issue",
                "text": "Whether the prosecution proved the guilt of the accused beyond reasonable doubt.",
                "issue_addressed": "Proof beyond reasonable doubt",
                "source_paragraphs": [4],
                "extraction_confidence": 0.8,
            },
            {
                "point_type": "final_order",
                "text": "The appeal is dismissed. The conviction and sentence are maintained.",
                "source_paragraphs": [10],
                "extraction_confidence": 1.0,
            },
        ],
        "total_issues": 1,
    }
    decomp = _parse_decomposition(raw)
    assert len(decomp.points) == 3
    assert decomp.total_issues == 1
    assert decomp.points[0].point_type == ReasoningPointType.FACTS
    assert decomp.points[1].issue_addressed == "Proof beyond reasonable doubt"
    assert decomp.points[2].extraction_confidence == 1.0


def test_parse_skips_invalid_type():
    raw = {
        "points": [
            {"point_type": "invalid_type", "text": "Some valid text here for this point."},
            {"point_type": "facts", "text": "The accused was charged under Section 302 PPC."},
        ],
        "total_issues": 0,
    }
    decomp = _parse_decomposition(raw)
    assert len(decomp.points) == 1
    assert decomp.extraction_metadata["skipped_count"] == 1


def test_parse_skips_short_text():
    raw = {
        "points": [
            {"point_type": "facts", "text": "Short"},
            {"point_type": "issue", "text": "Whether the prosecution proved guilt beyond reasonable doubt in this case."},
        ],
        "total_issues": 1,
    }
    decomp = _parse_decomposition(raw)
    assert len(decomp.points) == 1
    assert decomp.points[0].point_type == ReasoningPointType.ISSUE


def test_parse_skips_non_dict_points():
    raw = {
        "points": [
            "not a dict",
            {"point_type": "facts", "text": "The accused was charged under Section 302 PPC for murder."},
        ],
        "total_issues": 0,
    }
    decomp = _parse_decomposition(raw)
    assert len(decomp.points) == 1


def test_parse_non_list_points():
    raw = {"points": "not a list", "total_issues": 0}
    decomp = _parse_decomposition(raw)
    assert len(decomp.points) == 0
    assert "error" in decomp.extraction_metadata


def test_parse_empty_points():
    raw = {"points": [], "total_issues": 0}
    decomp = _parse_decomposition(raw)
    assert len(decomp.points) == 0


def test_parse_missing_points_key():
    raw = {"total_issues": 0}
    decomp = _parse_decomposition(raw)
    assert len(decomp.points) == 0


def test_parse_sequence_numbering():
    """Parsed points get sequential indices (0, 1, 2...)."""
    raw = {
        "points": [
            {"point_type": "facts", "text": "Fact text here for testing purposes in this case."},
            {"point_type": "invalid", "text": "This one gets skipped entirely."},
            {"point_type": "final_order", "text": "Order text here for the final disposition of appeal."},
        ],
        "total_issues": 0,
    }
    decomp = _parse_decomposition(raw)
    assert len(decomp.points) == 2
    assert decomp.points[0].sequence == 0
    assert decomp.points[1].sequence == 1


def test_parse_null_optional_fields():
    """Null optional fields should parse cleanly."""
    raw = {
        "points": [
            {
                "point_type": "facts",
                "text": "The accused was charged under Section 302 PPC for murder.",
                "source_paragraphs": None,
                "issue_addressed": None,
                "sections_cited": None,
                "precedents_cited": None,
                "scope": None,
                "limitations": None,
                "evidence_type": None,
                "admissibility_ruling": None,
                "weight_given": None,
                "strength_assessment": None,
                "dissenting_judge": None,
                "extraction_confidence": None,
            },
        ],
        "total_issues": 0,
    }
    decomp = _parse_decomposition(raw)
    assert len(decomp.points) == 1
    assert decomp.points[0].source_paragraphs == []
    assert decomp.points[0].sections_cited == []
    assert decomp.points[0].extraction_confidence == 0.5  # default


# ── Helper Function Tests ──────────────────────────────────────────


def test_safe_str():
    assert _safe_str(None) is None
    assert _safe_str("") is None
    assert _safe_str("  ") is None
    assert _safe_str("hello") == "hello"
    assert _safe_str("  spaced  ") == "spaced"
    assert _safe_str(123) == "123"


def test_safe_str_list():
    assert _safe_str_list(None) == []
    assert _safe_str_list("not a list") == []
    assert _safe_str_list([]) == []
    assert _safe_str_list(["a", "b"]) == ["a", "b"]
    assert _safe_str_list(["a", None, "", "b"]) == ["a", "b"]
    assert _safe_str_list(["  spaced  "]) == ["spaced"]


def test_safe_int_list():
    assert _safe_int_list(None) == []
    assert _safe_int_list("not a list") == []
    assert _safe_int_list([1, 2, 3]) == [1, 2, 3]
    assert _safe_int_list(["1", "2"]) == [1, 2]
    assert _safe_int_list([1, "abc", 3]) == [1, 3]
    assert _safe_int_list([1.5]) == [1]


def test_safe_float():
    assert _safe_float(None) == 0.5
    assert _safe_float(0.8) == 0.8
    assert _safe_float("0.9") == 0.9
    assert _safe_float(1.5) == 1.0  # clamped
    assert _safe_float(-0.5) == 0.0  # clamped
    assert _safe_float("invalid") == 0.5  # default


def test_truncate_short():
    text = "Short text"
    assert _truncate_for_extraction(text) == text


def test_truncate_long():
    text = "a" * 50000
    result = _truncate_for_extraction(text)
    assert len(result) < 50000
    assert "MIDDLE SECTION OMITTED" in result
    # Head is 18K, tail is 12K
    parts = result.split("[...MIDDLE SECTION OMITTED FOR LENGTH...]")
    assert len(parts) == 2
    assert len(parts[0].rstrip()) == 18000
    assert len(parts[1].lstrip()) == 12000


# ── Validation Tests ───────────────────────────────────────────────


def test_validate_complete(caplog):
    """Complete decomposition should not warn."""
    import logging
    points = [
        ReasoningPoint(point_type=ReasoningPointType.FACTS, text="Facts text here for this case.", sequence=0),
        ReasoningPoint(point_type=ReasoningPointType.COURT_REASONING, text="Reasoning text here for this issue.", sequence=1),
        ReasoningPoint(point_type=ReasoningPointType.FINAL_ORDER, text="Order text here for disposition.", sequence=2),
    ]
    with caplog.at_level(logging.WARNING):
        _validate_decomposition(points)
    assert "missing" not in caplog.text
    assert "mismatch" not in caplog.text


def test_validate_missing_facts(caplog):
    """Missing facts should log warning."""
    import logging
    points = [
        ReasoningPoint(point_type=ReasoningPointType.FINAL_ORDER, text="Order text here for this case.", sequence=0),
    ]
    with caplog.at_level(logging.WARNING):
        _validate_decomposition(points)
    assert "missing FACTS" in caplog.text


def test_validate_issue_reasoning_mismatch(caplog):
    """Different issue and reasoning counts should warn."""
    import logging
    points = [
        ReasoningPoint(point_type=ReasoningPointType.FACTS, text="Facts text here for this case.", sequence=0),
        ReasoningPoint(point_type=ReasoningPointType.ISSUE, text="Issue one text for this legal question.", sequence=1),
        ReasoningPoint(point_type=ReasoningPointType.ISSUE, text="Issue two text for another legal question.", sequence=2),
        ReasoningPoint(point_type=ReasoningPointType.COURT_REASONING, text="Only one reasoning text for the issues.", sequence=3),
        ReasoningPoint(point_type=ReasoningPointType.FINAL_ORDER, text="Order text here for this case.", sequence=4),
    ]
    with caplog.at_level(logging.WARNING):
        _validate_decomposition(points)
    assert "mismatch" in caplog.text


# ── Point ID Tests ─────────────────────────────────────────────────


def test_reasoning_point_id_structure():
    pid = make_reasoning_id("SC", "CRL.A.1-K_2018", 5)
    assert pid.key == "SC:CRL.A.1-K_2018:reasoning:5"
    assert pid.point_type == PointType.REASONING


def test_reasoning_point_id_deterministic():
    pid1 = make_reasoning_id("SC", "CRL.A.1-K_2018", 5)
    pid2 = make_reasoning_id("SC", "CRL.A.1-K_2018", 5)
    assert pid1.uuid == pid2.uuid


def test_reasoning_point_id_differs_by_sequence():
    pid1 = make_reasoning_id("SC", "CRL.A.1-K_2018", 0)
    pid2 = make_reasoning_id("SC", "CRL.A.1-K_2018", 1)
    assert pid1.uuid != pid2.uuid


def test_reasoning_point_id_shares_parent():
    from src.qdrant.point_id import make_full_text_id
    pid_full = make_full_text_id("SC", "CRL.A.1-K_2018")
    pid_reasoning = make_reasoning_id("SC", "CRL.A.1-K_2018", 3)
    assert pid_full.parent_key == pid_reasoning.parent_key
    assert pid_full.parent_uuid == pid_reasoning.parent_uuid


def test_reasoning_point_id_differs_from_other_types():
    from src.qdrant.point_id import make_chunk_id, make_tier_c_id
    pid_reasoning = make_reasoning_id("SC", "CRL.A.1-K_2018", 0)
    pid_chunk = make_chunk_id("SC", "CRL.A.1-K_2018", 0)
    pid_tier_c = make_tier_c_id("SC", "CRL.A.1-K_2018", "ratio_decidendi")
    assert len({pid_reasoning.uuid, pid_chunk.uuid, pid_tier_c.uuid}) == 3


# ── Data Quality Tests ─────────────────────────────────────────────


def test_no_data_loss_in_ingestable():
    """Every point in decomposition must appear in ingestable output."""
    points = [
        ReasoningPoint(
            point_type=ReasoningPointType.FACTS,
            text="Fact text A for testing data quality.",
            sequence=0,
            sections_cited=["Section 302 PPC"],
        ),
        ReasoningPoint(
            point_type=ReasoningPointType.ISSUE,
            text="Issue text B whether prosecution proved guilt.",
            sequence=1,
            issue_addressed="Proof of guilt",
        ),
        ReasoningPoint(
            point_type=ReasoningPointType.COURT_REASONING,
            text="Reasoning text C the court analyzed the evidence.",
            sequence=2,
            precedents_cited=["PLD 2020 SC 1"],
        ),
    ]
    decomp = ReasoningDecomposition(points=points, total_issues=1)
    ingestable = decomp.to_ingestable_texts()

    assert len(ingestable) == len(points)
    for i, (point, ing) in enumerate(zip(points, ingestable)):
        assert ing["text"] == point.text, f"Text mismatch at index {i}"
        assert ing["sequence"] == point.sequence, f"Sequence mismatch at index {i}"
        assert ing["point_type"] == point.point_type.value, f"Type mismatch at index {i}"


def test_payload_excludes_text_sequence_and_point_type():
    """Payload in ingestable should NOT contain text, sequence, or point_type.

    point_type is excluded because it would collide with the Qdrant-level
    point_type field ("reasoning"). The reasoning-specific type is stored
    separately as reasoning_point_type in the ingestion layer.
    """
    point = ReasoningPoint(
        point_type=ReasoningPointType.FACTS,
        text="The accused was charged under Section 302.",
        sequence=0,
    )
    decomp = ReasoningDecomposition(points=[point])
    result = decomp.to_ingestable_texts()
    payload = result[0]["payload"]
    assert "text" not in payload
    assert "sequence" not in payload
    assert "point_type" not in payload
    # But the point_type IS available at the top level of the dict
    assert result[0]["point_type"] == "facts"


def test_all_metadata_preserved_in_payload():
    """All point metadata must survive serialization into payload."""
    point = ReasoningPoint(
        point_type=ReasoningPointType.EVIDENCE,
        text="The medical evidence showed cause of death was firearm injury.",
        sequence=3,
        source_paragraphs=[5, 6],
        evidence_type="forensic",
        admissibility_ruling="admitted",
        weight_given="relied_upon",
        sections_cited=["Article 164-A QSO"],
        extraction_confidence=0.85,
    )
    decomp = ReasoningDecomposition(points=[point])
    result = decomp.to_ingestable_texts()
    payload = result[0]["payload"]
    assert payload["evidence_type"] == "forensic"
    assert payload["admissibility_ruling"] == "admitted"
    assert payload["weight_given"] == "relied_upon"
    assert payload["sections_cited"] == ["Article 164-A QSO"]
    assert payload["source_paragraphs"] == [5, 6]
    assert payload["extraction_confidence"] == 0.85


def test_parse_preserves_all_evidence_fields():
    """Evidence points must carry type, admissibility, and weight through parsing."""
    raw = {
        "points": [
            {
                "point_type": "evidence",
                "text": "The DNA evidence was admitted by the court and given significant weight.",
                "evidence_type": "forensic",
                "admissibility_ruling": "admitted",
                "weight_given": "relied_upon",
                "source_paragraphs": [7],
                "extraction_confidence": 0.9,
            },
        ],
        "total_issues": 0,
    }
    decomp = _parse_decomposition(raw)
    assert len(decomp.points) == 1
    ev = decomp.points[0]
    assert ev.evidence_type == "forensic"
    assert ev.admissibility_ruling == "admitted"
    assert ev.weight_given == "relied_upon"
    assert ev.source_paragraphs == [7]


def test_parse_preserves_argument_fields():
    """Argument points must carry strength assessment through parsing."""
    raw = {
        "points": [
            {
                "point_type": "petitioner_argument",
                "text": "The learned counsel argued that the prosecution failed to prove motive.",
                "strength_assessment": "strong",
                "precedents_cited": ["PLD 2019 SC 500"],
                "source_paragraphs": [4],
                "extraction_confidence": 0.8,
            },
        ],
        "total_issues": 0,
    }
    decomp = _parse_decomposition(raw)
    assert len(decomp.points) == 1
    arg = decomp.points[0]
    assert arg.strength_assessment == "strong"
    assert arg.precedents_cited == ["PLD 2019 SC 500"]


def test_parse_preserves_ratio_scope():
    """Ratio decidendi must carry scope and limitations."""
    raw = {
        "points": [
            {
                "point_type": "ratio_decidendi",
                "text": "Where motive is not proved, the court may reduce sentence from death to life imprisonment.",
                "scope": "Murder cases under Section 302 PPC",
                "limitations": "Only where prosecution fails to allege motive",
                "precedents_cited": ["2020 SCMR 100"],
                "extraction_confidence": 1.0,
            },
        ],
        "total_issues": 0,
    }
    decomp = _parse_decomposition(raw)
    assert len(decomp.points) == 1
    ratio = decomp.points[0]
    assert ratio.scope == "Murder cases under Section 302 PPC"
    assert ratio.limitations is not None
    assert ratio.extraction_confidence == 1.0


# ── Run all tests ───────────────────────────────────────────────────

if __name__ == "__main__":
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print(f"  {name}: PASS")
    print("\nAll reasoning point tests passed!")
