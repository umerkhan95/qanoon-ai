"""Qdrant collection management for pk_judgments.

Single responsibility: create, check, and delete the pk_judgments collection.
Collection has two named vector spaces:
  - "dense": Voyage 3.5 semantic embeddings (1024-dim, cosine)
  - "sparse": BM25 keyword vectors for citation/section matching
"""

from __future__ import annotations

import logging
import os

from qdrant_client import QdrantClient, models

logger = logging.getLogger(__name__)

COLLECTION_NAME = "pk_judgments"

# Payload fields to index for filtered search
INDEXED_FIELDS = [
    ("court_level", models.PayloadSchemaType.KEYWORD),
    ("case_type", models.PayloadSchemaType.KEYWORD),
    ("jurisdiction_province", models.PayloadSchemaType.KEYWORD),
    ("judgment_type", models.PayloadSchemaType.KEYWORD),
    ("offense_category", models.PayloadSchemaType.KEYWORD),
    ("severity_level", models.PayloadSchemaType.KEYWORD),
    ("special_law", models.PayloadSchemaType.KEYWORD),
    ("appeal_outcome", models.PayloadSchemaType.KEYWORD),
    ("sentence_type", models.PayloadSchemaType.KEYWORD),
    ("date_judgment", models.PayloadSchemaType.DATETIME),
    ("case_number", models.PayloadSchemaType.KEYWORD),
    # Point identity & hierarchy (ticket #26)
    ("point_type", models.PayloadSchemaType.KEYWORD),
    ("parent_case_id", models.PayloadSchemaType.KEYWORD),
    ("court_code", models.PayloadSchemaType.KEYWORD),
    ("tier_c_field", models.PayloadSchemaType.KEYWORD),
]


def get_client() -> QdrantClient:
    """Create a Qdrant client from environment variables.

    If QDRANT_URL is not set, uses in-memory mode (for dev/testing).
    """
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")

    if url:
        logger.info("Connecting to Qdrant at %s", url)
        return QdrantClient(url=url, api_key=api_key)

    logger.info("No QDRANT_URL set — using in-memory Qdrant (dev mode)")
    return QdrantClient(":memory:")


def collection_exists(client: QdrantClient) -> bool:
    """Check if pk_judgments collection exists."""
    collections = client.get_collections().collections
    return any(c.name == COLLECTION_NAME for c in collections)


def create_collection(client: QdrantClient, dimensions: int = 1024) -> None:
    """Create pk_judgments collection with dense + sparse vectors.

    Args:
        client: Qdrant client instance.
        dimensions: Dense vector dimensions (matches VOYAGE_DIMENSIONS).
    """
    if collection_exists(client):
        logger.info("Collection '%s' already exists — skipping creation", COLLECTION_NAME)
        return

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "dense": models.VectorParams(
                size=dimensions,
                distance=models.Distance.COSINE,
            ),
        },
        sparse_vectors_config={
            "sparse": models.SparseVectorParams(),
        },
        quantization_config=models.ScalarQuantization(
            scalar=models.ScalarQuantizationConfig(
                type=models.ScalarType.INT8,
                always_ram=True,
            ),
        ),
    )
    logger.info(
        "Created collection '%s' (dense=%dd + sparse, scalar quantization)",
        COLLECTION_NAME,
        dimensions,
    )

    # Create payload indexes for filtered search
    for field_name, field_type in INDEXED_FIELDS:
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=field_name,
            field_schema=field_type,
        )
        logger.debug("Indexed payload field: %s (%s)", field_name, field_type)

    logger.info("Created %d payload indexes", len(INDEXED_FIELDS))


def delete_collection(client: QdrantClient) -> None:
    """Delete pk_judgments collection (use with caution)."""
    if not collection_exists(client):
        logger.info("Collection '%s' does not exist — nothing to delete", COLLECTION_NAME)
        return

    client.delete_collection(collection_name=COLLECTION_NAME)
    logger.info("Deleted collection '%s'", COLLECTION_NAME)


def get_collection_info(client: QdrantClient) -> dict:
    """Return collection stats."""
    if not collection_exists(client):
        return {"exists": False}

    info = client.get_collection(collection_name=COLLECTION_NAME)
    return {
        "exists": True,
        "points_count": info.points_count,
        "indexed_vectors_count": info.indexed_vectors_count,
        "status": info.status.value if info.status else "unknown",
    }
