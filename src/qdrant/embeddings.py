"""Voyage AI embedding service for Pakistani legal judgments.

Single responsibility: convert text -> dense vectors via Voyage 3.5.
No chunking needed — 32K token context handles full judgments.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import voyageai

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Raised when embedding call fails after retries."""


def _get_client() -> voyageai.Client:
    api_key = os.getenv("VOYAGE_API_KEY")
    if not api_key:
        raise EmbeddingError("VOYAGE_API_KEY not set in environment")
    return voyageai.Client(api_key=api_key)


def _get_model() -> str:
    return os.getenv("VOYAGE_MODEL", "voyage-3.5")


def _get_dimensions() -> int:
    return int(os.getenv("VOYAGE_DIMENSIONS", "1024"))


def embed_texts(
    texts: list[str],
    input_type: str = "document",
    model: str | None = None,
    max_retries: int = 3,
) -> list[list[float]]:
    """Embed a batch of texts via Voyage AI.

    Args:
        texts: List of texts to embed (max ~128 per batch per Voyage docs).
        input_type: "document" for indexing, "query" for search queries.
        model: Override model name (defaults to VOYAGE_MODEL env var).
        max_retries: Number of retry attempts with exponential backoff.

    Returns:
        List of embedding vectors (each is list[float] of VOYAGE_DIMENSIONS length).

    Raises:
        EmbeddingError: If all retries fail.
    """
    if not texts:
        return []

    client = _get_client()
    model = model or _get_model()

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            result = client.embed(
                texts=texts,
                model=model,
                input_type=input_type,
                output_dimension=_get_dimensions(),
            )
            logger.info(
                "Embedded %d texts (%d tokens used)",
                len(texts),
                result.total_tokens,
            )
            return result.embeddings

        except Exception as e:
            last_error = e
            logger.warning(
                "Embedding failed (attempt %d/%d): %s: %s",
                attempt, max_retries, type(e).__name__, str(e)[:200],
            )
            if attempt < max_retries:
                wait = 2 ** attempt
                time.sleep(wait)

    raise EmbeddingError(
        f"Embedding failed after {max_retries} attempts: {last_error}"
    )


def embed_query(text: str, model: str | None = None) -> list[float]:
    """Embed a single search query. Uses input_type='query' for asymmetric search."""
    vectors = embed_texts([text], input_type="query", model=model)
    return vectors[0]


def embed_document(text: str, model: str | None = None) -> list[float]:
    """Embed a single document for indexing."""
    vectors = embed_texts([text], input_type="document", model=model)
    return vectors[0]


def embed_batch(
    texts: list[str],
    input_type: str = "document",
    batch_size: int = 64,
    model: str | None = None,
) -> list[list[float]]:
    """Embed a large list of texts in batches.

    Voyage API accepts up to 128 texts per call, but we default to 64
    to stay well under rate limits and token caps.
    """
    all_embeddings: list[list[float]] = []
    total = len(texts)

    for i in range(0, total, batch_size):
        batch = texts[i : i + batch_size]
        logger.info("Embedding batch %d-%d / %d", i + 1, i + len(batch), total)
        vectors = embed_texts(batch, input_type=input_type, model=model)
        all_embeddings.extend(vectors)

        # Small delay between batches to respect rate limits
        if i + batch_size < total:
            time.sleep(0.5)

    return all_embeddings


def get_model_info() -> dict[str, Any]:
    """Return current embedding model configuration."""
    return {
        "provider": "voyage",
        "model": _get_model(),
        "dimensions": _get_dimensions(),
        "max_context_tokens": 32000,
    }
