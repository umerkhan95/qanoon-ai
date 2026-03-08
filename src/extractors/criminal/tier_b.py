"""Tier B: LLM-reasoned classification fields (~65 fields).

The LLM reads the judgment context and classifies fields like
prosecution_strength_rating, defense_strategy_primary, motive_proven, etc.
These are NOT literal text extraction — the LLM must reason about the content.
"""

from __future__ import annotations

from typing import Any

from ..common.json_utils import flatten_nested_json
from ..common.llm_client import call_llm_json
from .schema import TierB

SYSTEM_PROMPT = """You are a Pakistani criminal law expert. You will be given the full text of a criminal judgment from a Pakistani court.

Your task: Read the judgment carefully and classify each field below based on what the judgment text implies or states. These are NOT direct quotes — you must REASON about the content.

Rules:
1. Only fill fields where the judgment provides enough context to make a reasonable classification
2. Use null for fields where the judgment provides no relevant information
3. For keyword fields, use ONLY the allowed values listed
4. For boolean fields, use true/false only when the judgment clearly supports it
5. For keyword[] fields, include ALL applicable values
6. Be conservative — when in doubt, use null rather than guess
7. Read the OPERATIVE ORDER (usually the last 1-2 paragraphs) to determine judgment_type, sentence_type, and appeal_outcome
8. For aggravating/mitigating factors, extract what THE COURT actually found — not what the prosecution argued or defense claimed

Return a JSON object with these fields:

## Case Outcome (from operative order — what the court actually decided)
- judgment_type: "conviction"|"acquittal"|"partial_conviction"|"dismissal"|"remand"|"sentence_modified"|"monitoring_order"
- sentence_type: "death"|"life"|"rigorous"|"simple"|"fine_only"|"acquitted"
- appeal_outcome: "allowed"|"dismissed"|"partially_allowed"|"remanded"|null

## Offense Classification (requires legal reasoning, not keyword matching)
- offense_category: "person"|"property"|"state"|"religion"|"public_health"
- severity_level: "capital"|"life"|"long_term_7plus"|"medium_3to7"|"short_under3"
- special_law: "anti_terrorism"|"cnsa"|"hudood"|"juvenile"|"contempt"|"nab"|"cyber"|"none"|null (only if the case was TRIED under the special law, not merely mentioned)
- motive_category: keyword describing the actual motive (e.g. "property_dispute","personal_enmity","honor","political","sectarian","financial","crop_dispute") or null
- murder_category: "qatal_i_amd"|"khata"|"azhar" (PPC classification)
- premeditation_indicators: [] from ["prior_enmity","weapon_procurement","planning_evidence"]
- provocation_claimed: bool
- abetment_type: "instigator"|"conspirator"|"aid_provider"|null
- cnsa_quantity_classification: "personal"|"commercial"|"trafficking"|null
- recovery_circumstances: "lawful_warrant"|"warrantless"|"consent"|"contested"|null

## Parties & Credibility
- accused_age_at_offense: integer or null
- criminal_history_count: integer or null
- complainant_relation_to_victim: keyword (e.g. "father","brother","wife")
- complainant_motive_bias: [] from ["family_enmity","land_dispute","revenge"]
- witness_interest_in_case: "family"|"financial"|"neutral"
- witness_relationship_to_parties: keyword
- witness_impeachment_ground: [] from ["prior_inconsistent","interest","bias","enmity"]
- accomplice_testimony_corroboration: bool
- conflicting_expert_opinions: bool

## Evidence & Witness Classification (requires reasoning about what the evidence means)
- weapon_type: "firearm"|"knife"|"blunt"|"poison"|"explosive"|"none"|null (what weapon was USED in the crime)
- forensic_evidence_types: [] from ["dna","fingerprint","ballistics","toxicology","trace"] (only if forensic tests were actually conducted)
- documentary_evidence_types: [] from ["fir","pm_report","medical","bank","call_records","recovery_memo"]
- evidence_classification: "direct"|"mostly_direct"|"wholly_circumstantial"|"mostly_circumstantial"|null
- expert_witness_present: bool (doctors performing post-mortem, forensic experts, etc. who testified ARE expert witnesses)
- witness_impeached: bool (was any witness impeached or discredited during trial)
- accomplice_witness: bool (did any accomplice testify as a witness)
- accomplices_count: integer (number of co-accused persons) or null
- investigation_quality: "thorough"|"adequate"|"defective"|null

## Sentencing Factors (what THE COURT actually found, not prosecution/defense arguments)
- aggravating_factors: [] from ["premeditation","brutality","vulnerable_victim","public_crime","organized_crime","multiple_victims","abuse_of_trust"] — ONLY include factors the court FOUND to exist
- mitigating_factors: [] from ["first_offense","young_age","mental_illness","provocation","cooperation","remorse","unproven_motive","good_character"] — ONLY include factors the court FOUND to exist
- benefit_of_doubt_applied: bool

## Evidence Assessment
- motive_strength: "strong"|"weak"|"none"
- motive_proven: bool
- alibi_evidence_strength: "strong"|"weak"|"none"
- presence_at_crime_scene: "confirmed"|"likely"|"unproven"
- last_seen_together_evidence: bool
- consciousness_of_guilt_evidence: [] from ["fled","destroyed_evidence","bribed_witness"]
- recovery_from_possession: bool
- pm_report_quality: "detailed"|"standard"|"minimal"
- injury_count: integer or null
- injury_severity: "fatal"|"grievous"|"simple"
- weapon_forensic_tested: bool
- hearsay_exception_applied: "dying_declaration"|"res_gestae"|"admission"|null
- evidence_illegally_obtained: bool
- similar_fact_evidence: bool
- expert_opinion_overruled: bool
- accused_prior_criminal_convictions: bool

## Procedural Assessment
- fir_discrepancies_with_testimony: [] from ["location_changed","weapon_different","accused_count_changed"]
- investigation_defect_description: [] from ["witness_not_examined","scene_not_visited","evidence_not_collected"]
- section_164_voluntariness_challenged: bool
- section_164_officer_present: "police_absent"|"police_present_violation"|null
- police_brutality_fir: bool
- fir_based_on_suspicion_only: bool
- defense_adequate: "thorough"|"adequate"|"inadequate"
- charges_framed_properly: bool
- cross_examination_quality_assessment: "thorough"|"adequate"|"superficial"
- eyewitness_visibility_conditions: "daylight"|"twilight"|"darkness"
- eyewitness_familiarity_with_accused: "familiar"|"stranger"
- eyewitness_identification_procedure_defects: [] (free text keywords)

## Sentencing Assessment
- prosecution_strength_rating: "weak"|"moderate"|"strong"|"very_strong"
- conviction_certainty: "beyond_reasonable_doubt"|"benefit_of_doubt"
- conviction_strength: "unassailable"|"strong"|"weak"|"overturned"
- brutality_level: "extreme"|"moderate"|"minimal"
- victim_vulnerability: "child"|"elderly"|"disabled"|"none"
- provocation_evidence_weight: "grave"|"minor"|"none"
- mental_illness: bool
- intoxication_at_time: bool
- cooperation_with_prosecution: bool
- remorse_shown: bool
- first_offense: bool

## Strategy & Patterns
- defense_strategy_primary: "alibi"|"mistaken_identity"|"self_defense"|"insanity"|"procedural_defect"|"reasonable_doubt"|"false_implication"
- prosecution_strategy_primary: "eyewitness"|"circumstantial_chain"|"forensic"|"confession"|"motive_opportunity"
- self_defense_claimed: bool
- insanity_plea: bool
- confession_voluntary: bool
- confession_corroborated: bool
- confessional_statement: bool
- honor_crime_defense: bool
- honor_crime_motive: keyword or null
- sexual_offense_type: keyword or null
- victim_delay_reporting: integer (days) or null
- sectarian_violence_case: bool
- rape_murder_combined: bool
- grounds_for_appeal_list: [] (free text keywords like "insufficient_evidence","procedural_violation")
- defect_fatal_to_conviction: bool
- defects_cumulatively_fatal: bool
- eyewitness_sole_evidence: bool
- reasonable_doubt_not_applied_ground: bool
- judgment_reasoning_quality: "thorough"|"adequate"|"superficial"|"contradictory"

Return ONLY valid JSON. Use null for unknown fields. Do not include explanations."""


