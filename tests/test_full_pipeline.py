"""Full pipeline test — Tier A + B + C on one real criminal judgment."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from src.extractors.criminal.pipeline import extract_criminal_judgment

SAMPLES_PATH = Path(__file__).parent.parent / "data" / "evaluation" / "criminal_samples.json"


def main():
    with open(SAMPLES_PATH) as f:
        samples = json.load(f)

    # Use Crl.A.103_2010 — Amjad Shah murder appeal, richest criminal content
    sample = next(s for s in samples if s["case_id"] == "Crl.A.103_2010")
    text = sample["text"]

    print(f"Running full pipeline on: {sample['case_id']} ({len(text):,} chars)")
    print("=" * 80)

    result = extract_criminal_judgment(text, skip_llm=False)

    # ── Tier A Results ──
    print("\n── TIER A (regex) ──")
    a = result.tier_a.model_dump(exclude_none=True)
    for k, v in sorted(a.items()):
        print(f"  {k}: {v}")

    # ── Tier B Results ──
    print("\n── TIER B (LLM classification) ──")
    b = result.tier_b.model_dump(exclude_none=True)
    if b:
        for k, v in sorted(b.items()):
            print(f"  {k}: {v}")
    else:
        print("  (empty — LLM may have failed)")

    # ── Tier C Results ──
    print("\n── TIER C (reasoning points) ──")
    c = result.tier_c.model_dump(exclude_none=True)
    if c:
        for k, v in sorted(c.items()):
            preview = v[:150] + "..." if len(v) > 150 else v
            print(f"  {k}: {preview}")
    else:
        print("  (empty — LLM may have failed)")

    # ── Coverage ──
    print("\n── COVERAGE ──")
    coverage = result.field_coverage()
    for k, v in coverage.items():
        print(f"  {k}: {v}%")

    # ── Metadata ──
    print("\n── EXTRACTION METADATA ──")
    for k, v in result.extraction_metadata.items():
        print(f"  {k}: {v}")

    # ── Qdrant payload preview ──
    payload = result.to_qdrant_payload()
    vectors = result.to_vector_texts()
    print(f"\n── QDRANT OUTPUT ──")
    print(f"  Payload fields: {len(payload)}")
    print(f"  Vector text fields: {len(vectors)}")

    # Save full output
    out_path = Path(__file__).parent.parent / "data" / "evaluation" / "pipeline_output_sample.json"
    with open(out_path, "w") as f:
        json.dump({
            "case_id": sample["case_id"],
            "payload": payload,
            "vector_texts": vectors,
            "metadata": result.extraction_metadata,
        }, f, indent=2, default=str)
    print(f"\n  Full output saved to: {out_path}")


if __name__ == "__main__":
    main()
