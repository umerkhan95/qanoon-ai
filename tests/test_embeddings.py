"""Test Voyage AI embedding service against real Pakistani judgment samples."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.qdrant.embeddings import (
    embed_batch,
    embed_document,
    embed_query,
    get_model_info,
)

SAMPLES_PATH = Path(__file__).parent.parent / "data" / "evaluation" / "criminal_samples.json"


def test_model_info():
    info = get_model_info()
    print(f"Model config: {info}")
    assert info["provider"] == "voyage"
    assert info["dimensions"] == 1024
    print("  model_info OK\n")


def test_single_query():
    print("Testing single query embedding...")
    start = time.time()
    vec = embed_query("bail application for murder under section 302 PPC")
    elapsed = (time.time() - start) * 1000

    print(f"  Dimensions: {len(vec)}")
    print(f"  First 5 values: {vec[:5]}")
    print(f"  Latency: {elapsed:.0f}ms")
    assert len(vec) == 1024
    assert all(isinstance(v, float) for v in vec)
    print("  single_query OK\n")


def test_single_document():
    print("Testing single document embedding...")
    sample_text = (
        "IN THE SUPREME COURT OF PAKISTAN. Criminal Appeal No. 103 of 2010. "
        "The appellant was convicted under section 302 PPC by the trial court. "
        "The evidence consisted of eyewitness testimony and medical evidence."
    )
    start = time.time()
    vec = embed_document(sample_text)
    elapsed = (time.time() - start) * 1000

    print(f"  Dimensions: {len(vec)}")
    print(f"  Latency: {elapsed:.0f}ms")
    assert len(vec) == 1024
    print("  single_document OK\n")


def test_real_judgment_samples():
    if not SAMPLES_PATH.exists():
        print(f"  SKIP: {SAMPLES_PATH} not found\n")
        return

    with open(SAMPLES_PATH) as f:
        samples = json.load(f)

    print(f"Testing {len(samples)} real judgment samples...")
    texts = [s["text"] for s in samples]
    char_counts = [len(t) for t in texts]

    print(f"  Char lengths: {char_counts}")
    print(f"  Total chars: {sum(char_counts):,}")

    # Free tier: 3 RPM, 10K TPM — embed one at a time with delay
    vectors = []
    start = time.time()
    for idx, text in enumerate(texts):
        print(f"  Embedding sample {idx + 1}/{len(texts)} ({len(text):,} chars)...")
        vec = embed_document(text)
        vectors.append(vec)
        if idx < len(texts) - 1:
            time.sleep(25)  # stay under 3 RPM

    elapsed = (time.time() - start) * 1000

    print(f"  Got {len(vectors)} vectors")
    print(f"  All 1024-dim: {all(len(v) == 1024 for v in vectors)}")
    print(f"  Total latency: {elapsed:.0f}ms")

    assert len(vectors) == len(samples)
    assert all(len(v) == 1024 for v in vectors)
    print("  real_judgment_samples OK\n")


def test_semantic_similarity():
    """Verify that semantically similar queries produce closer vectors."""
    import math

    def cosine_sim(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

    print("Testing semantic similarity...")
    queries = [
        "murder conviction under section 302 PPC",          # q0
        "conviction for killing under Pakistan Penal Code",  # q1 — similar to q0
        "bail application in cheque bounce case",            # q2 — very different
    ]

    vectors = embed_batch(queries, input_type="query", batch_size=3)

    sim_01 = cosine_sim(vectors[0], vectors[1])  # similar
    sim_02 = cosine_sim(vectors[0], vectors[2])  # different

    print(f"  'murder 302 PPC' vs 'killing under PPC': {sim_01:.4f}")
    print(f"  'murder 302 PPC' vs 'cheque bounce bail': {sim_02:.4f}")
    print(f"  Delta: {sim_01 - sim_02:.4f} (higher = better semantic discrimination)")

    assert sim_01 > sim_02, (
        f"Similar queries should have higher cosine sim ({sim_01:.4f}) "
        f"than different queries ({sim_02:.4f})"
    )
    print("  semantic_similarity OK\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Voyage AI Embedding Service — Integration Test")
    print("=" * 60 + "\n")

    test_model_info()
    test_single_query()
    test_single_document()
    test_semantic_similarity()
    test_real_judgment_samples()

    print("=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