def extract_tier_b(text: str) -> TierB:
    """Extract Tier B fields via LLM reasoning."""
    # Truncate very long judgments to fit context window
    # Keep first 4000 + last 4000 chars for most signal
    if len(text) > 25000:
        truncated = text[:12000] + "\n\n[...MIDDLE SECTION OMITTED...]\n\n" + text[-12000:]
    else:
        truncated = text

    raw = call_llm_json(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=f"Analyze this Pakistani criminal judgment and classify all fields:\n\n{truncated}",
    )

    return _parse_tier_b(raw)


def _parse_tier_b(raw: dict[str, Any]) -> TierB:
    """Parse raw LLM JSON into TierB model, handling type mismatches gracefully."""
    raw = flatten_nested_json(raw)
    cleaned = {}
    for field_name, field_info in TierB.model_fields.items():
        if field_name not in raw:
            continue
        val = raw[field_name]
        if val is None:
            continue
        # LLM sometimes returns literal "null"/"None" strings instead of JSON null
        if isinstance(val, str) and val.strip().lower() in ("null", "none", "n/a", ""):
            continue

        annotation = field_info.annotation
        anno_str = str(annotation)

        if annotation == list[str] or "list[str]" in anno_str:
            if isinstance(val, list):
                cleaned[field_name] = [
                    str(v) for v in val
                    if v is not None and str(v).strip().lower() not in ("null", "none", "n/a", "")
                ]
            elif isinstance(val, str):
                cleaned[field_name] = [val]
        elif annotation in (bool, "bool") or "bool" in str(annotation):
            if isinstance(val, bool):
                cleaned[field_name] = val
            elif isinstance(val, str):
                cleaned[field_name] = val.lower() in ("true", "yes", "1")
        elif annotation in (int, "int") or "int" in str(annotation):
            try:
                cleaned[field_name] = int(val)
            except (ValueError, TypeError):
                pass
        else:
            cleaned[field_name] = str(val) if val else None

    return TierB(**cleaned)
