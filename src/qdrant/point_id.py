"""Deterministic Point ID generation for Qdrant.

Single responsibility: case identifiers → deterministic UUID point IDs.

Point ID structure (human-readable key before hashing):
  {court}:{case_number}:{point_type}:{sequence}

Examples:
  SC:CRL.A.1-K_2018:full_text:0     → UUID3(...)
  SC:CRL.A.1-K_2018:chunk:3         → UUID3(...)
  SC:CRL.A.1-K_2018:tier_c:ratio_decidendi → UUID3(...)

Properties:
  - Deterministic: same input always produces same UUID
  - Re-ingesting the same case overwrites (upsert deduplication)
  - Hierarchical: parent_case_id links all points for one judgment
"""

from __future__ import annotations

import uuid
from enum import Enum

from pydantic import BaseModel, field_validator


class PointType(str, Enum):
    FULL_TEXT = "full_text"
    CHUNK = "chunk"
    TIER_C = "tier_c"


class PointId(BaseModel):
    """A structured, deterministic Qdrant point identifier."""

    court: str
    case_number: str
    point_type: PointType
    sequence: str  # "0" for full_text, chunk index, or tier_c field name

    @field_validator("court", "case_number", "sequence")
    @classmethod
    def no_colons(cls, v: str) -> str:
        if ":" in v:
            raise ValueError(f"Field must not contain ':' delimiter, got: {v!r}")
        return v

    @property
    def key(self) -> str:
        """Human-readable key before hashing."""
        return f"{self.court}:{self.case_number}:{self.point_type.value}:{self.sequence}"

    @property
    def uuid(self) -> str:
        """Deterministic UUID3 for Qdrant."""
        return str(uuid.uuid3(uuid.NAMESPACE_URL, self.key))

    @property
    def parent_key(self) -> str:
        """Key identifying the parent case (shared by all points of one judgment)."""
        return f"{self.court}:{self.case_number}"

    @property
    def parent_uuid(self) -> str:
        """Deterministic UUID for the parent case."""
        return str(uuid.uuid3(uuid.NAMESPACE_URL, self.parent_key))


def make_full_text_id(court: str, case_number: str) -> PointId:
    """Create a point ID for the full-text judgment vector."""
    return PointId(
        court=court,
        case_number=case_number,
        point_type=PointType.FULL_TEXT,
        sequence="0",
    )


def make_chunk_id(court: str, case_number: str, chunk_index: int) -> PointId:
    """Create a point ID for a judgment chunk."""
    return PointId(
        court=court,
        case_number=case_number,
        point_type=PointType.CHUNK,
        sequence=str(chunk_index),
    )


def make_tier_c_id(court: str, case_number: str, field_name: str) -> PointId:
    """Create a point ID for a Tier C reasoning text vector."""
    return PointId(
        court=court,
        case_number=case_number,
        point_type=PointType.TIER_C,
        sequence=field_name,
    )
