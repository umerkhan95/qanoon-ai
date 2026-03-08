"""Chunk Pakistani judgments for Qdrant ingestion.

Single responsibility: judgment text + metadata → list of enriched chunks.

Strategy (from ticket #18 research):
- Most judgments (8K-36K chars, ~1K-5K tokens) fit in Voyage 3.5's 32K window
  → embedded as a single chunk (no splitting needed).
- Long judgments (>MAX_SINGLE_EMBED_CHARS) → split at numbered paragraph
  boundaries within each section, with overlap.
- Every chunk gets a SAC (Summary-Augmented Chunking) prefix prepended
  to reduce Document-Level Retrieval Mismatch by ~50%.
- Every chunk carries metadata (court, citation, date, case type) for
  filtered search in Qdrant.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from pydantic import BaseModel

from .section_parser import JudgmentSection, SectionType, parse_judgment

logger = logging.getLogger(__name__)

# Judgments under this char count are embedded as a single vector.
# ~25K tokens ≈ 100K chars. Voyage 3.5 handles 32K tokens.
MAX_SINGLE_EMBED_CHARS = 100_000

# Target chunk size in characters (~512 tokens ≈ 2048 chars)
TARGET_CHUNK_CHARS = 2048

# Overlap between consecutive chunks
CHUNK_OVERLAP_CHARS = 256

# Minimum chunk size — don't create tiny chunks
MIN_CHUNK_CHARS = 200

# Numbered paragraph boundary for splitting
_PARA_BOUNDARY = re.compile(r"\n\s*(?=\d{1,3}\.\s)")


class Chunk(BaseModel):
    """A single chunk ready for embedding and Qdrant ingestion."""

    text: str
    chunk_index: int
    total_chunks: int
    section_type: SectionType
    char_start: int
    char_end: int
    metadata: dict = {}


def chunk_judgment(
    text: str,
    metadata: Optional[dict] = None,
    summary: Optional[str] = None,
) -> list[Chunk]:
    """Chunk a judgment for embedding.

    Args:
        text: Full judgment text.
        metadata: Case metadata (citation, court, date, etc.) to attach
                  to every chunk.
        summary: SAC summary to prepend to each chunk. If None, no prefix.

    Returns:
        List of Chunk objects. For short judgments, returns a single chunk.
    """
    if not text or not text.strip():
        return []

    text = text.strip()
    meta = metadata or {}

    # Short judgments → single chunk
    if len(text) <= MAX_SINGLE_EMBED_CHARS:
        chunk_text = _prepend_summary(text, summary)
        return [Chunk(
            text=chunk_text,
            chunk_index=0,
            total_chunks=1,
            section_type=SectionType.BODY,
            char_start=0,
            char_end=len(text),
            metadata=meta,
        )]

    # Long judgments → section-based splitting
    logger.info(
        "Long judgment (%d chars), splitting into sections",
        len(text),
    )
    sections = parse_judgment(text)
    raw_chunks = _split_sections(sections)

    # Assign indices and prepend summary
    total = len(raw_chunks)
    result = []
    for idx, chunk in enumerate(raw_chunks):
        chunk_text = _prepend_summary(chunk.text, summary)
        result.append(Chunk(
            text=chunk_text,
            chunk_index=idx,
            total_chunks=total,
            section_type=chunk.section_type,
            char_start=chunk.char_start,
            char_end=chunk.char_end,
            metadata=meta,
        ))

    logger.info(
        "Split into %d chunks (sections: %s)",
        len(result),
        [c.section_type.value for c in result],
    )
    return result


def _split_sections(sections: list[JudgmentSection]) -> list[Chunk]:
    """Split sections into chunks at paragraph boundaries.

    Tiny sections (< MIN_CHUNK_CHARS) are merged into the nearest
    adjacent chunk to preserve 100% of the content.
    """
    chunks: list[Chunk] = []
    # Collect tiny sections to merge with adjacent chunks
    pending_prefix = ""
    pending_prefix_start: int | None = None

    for i, section in enumerate(sections):
        text = section.text
        start = section.start_char
        end = section.end_char

        # Prepend any accumulated tiny section text
        if pending_prefix:
            text = pending_prefix + "\n\n" + text
            start = pending_prefix_start if pending_prefix_start is not None else start
            pending_prefix = ""
            pending_prefix_start = None

        if len(text) < MIN_CHUNK_CHARS:
            # Too small — accumulate for merging with next section
            pending_prefix = text
            pending_prefix_start = start
            continue

        if len(text) <= TARGET_CHUNK_CHARS:
            chunks.append(Chunk(
                text=text,
                chunk_index=0,
                total_chunks=0,
                section_type=section.section_type,
                char_start=start,
                char_end=end,
            ))
        else:
            section_chunks = _split_at_paragraphs(
                text,
                section.section_type,
                start,
            )
            chunks.extend(section_chunks)

    # If there's a trailing tiny section, append it to the last chunk
    if pending_prefix and chunks:
        last = chunks[-1]
        chunks[-1] = Chunk(
            text=last.text + "\n\n" + pending_prefix,
            chunk_index=0,
            total_chunks=0,
            section_type=last.section_type,
            char_start=last.char_start,
            char_end=pending_prefix_start + len(pending_prefix) if pending_prefix_start is not None else last.char_end,
        )
    elif pending_prefix:
        # Edge case: all sections were tiny
        chunks.append(Chunk(
            text=pending_prefix,
            chunk_index=0,
            total_chunks=0,
            section_type=SectionType.BODY,
            char_start=pending_prefix_start or 0,
            char_end=(pending_prefix_start or 0) + len(pending_prefix),
        ))

    return chunks


def _split_at_paragraphs(
    text: str,
    section_type: SectionType,
    base_offset: int,
) -> list[Chunk]:
    """Split text at numbered paragraph boundaries with overlap."""
    # Find all paragraph boundary positions
    boundaries = [0]
    for match in _PARA_BOUNDARY.finditer(text):
        boundaries.append(match.start())
    boundaries.append(len(text))

    # Build paragraphs
    paragraphs: list[tuple[int, int]] = []
    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1]
        if end - start > 0:
            paragraphs.append((start, end))

    if not paragraphs:
        return [Chunk(
            text=text,
            chunk_index=0,
            total_chunks=0,
            section_type=section_type,
            char_start=base_offset,
            char_end=base_offset + len(text),
        )]

    # Merge paragraphs into chunks of ~TARGET_CHUNK_CHARS
    chunks: list[Chunk] = []
    current_start = paragraphs[0][0]
    current_end = paragraphs[0][0]

    for para_start, para_end in paragraphs:
        para_len = para_end - para_start
        current_len = current_end - current_start

        if current_len > 0 and current_len + para_len > TARGET_CHUNK_CHARS:
            # Flush current chunk
            chunk_text = text[current_start:current_end].strip()
            if len(chunk_text) >= MIN_CHUNK_CHARS:
                chunks.append(Chunk(
                    text=chunk_text,
                    chunk_index=0,
                    total_chunks=0,
                    section_type=section_type,
                    char_start=base_offset + current_start,
                    char_end=base_offset + current_end,
                ))

            # Start new chunk with overlap
            overlap_start = _find_overlap_start(
                text, current_end, CHUNK_OVERLAP_CHARS
            )
            current_start = overlap_start
            current_end = para_end
        else:
            current_end = para_end

    # Flush remaining
    chunk_text = text[current_start:current_end].strip()
    if len(chunk_text) >= MIN_CHUNK_CHARS:
        chunks.append(Chunk(
            text=chunk_text,
            chunk_index=0,
            total_chunks=0,
            section_type=section_type,
            char_start=base_offset + current_start,
            char_end=base_offset + current_end,
        ))
    elif chunks:
        # Merge tiny remainder into last chunk
        last = chunks[-1]
        merged_text = text[
            last.char_start - base_offset : current_end
        ].strip()
        chunks[-1] = Chunk(
            text=merged_text,
            chunk_index=0,
            total_chunks=0,
            section_type=section_type,
            char_start=last.char_start,
            char_end=base_offset + current_end,
        )

    return chunks


def _find_overlap_start(text: str, end_pos: int, overlap_chars: int) -> int:
    """Find a good overlap start position (at a paragraph or sentence boundary)."""
    target = max(0, end_pos - overlap_chars)

    # Try to start at a paragraph boundary
    para_match = _PARA_BOUNDARY.search(text, pos=target)
    if para_match and para_match.start() < end_pos:
        return para_match.start()

    # Fall back to sentence boundary
    sentence_end = text.rfind(". ", target, end_pos)
    if sentence_end > target:
        return sentence_end + 2

    return target


def _prepend_summary(text: str, summary: Optional[str]) -> str:
    """Prepend SAC summary to chunk text."""
    if not summary:
        return text
    return f"[Summary: {summary.strip()}]\n\n{text}"
