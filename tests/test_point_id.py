"""Tests for Point ID generation and ingestion wiring.

Unit tests (no network, no Qdrant) for deterministic ID generation,
parent-child linking, and the full ingestion data flow.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.qdrant.point_id import (
    PointId,
    PointType,
    make_chunk_id,
    make_full_text_id,
    make_tier_c_id,
)


# ── Point ID Tests ──────────────────────────────────────────────────


def test_full_text_id_structure():
    pid = make_full_text_id("SC", "CRL.A.1-K_2018")
    assert pid.court == "SC"
    assert pid.case_number == "CRL.A.1-K_2018"
    assert pid.point_type == PointType.FULL_TEXT
    assert pid.sequence == "0"
    assert pid.key == "SC:CRL.A.1-K_2018:full_text:0"


def test_chunk_id_structure():
    pid = make_chunk_id("SC", "CRL.A.1-K_2018", 3)
    assert pid.key == "SC:CRL.A.1-K_2018:chunk:3"
    assert pid.point_type == PointType.CHUNK


def test_tier_c_id_structure():
    pid = make_tier_c_id("SC", "CRL.A.1-K_2018", "ratio_decidendi")
    assert pid.key == "SC:CRL.A.1-K_2018:tier_c:ratio_decidendi"
    assert pid.point_type == PointType.TIER_C


def test_deterministic_uuid():
    """Same inputs must always produce the same UUID."""
    pid1 = make_full_text_id("SC", "CRL.A.1-K_2018")
    pid2 = make_full_text_id("SC", "CRL.A.1-K_2018")
    assert pid1.uuid == pid2.uuid


def test_different_inputs_different_uuid():
    pid1 = make_full_text_id("SC", "CRL.A.1-K_2018")
    pid2 = make_full_text_id("SC", "CRL.A.2-K_2018")
    assert pid1.uuid != pid2.uuid


def test_different_point_types_different_uuid():
    pid_full = make_full_text_id("SC", "CRL.A.1-K_2018")
    pid_chunk = make_chunk_id("SC", "CRL.A.1-K_2018", 0)
    pid_tier_c = make_tier_c_id("SC", "CRL.A.1-K_2018", "ratio_decidendi")
    assert len({pid_full.uuid, pid_chunk.uuid, pid_tier_c.uuid}) == 3


def test_parent_key_shared():
    """All points of one judgment share the same parent key."""
    pid_full = make_full_text_id("SC", "CRL.A.1-K_2018")
    pid_chunk = make_chunk_id("SC", "CRL.A.1-K_2018", 5)
    pid_tier_c = make_tier_c_id("SC", "CRL.A.1-K_2018", "ratio_decidendi")

    assert pid_full.parent_key == pid_chunk.parent_key == pid_tier_c.parent_key
    assert pid_full.parent_uuid == pid_chunk.parent_uuid == pid_tier_c.parent_uuid
    assert pid_full.parent_key == "SC:CRL.A.1-K_2018"


def test_parent_key_differs_between_cases():
    pid1 = make_full_text_id("SC", "CRL.A.1-K_2018")
    pid2 = make_full_text_id("LHC", "WP.456_2022")
    assert pid1.parent_key != pid2.parent_key
    assert pid1.parent_uuid != pid2.parent_uuid


def test_uuid_is_valid_format():
    """UUID must be a valid UUID string."""
    import uuid
    pid = make_full_text_id("SC", "test")
    parsed = uuid.UUID(pid.uuid)
    assert str(parsed) == pid.uuid


def test_pydantic_serialization():
    pid = make_full_text_id("SC", "CRL.A.1-K_2018")
    data = pid.model_dump()
    assert isinstance(data, dict)
    assert data["court"] == "SC"
    assert data["point_type"] == "full_text"


# ── Ingestion Wiring Tests (no network) ─────────────────────────────


def test_build_sparse_vector():
    from src.qdrant.ingestion import _build_sparse_vector

    sv = _build_sparse_vector("section 302 PPC murder accused")
    assert sv is not None
    assert len(sv.indices) > 0
    assert len(sv.indices) == len(sv.values)


def test_build_sparse_vector_empty():
    from src.qdrant.ingestion import _build_sparse_vector

    assert _build_sparse_vector("") is None
    assert _build_sparse_vector("a b") is None  # words < 3 chars


def test_build_sparse_vector_citations():
    from src.qdrant.ingestion import _build_sparse_vector

    sv = _build_sparse_vector("PLD 2020 SC 1 and SCMR 2019 100")
    assert sv is not None
    # Should extract citation tokens
    assert len(sv.indices) > 0


def test_build_sparse_vector_deterministic():
    from src.qdrant.ingestion import _build_sparse_vector

    sv1 = _build_sparse_vector("section 302 PPC")
    sv2 = _build_sparse_vector("section 302 PPC")
    assert sv1.indices == sv2.indices
    assert sv1.values == sv2.values


# ── Run all tests ───────────────────────────────────────────────────


if __name__ == "__main__":
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print(f"  {name}: PASS")
    print("\nAll point_id tests passed!")
