"""Test Tier A regex extraction against 5 real criminal judgment samples."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extractors.criminal.tier_a import extract_tier_a

SAMPLES_PATH = Path(__file__).parent.parent / "data" / "evaluation" / "criminal_samples.json"

# Expected values for each sample (manually verified from schema audit)
EXPECTED = {
    "CRL.A.1-K_2018": {
        "court_level": "supreme_court",
        "case_type": "suo_motu",  # Shahzeb Khan case — Suo Motu with criminal appeals
        "has_judges": True,
        "has_ppc_sections": True,
        "has_precedents": True,
    },
    "Crl.A.103_2010": {
        "court_level": "supreme_court",
        "case_type": "appeal",
        "has_judges": True,
        "has_ppc_sections": True,
        "has_precedents": True,
    },
    "Crl.M.A.130-K_2019": {
        "court_level": "supreme_court",
        "has_judges": True,
    },
    "CRL.M.A.486_2010": {
        "court_level": "supreme_court",
        "has_judges": True,
    },
    "Crl.O.P.154_2017": {
        "court_level": "supreme_court",
        "case_type": "contempt",
        "has_judges": True,
    },
}


def run_tests():
    with open(SAMPLES_PATH) as f:
        samples = json.load(f)

    print(f"Testing Tier A extraction on {len(samples)} samples\n")
    print("=" * 80)

    total_fields = 0
    total_filled = 0

    for sample in samples:
        case_id = sample["case_id"]
        text = sample["text"]

        result = extract_tier_a(text)
        payload = result.model_dump(exclude_none=True)

        # Count filled fields
        filled = len(payload)
        all_fields = len(result.model_fields)
        total_fields += all_fields
        total_filled += filled
        fill_rate = filled / all_fields * 100

        print(f"\n{'─' * 80}")
        print(f"Case: {case_id} ({len(text):,} chars)")
        print(f"Fill rate: {filled}/{all_fields} ({fill_rate:.1f}%)")
        print(f"{'─' * 80}")

        # Print extracted values (Tier A = pattern extraction only)
        print(f"  case_number:    {result.case_number}")
        print(f"  case_title:     {result.case_title}")
        print(f"  case_type:      {result.case_type}")
        print(f"  court_name:     {result.court_name}")
        print(f"  court_level:    {result.court_level}")
        print(f"  judge_names:    {result.judge_names}")
        print(f"  date_judgment:  {result.date_judgment}")
        print(f"  ppc_sections:   {result.ppc_sections}")
        print(f"  accused_name:   {result.accused_name}")
        print(f"  victim_name:    {result.victim_name}")
        print(f"  fir_number:     {result.fir_number}")
        print(f"  precedents:     {len(result.precedents_cited)} citations")
        print(f"  statutes:       {len(result.statutes_discussed)} statutes")

        # Validate against expected
        expected = EXPECTED.get(case_id, {})
        failures = []

        if "court_level" in expected and result.court_level:
            if result.court_level.value != expected["court_level"]:
                failures.append(f"court_level: got {result.court_level.value}, expected {expected['court_level']}")

        if "case_type" in expected and result.case_type:
            if result.case_type.value != expected["case_type"]:
                failures.append(f"case_type: got {result.case_type.value}, expected {expected['case_type']}")

        if expected.get("has_judges") and not result.judge_names:
            failures.append("judge_names: expected non-empty, got []")

        if expected.get("has_ppc_sections") and not result.ppc_sections:
            failures.append("ppc_sections: expected non-empty, got []")

        if expected.get("has_precedents") and not result.precedents_cited:
            failures.append("precedents_cited: expected non-empty, got []")

        if failures:
            print(f"\n  FAILURES:")
            for f in failures:
                print(f"    ✗ {f}")
        else:
            print(f"\n  ✓ All checks passed")

    print(f"\n{'=' * 80}")
    print(f"OVERALL: {total_filled}/{total_fields} fields filled ({total_filled/total_fields*100:.1f}%)")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    run_tests()
