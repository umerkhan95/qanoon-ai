"""Tier C: Reasoning point extraction (~35 fields stored as vectors).

These are free-text fields extracted by the LLM — verbatim quotes, narrative
summaries, and legal reasoning passages. They are NOT stored as Qdrant payload
filters but as separate vectors for semantic search.
"""

from __future__ import annotations

from ..common.json_utils import flatten_nested_json
from ..common.llm_client import call_llm_json
from .schema import TierC

SYSTEM_PROMPT = """You are a Pakistani criminal law expert. Extract the following reasoning points from the judgment text.

For each field, extract the RELEVANT TEXT PASSAGE from the judgment. These should be:
- Direct quotes where possible (especially dying declarations, accused statements)
- Concise summaries for analytical fields (cause of death, injury patterns)
- The actual court reasoning for legal analysis fields (ratio decidendi, operative order)

Rules:
1. Only fill fields where the judgment contains relevant content
2. Use null for fields with no relevant content in the judgment
3. Keep extractions concise (50-300 words each) — capture the essence, not the entire section
4. Preserve legal terminology and citations within excerpts
5. For operative_order_text, extract the EXACT order (acquitted/convicted/remanded/etc.)

Fields to extract:

- cause_of_death_description: Forensic/medical findings on how victim died
- injury_pattern_analysis: Description of injuries from PM report or medical evidence
- dying_declaration_content: Verbatim or summarized dying declaration if exists
- accused_342_statement: The accused's statement under Section 342 CrPC
- provocation_evidence: What provoked the accused (if claimed)
- motive_evidence: Evidence items proving or suggesting motive
- recovery_explanation: Accused's explanation for recovered items
- knowledge_only_culprit_would_have: "Secret knowledge" items only the perpetrator would know
- sentence_justification_leniency: Court's reasoning for lenient sentence (if applicable)
- fir_discrepancy_details: Specific contradictions between FIR and later testimony
- investigation_defect_details: Specific investigation gaps identified by court
- expert_findings_key: Key quotes from expert reports (medical, forensic, ballistic)
- accomplices_details: Co-accused names, roles, and case statuses
- witness_admission_during_cross: Specific admissions made by witnesses during cross-examination
- points_for_determination: CrPC 367 mandated legal questions the court addressed
- ratio_decidendi: The binding legal principle established by this judgment
- operative_order_text: The actual court order (exact disposal text)

Return ONLY valid JSON. Use null for fields not found in the judgment."""


def extract_tier_c(text: str) -> TierC:
    """Extract Tier C reasoning points via LLM."""
    # For Tier C we need more text context since we're extracting passages
    if len(text) > 30000:
        truncated = text[:15000] + "\n\n[...MIDDLE SECTION OMITTED...]\n\n" + text[-15000:]
    else:
        truncated = text

    raw = call_llm_json(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=f"Extract reasoning points from this Pakistani criminal judgment:\n\n{truncated}",
    )

    return _parse_tier_c(raw)


def _parse_tier_c(raw: dict) -> TierC:
    """Parse raw LLM JSON into TierC model."""
    raw = flatten_nested_json(raw)
    cleaned = {}
    for field_name in TierC.model_fields:
        val = raw.get(field_name)
        if val and isinstance(val, str) and len(val.strip()) > 5:
            cleaned[field_name] = val.strip()
    return TierC(**cleaned)
