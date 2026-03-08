"""Tests for the chunking pipeline.

Unit tests (no network, no LLM) for section parsing and chunking logic.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.chunking.section_parser import (
    JudgmentSection,
    SectionType,
    _extract_paragraph_numbers,
    _find_disposition,
    _find_judgment_marker,
    parse_judgment,
)
from src.chunking.chunker import (
    Chunk,
    MAX_SINGLE_EMBED_CHARS,
    MIN_CHUNK_CHARS,
    TARGET_CHUNK_CHARS,
    _prepend_summary,
    chunk_judgment,
)


# ── Section Parser Tests ────────────────────────────────────────────


SAMPLE_JUDGMENT = """IN THE SUPREME COURT OF PAKISTAN
(Appellate Jurisdiction)

PRESENT:
Mr. Justice Saqib Nisar, HCJ
Mr. Justice Asif Saeed Khan Khosa

Criminal Appeals No. 1-K to 3-K of 2018

JUDGMENT

Asif Saeed Khan Khosa, J.: On 01.02.2018 the captioned
appeals had been disposed of by us through a short order.

2. The facts of the case are that the accused was charged
under Section 302 PPC for the murder of the deceased.

3. The prosecution case was that on 15.01.2017 the accused
shot the deceased with a pistol.

4. We have heard the learned counsel for the parties and
have perused the record with their assistance.

5. For the reasons recorded above, the appeal is dismissed.
The conviction and sentence recorded by the courts below are
maintained. These are the reasons for our short order.

MFR - Islamabad
"""


def test_parse_judgment_finds_all_sections():
    sections = parse_judgment(SAMPLE_JUDGMENT)
    assert len(sections) >= 2  # At least header + body
    types = [s.section_type for s in sections]
    assert SectionType.HEADER in types
    assert SectionType.BODY in types


def test_parse_judgment_header_contains_court_info():
    sections = parse_judgment(SAMPLE_JUDGMENT)
    header = next(s for s in sections if s.section_type == SectionType.HEADER)
    assert "SUPREME COURT" in header.text
    assert "JUDGMENT" not in header.text


def test_parse_judgment_body_has_paragraph_numbers():
    sections = parse_judgment(SAMPLE_JUDGMENT)
    body = next(s for s in sections if s.section_type == SectionType.BODY)
    assert 2 in body.paragraph_numbers
    assert 3 in body.paragraph_numbers


def test_find_judgment_marker_standard():
    text = "Some header text\n\nJUDGMENT\n\nBody text here"
    header_end, body_start = _find_judgment_marker(text)
    assert header_end > 0
    assert body_start >= header_end


def test_find_judgment_marker_order():
    text = "Header\n\nORDER\n\nBody"
    header_end, body_start = _find_judgment_marker(text)
    assert header_end > 0


def test_find_judgment_marker_spaced():
    text = "Header\n\nJ U D G M E N T\n\nBody"
    header_end, body_start = _find_judgment_marker(text)
    assert header_end > 0


def test_find_judgment_marker_missing():
    text = "No marker in this text at all"
    header_end, body_start = _find_judgment_marker(text)
    assert header_end == 0 and body_start == 0


def test_extract_paragraph_numbers():
    text = "1. First para\n2. Second para\n10. Tenth para"
    nums = _extract_paragraph_numbers(text)
    assert nums == [1, 2, 10]


def test_extract_paragraph_numbers_no_paras():
    text = "No numbered paragraphs here."
    nums = _extract_paragraph_numbers(text)
    assert nums == []


def test_find_disposition_dismissed():
    text = "x" * 1000 + "\n5. The appeal is dismissed.\nMFR - Islamabad"
    result = _find_disposition(text, 0)
    assert result is not None
    assert result > 500


def test_find_disposition_none():
    text = "Just some text with no disposition markers at all."
    result = _find_disposition(text, 0)
    assert result is None


def test_parse_empty():
    assert parse_judgment("") == []
    assert parse_judgment("   ") == []


def test_parse_no_marker_fallback():
    text = "Just a plain text judgment with no markers.\n2. Some paragraph."
    sections = parse_judgment(text)
    assert len(sections) >= 1
    assert sections[0].section_type == SectionType.BODY


# ── Chunker Tests ───────────────────────────────────────────────────


def test_chunk_short_judgment():
    text = "Short judgment text under the limit."
    chunks = chunk_judgment(text)
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].total_chunks == 1
    assert chunks[0].text == text


def test_chunk_empty():
    assert chunk_judgment("") == []
    assert chunk_judgment("   ") == []


def test_chunk_with_summary():
    text = "Short judgment."
    chunks = chunk_judgment(text, summary="This is a test case summary.")
    assert len(chunks) == 1
    assert chunks[0].text.startswith("[Summary:")
    assert "test case summary" in chunks[0].text
    assert "Short judgment." in chunks[0].text


def test_chunk_with_metadata():
    meta = {"court": "supreme_court", "citation": "[2024] PKSC 1"}
    chunks = chunk_judgment("Some text", metadata=meta)
    assert chunks[0].metadata == meta


def test_chunk_long_judgment():
    # Create a judgment that exceeds MAX_SINGLE_EMBED_CHARS
    paras = []
    for i in range(1, 201):
        paras.append(f"\n{i}. " + "x" * 600)
    long_text = "HEADER\n\nJUDGMENT\n" + "".join(paras)

    assert len(long_text) > MAX_SINGLE_EMBED_CHARS
    chunks = chunk_judgment(long_text)
    assert len(chunks) > 1

    # All chunks should have consistent total_chunks
    for c in chunks:
        assert c.total_chunks == len(chunks)

    # No chunk should be tiny
    for c in chunks:
        assert len(c.text) >= MIN_CHUNK_CHARS


def test_prepend_summary_none():
    assert _prepend_summary("text", None) == "text"


def test_prepend_summary_empty():
    assert _prepend_summary("text", "") == "text"


def test_prepend_summary_value():
    result = _prepend_summary("body", "A summary.")
    assert result == "[Summary: A summary.]\n\nbody"


def test_chunk_pydantic_serialization():
    chunks = chunk_judgment("Test text")
    data = chunks[0].model_dump()
    assert isinstance(data, dict)
    assert data["chunk_index"] == 0
    assert data["section_type"] == "body"


# ── Run all tests ───────────────────────────────────────────────────


if __name__ == "__main__":
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print(f"  {name}: PASS")
    print("\nAll chunking tests passed!")
