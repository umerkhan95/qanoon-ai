"""Ingest judgments into Qdrant pk_judgments collection.

Single responsibility: judgment text + extraction result → embedded Qdrant points.

One judgment produces N points:
  1. full_text  — Full judgment as single vector (primary search entry)
  2. chunk:{N}  — Only for long judgments (>100K chars), paragraph-split chunks
  3. tier_c:{field} — Each Tier C reasoning text as a separate searchable vector

All points share a parent_case_id for grouping and carry structured metadata.
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections import Counter
from typing import Optional

from qdrant_client import QdrantClient, models

from .collections import COLLECTION_NAME
from .embeddings import embed_batch, embed_document
from .point_id import (
    PointType,
    make_chunk_id,
    make_full_text_id,
    make_tier_c_id,
)

logger = logging.getLogger(__name__)

# Qdrant recommended batch size for upserts
UPSERT_BATCH_SIZE = 100


def _build_sparse_vector(text: str) -> Optional[models.SparseVector]:
    """Build a term-frequency sparse vector for BM25-style matching.

    Extracts legal terms, citation patterns, and section numbers.
    """
    if not text:
        return None

    text_lower = text.lower()

    # Words 3+ chars
    tokens = re.findall(r"\b[a-z]{3,}\b", text_lower)

    # PPC/CrPC section references
    section_refs = re.findall(
        r"section\s+\d+[a-z]?(?:\s*[-/]\s*\d+[a-z]?)?",
        text_lower,
    )
    tokens.extend(section_refs)

    # Citation patterns (PLD, SCMR, etc.)
    citations = re.findall(
        r"\b(?:pld|scmr|clc|pcrlj|ptd|plc|cld|ylr|mld)\s+\d{4}\b",
        text_lower,
    )
    tokens.extend(citations)

    if not tokens:
        return None

    tf = Counter(tokens)
    index_map: dict[int, float] = {}
    for token, count in tf.items():
        idx = int(hashlib.md5(token.encode()).hexdigest()[:8], 16)
        if idx in index_map:
            index_map[idx] += float(count)
        else:
            index_map[idx] = float(count)

    return models.SparseVector(
        indices=list(index_map.keys()),
        values=list(index_map.values()),
    )


def _make_point(
    point_id: str,
    dense_vector: list[float],
    payload: dict,
    text: str,
) -> models.PointStruct:
    """Create a Qdrant PointStruct with dense + sparse vectors."""
    vectors: dict = {"dense": dense_vector}
    sparse = _build_sparse_vector(text)
    if sparse is not None:
        vectors["sparse"] = sparse

    return models.PointStruct(
        id=point_id,
        vector=vectors,
        payload=payload,
    )


def ingest_judgment(
    client: QdrantClient,
    text: str,
    payload: dict,
    court: str,
    case_number: str,
    chunks: list[dict] | None = None,
    tier_c_texts: dict[str, str] | None = None,
    sac_summary: str = "",
) -> list[str]:
    """Ingest a single judgment as one or more Qdrant points.

    Args:
        client: Qdrant client.
        text: Full judgment text.
        payload: Flat dict from CriminalExtractionResult.to_qdrant_payload().
        court: Court code (e.g., "SC", "LHC", "SHC").
        case_number: Case number for ID generation.
        chunks: Pre-computed chunks from chunker.chunk_judgment(). If None
                and text is short, a single full_text point is created.
        tier_c_texts: Dict of {field_name: text} from to_vector_texts().
        sac_summary: SAC summary string to store in payload.

    Returns:
        List of upserted point UUIDs.
    """
    if not text or not text.strip():
        logger.error("Empty text for case %s — skipping", case_number)
        return []

    if not case_number:
        logger.error("No case_number provided — skipping")
        return []

    point_ids: list[str] = []

    # Shared metadata for all points of this judgment
    pid_full = make_full_text_id(court, case_number)
    base_payload = {
        **payload,
        "parent_case_id": pid_full.parent_uuid,
        "parent_case_key": pid_full.parent_key,
        "court_code": court,
    }
    if sac_summary:
        base_payload["sac_summary"] = sac_summary

    # ── Point 1: Full text (or chunks for long judgments) ──

    if chunks and len(chunks) > 1:
        # Long judgment: store each chunk as a separate point
        chunk_texts = [c["text"] for c in chunks]
        logger.info("Embedding %d chunks for %s", len(chunk_texts), case_number)
        chunk_vectors = embed_batch(chunk_texts, input_type="document")

        if len(chunk_vectors) != len(chunk_texts):
            raise ValueError(
                f"Embedding count mismatch for {case_number}: "
                f"sent {len(chunk_texts)} texts, got {len(chunk_vectors)} vectors"
            )

        for i, (chunk, vector) in enumerate(zip(chunks, chunk_vectors)):
            pid = make_chunk_id(court, case_number, i)
            chunk_payload = {
                **base_payload,
                "point_type": PointType.CHUNK.value,
                "point_key": pid.key,
                "chunk_index": chunk.get("chunk_index", i),
                "total_chunks": chunk.get("total_chunks", len(chunks)),
                "section_type": chunk.get("section_type", "body"),
            }
            point = _make_point(pid.uuid, vector, chunk_payload, chunk["text"])
            _upsert_single(client, point)
            point_ids.append(pid.uuid)

        logger.info("Ingested %d chunk points for %s", len(point_ids), case_number)
    else:
        # Short judgment (or single chunk): store as full_text point
        logger.info("Embedding full text for %s (%d chars)", case_number, len(text))
        dense_vector = embed_document(text)
        full_payload = {
            **base_payload,
            "point_type": PointType.FULL_TEXT.value,
            "point_key": pid_full.key,
        }
        point = _make_point(pid_full.uuid, dense_vector, full_payload, text)
        _upsert_single(client, point)
        point_ids.append(pid_full.uuid)

    # ── Point 2+: Tier C reasoning texts ──

    if tier_c_texts:
        tier_c_ids = _ingest_tier_c(
            client, court, case_number, tier_c_texts, base_payload,
        )
        point_ids.extend(tier_c_ids)

    logger.info(
        "Ingested %s: %d total points (court=%s)",
        case_number, len(point_ids), court,
    )
    return point_ids


def _ingest_tier_c(
    client: QdrantClient,
    court: str,
    case_number: str,
    tier_c_texts: dict[str, str],
    base_payload: dict,
) -> list[str]:
    """Embed and upsert Tier C reasoning text fields as separate points."""
    # Filter to non-empty texts
    valid = {k: v for k, v in tier_c_texts.items() if v and v.strip()}
    skipped = set(tier_c_texts.keys()) - set(valid.keys())
    if skipped:
        logger.warning(
            "Skipped %d empty Tier C fields for %s: %s",
            len(skipped), case_number, sorted(skipped),
        )
    if not valid:
        return []

    field_names = list(valid.keys())
    texts = list(valid.values())
    logger.info("Embedding %d Tier C fields for %s", len(texts), case_number)
    vectors = embed_batch(texts, input_type="document")

    if len(vectors) != len(texts):
        raise ValueError(
            f"Tier C embedding count mismatch for {case_number}: "
            f"sent {len(texts)} texts, got {len(vectors)} vectors"
        )

    point_ids: list[str] = []
    for field_name, text, vector in zip(field_names, texts, vectors):
        pid = make_tier_c_id(court, case_number, field_name)
        tier_c_payload = {
            **base_payload,
            "point_type": PointType.TIER_C.value,
            "point_key": pid.key,
            "tier_c_field": field_name,
        }
        point = _make_point(pid.uuid, vector, tier_c_payload, text)
        _upsert_single(client, point)
        point_ids.append(pid.uuid)

    logger.info("Ingested %d Tier C points for %s", len(point_ids), case_number)
    return point_ids


def ingest_batch(
    client: QdrantClient,
    items: list[dict],
) -> list[str]:
    """Ingest a batch of judgments.

    Each item must have:
        - "text": full judgment text
        - "payload": dict from to_qdrant_payload()
        - "court": str (e.g., "SC")
        - "case_number": str
    Optional:
        - "chunks": list of chunk dicts
        - "tier_c_texts": dict of {field_name: text}
        - "sac_summary": str

    Returns:
        List of all upserted point UUIDs.
    """
    if not items:
        return []

    all_ids: list[str] = []
    for idx, item in enumerate(items):
        try:
            ids = ingest_judgment(
                client=client,
                text=item["text"],
                payload=item["payload"],
                court=item["court"],
                case_number=item["case_number"],
                chunks=item.get("chunks"),
                tier_c_texts=item.get("tier_c_texts"),
                sac_summary=item.get("sac_summary", ""),
            )
            all_ids.extend(ids)
        except Exception as e:
            logger.error(
                "[%d/%d] Failed to ingest %s: %s: %s",
                idx + 1, len(items),
                item.get("case_number", "?"),
                type(e).__name__, e,
            )

    logger.info("Batch ingested %d items → %d total points", len(items), len(all_ids))
    return all_ids


def _upsert_single(client: QdrantClient, point: models.PointStruct) -> None:
    """Upsert a single point to Qdrant."""
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[point],
    )
