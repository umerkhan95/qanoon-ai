"""Pydantic models for Criminal Case Schema v2.1 (three-tier extraction)."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────────

class CaseType(str, Enum):
    TRIAL = "trial"
    APPEAL = "appeal"
    REVISION = "revision"
    REFERENCE = "reference"
    SUO_MOTU = "suo_motu"
    PETITION = "petition"
    CONTEMPT = "contempt"
    IMPLEMENTATION = "implementation"


class JudgmentType(str, Enum):
    CONVICTION = "conviction"
    ACQUITTAL = "acquittal"
    PARTIAL_CONVICTION = "partial_conviction"
    DISMISSAL = "dismissal"
    REMAND = "remand"
    SENTENCE_MODIFIED = "sentence_modified"
    MONITORING_ORDER = "monitoring_order"


class CourtLevel(str, Enum):
    TRIAL_COURT = "trial_court"
    HIGH_COURT = "high_court"
    SUPREME_COURT = "supreme_court"
    SPECIAL_COURT = "special_court"
    FEDERAL_SHARIAT = "federal_shariat"
    ANTI_TERRORISM_COURT = "anti_terrorism_court"


class Province(str, Enum):
    PUNJAB = "punjab"
    SINDH = "sindh"
    KPK = "kpk"
    BALOCHISTAN = "balochistan"
    ISLAMABAD = "islamabad"
    FEDERAL = "federal"


class OffenseCategory(str, Enum):
    PERSON = "person"
    PROPERTY = "property"
    STATE = "state"
    RELIGION = "religion"
    PUBLIC_HEALTH = "public_health"


class SeverityLevel(str, Enum):
    CAPITAL = "capital"
    LIFE = "life"
    LONG_TERM_7PLUS = "long_term_7plus"
    MEDIUM_3TO7 = "medium_3to7"
    SHORT_UNDER3 = "short_under3"


class SpecialLaw(str, Enum):
    ANTI_TERRORISM = "anti_terrorism"
    CNSA = "cnsa"
    HUDOOD = "hudood"
    JUVENILE = "juvenile"
    CONTEMPT = "contempt"
    NAB = "nab"
    CYBER = "cyber"
    NONE = "none"


class WeaponType(str, Enum):
    FIREARM = "firearm"
    KNIFE = "knife"
    BLUNT = "blunt"
    POISON = "poison"
    EXPLOSIVE = "explosive"
    NONE = "none"


class SentenceType(str, Enum):
    DEATH = "death"
    LIFE = "life"
    RIGOROUS = "rigorous"
    SIMPLE = "simple"
    FINE_ONLY = "fine_only"
    ACQUITTED = "acquitted"


class AppealOutcome(str, Enum):
    ALLOWED = "allowed"
    DISMISSED = "dismissed"
    PARTIALLY_ALLOWED = "partially_allowed"
    REMANDED = "remanded"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ── Tier A: Directly Extractable (regex/NER) ──────────────────────────────

class TierA(BaseModel):
    """~85 fields extractable via regex, pattern matching, and NER."""

    # Tier 1: Core Identification
    case_id: Optional[str] = None
    case_number: Optional[str] = None
    case_title: Optional[str] = None
    case_type: Optional[CaseType] = None
    date_judgment: Optional[date] = None
    date_incident: Optional[date] = None
    date_fir: Optional[date] = None
    date_filed: Optional[date] = None
    court_level: Optional[CourtLevel] = None
    court_name: Optional[str] = None
    judge_names: list[str] = Field(default_factory=list)
    jurisdiction_province: Optional[Province] = None

    # Tier 2: Offense & Charges (regex-extractable only)
    ppc_sections: list[int] = Field(default_factory=list)
    section_34_applied: Optional[bool] = None
    forum_category: Optional[str] = None

    # Tier 3: Parties
    accused_name: Optional[str] = None
    victim_name: Optional[str] = None
    victim_relationship: Optional[str] = None
    complainant_name: Optional[str] = None
    fir_number: Optional[str] = None
    police_station: Optional[str] = None
    prosecuting_agency: Optional[str] = None
    prosecutor_name: Optional[str] = None
    defense_counsel: Optional[str] = None

    # Tier 4: Evidence Indicators (keyword-matchable only)
    weapon_recovered: Optional[bool] = None
    dna_tested: Optional[bool] = None
    dna_matched_accused: Optional[bool] = None
    ballistics_matched: Optional[bool] = None
    post_mortem_done: Optional[bool] = None
    medical_evidence_present: Optional[bool] = None
    chain_of_custody_intact: Optional[bool] = None
    recovery_witnesses_examined: Optional[str] = None

    # Tier 5: Witness Summary (count-based and keyword-matchable)
    prosecution_witness_count: Optional[int] = None
    defense_witness_count: Optional[int] = None
    eyewitness_count: Optional[int] = None
    hostile_witness_declared: Optional[bool] = None
    dying_declaration_exists: Optional[bool] = None

    # Tier 6: Procedural Issues (keyword-matchable)
    fir_delay_hours: Optional[int] = None
    police_malpractice_alleged: Optional[bool] = None
    torture_allegations: Optional[bool] = None
    section_161_recorded: Optional[bool] = None
    section_164_recorded: Optional[bool] = None
    search_warrant_obtained: Optional[bool] = None
    alibi_raised: Optional[bool] = None

    # Tier 7: Sentencing & Outcome (pattern-extractable)
    sentence_total_months: Optional[int] = None
    fine_amount_pkr: Optional[int] = None
    sentence_modified_to: Optional[str] = None
    diyat_compromise: Optional[bool] = None
    section_382b_benefit: Optional[bool] = None

    # Tier 8: Appeal & Case Linkage (pattern-extractable)
    lower_court_case_number: Optional[str] = None
    lower_court_name: Optional[str] = None
    lower_court_judgment_date: Optional[date] = None
    precedents_cited: list[str] = Field(default_factory=list)
    statutes_discussed: list[str] = Field(default_factory=list)
    constitutional_articles: list[str] = Field(default_factory=list)
    parallel_citations: list[str] = Field(default_factory=list)
    source_url: Optional[str] = None
    reporting_status: Optional[str] = None


# ── Tier B: LLM-Reasoned Classifications ──────────────────────────────────

class TierB(BaseModel):
    """~80 fields requiring LLM to read context and classify."""

    # Case Outcome (requires understanding operative order)
    judgment_type: Optional[JudgmentType] = None
    sentence_type: Optional[SentenceType] = None
    appeal_outcome: Optional[AppealOutcome] = None

    # Offense Classification (requires legal reasoning)
    offense_category: Optional[OffenseCategory] = None
    severity_level: Optional[SeverityLevel] = None
    special_law: Optional[SpecialLaw] = None
    motive_category: Optional[str] = None
    murder_category: Optional[str] = None
    premeditation_indicators: list[str] = Field(default_factory=list)
    provocation_claimed: Optional[bool] = None
    abetment_type: Optional[str] = None
    cnsa_quantity_classification: Optional[str] = None
    recovery_circumstances: Optional[str] = None

    # Evidence Classification (requires reasoning about what evidence means)
    weapon_type: Optional[WeaponType] = None
    forensic_evidence_types: list[str] = Field(default_factory=list)
    documentary_evidence_types: list[str] = Field(default_factory=list)
    evidence_classification: Optional[str] = None
    expert_witness_present: Optional[bool] = None
    witness_impeached: Optional[bool] = None
    accomplice_witness: Optional[bool] = None
    accomplices_count: Optional[int] = None
    investigation_quality: Optional[str] = None

    # Sentencing Assessment (requires understanding court's reasoning)
    aggravating_factors: list[str] = Field(default_factory=list)
    mitigating_factors: list[str] = Field(default_factory=list)
    benefit_of_doubt_applied: Optional[bool] = None

    # Parties & Credibility
    accused_age_at_offense: Optional[int] = None
    criminal_history_count: Optional[int] = None
    complainant_relation_to_victim: Optional[str] = None
    complainant_motive_bias: list[str] = Field(default_factory=list)
    witness_interest_in_case: Optional[str] = None
    witness_relationship_to_parties: Optional[str] = None
    witness_impeachment_ground: list[str] = Field(default_factory=list)
    accomplice_testimony_corroboration: Optional[bool] = None
    conflicting_expert_opinions: Optional[bool] = None

    # Evidence Assessment
    motive_strength: Optional[str] = None
    motive_proven: Optional[bool] = None
    alibi_evidence_strength: Optional[str] = None
    presence_at_crime_scene: Optional[str] = None
    last_seen_together_evidence: Optional[bool] = None
    consciousness_of_guilt_evidence: list[str] = Field(default_factory=list)
    recovery_from_possession: Optional[bool] = None
    pm_report_quality: Optional[str] = None
    injury_count: Optional[int] = None
    injury_severity: Optional[str] = None
    weapon_forensic_tested: Optional[bool] = None
    hearsay_exception_applied: Optional[str] = None
    evidence_illegally_obtained: Optional[bool] = None
    similar_fact_evidence: Optional[bool] = None
    expert_opinion_overruled: Optional[bool] = None
    accused_prior_criminal_convictions: Optional[bool] = None

    # Procedural Assessment
    fir_discrepancies_with_testimony: list[str] = Field(default_factory=list)
    investigation_defect_description: list[str] = Field(default_factory=list)
    section_164_voluntariness_challenged: Optional[bool] = None
    section_164_officer_present: Optional[str] = None
    police_brutality_fir: Optional[bool] = None
    fir_based_on_suspicion_only: Optional[bool] = None
    defense_adequate: Optional[str] = None
    charges_framed_properly: Optional[bool] = None
    cross_examination_quality_assessment: Optional[str] = None
    eyewitness_visibility_conditions: Optional[str] = None
    eyewitness_familiarity_with_accused: Optional[str] = None
    eyewitness_identification_procedure_defects: list[str] = Field(default_factory=list)

    # Sentencing Assessment
    prosecution_strength_rating: Optional[str] = None
    conviction_certainty: Optional[str] = None
    conviction_strength: Optional[str] = None
    brutality_level: Optional[str] = None
    victim_vulnerability: Optional[str] = None
    provocation_evidence_weight: Optional[str] = None
    mental_illness: Optional[bool] = None
    intoxication_at_time: Optional[bool] = None
    cooperation_with_prosecution: Optional[bool] = None
    remorse_shown: Optional[bool] = None
    first_offense: Optional[bool] = None

    # Strategy & Patterns
    defense_strategy_primary: Optional[str] = None
    prosecution_strategy_primary: Optional[str] = None
    self_defense_claimed: Optional[bool] = None
    insanity_plea: Optional[bool] = None
    confession_voluntary: Optional[bool] = None
    confession_corroborated: Optional[bool] = None
    confessional_statement: Optional[bool] = None
    honor_crime_defense: Optional[bool] = None
    honor_crime_motive: Optional[str] = None
    sexual_offense_type: Optional[str] = None
    victim_delay_reporting: Optional[int] = None
    sectarian_violence_case: Optional[bool] = None
    rape_murder_combined: Optional[bool] = None
    grounds_for_appeal_list: list[str] = Field(default_factory=list)
    defect_fatal_to_conviction: Optional[bool] = None
    defects_cumulatively_fatal: Optional[bool] = None
    eyewitness_sole_evidence: Optional[bool] = None
    reasonable_doubt_not_applied_ground: Optional[bool] = None
    judgment_reasoning_quality: Optional[str] = None


# ── Tier C: Reasoning Points (vector text, not payload) ───────────────────

class TierC(BaseModel):
    """~35 fields stored as separate vectors, not filterable payload."""

    cause_of_death_description: Optional[str] = None
    injury_pattern_analysis: Optional[str] = None
    dying_declaration_content: Optional[str] = None
    accused_342_statement: Optional[str] = None
    provocation_evidence: Optional[str] = None
    motive_evidence: Optional[str] = None
    recovery_explanation: Optional[str] = None
    knowledge_only_culprit_would_have: Optional[str] = None
    sentence_justification_leniency: Optional[str] = None
    fir_discrepancy_details: Optional[str] = None
    investigation_defect_details: Optional[str] = None
    expert_findings_key: Optional[str] = None
    accomplices_details: Optional[str] = None
    witness_admission_during_cross: Optional[str] = None
    points_for_determination: Optional[str] = None
    ratio_decidendi: Optional[str] = None
    operative_order_text: Optional[str] = None


# ── Combined Result ────────────────────────────────────────────────────────

class CriminalExtractionResult(BaseModel):
    """Complete extraction result from all tiers + reasoning decomposition."""

    tier_a: TierA = Field(default_factory=TierA)
    tier_b: TierB = Field(default_factory=TierB)
    tier_c: TierC = Field(default_factory=TierC)
    extraction_metadata: dict = Field(default_factory=dict)
    reasoning_points: list = Field(default_factory=list)

    def to_qdrant_payload(self) -> dict:
        """Merge Tier A + B into a flat dict for Qdrant payload (exclude None).

        Uses mode="json" so Pydantic auto-serializes enums to values,
        dates to ISO strings, etc. — no manual isinstance checks needed.
        """
        payload = self.tier_a.model_dump(mode="json", exclude_none=True)
        payload.update(self.tier_b.model_dump(mode="json", exclude_none=True))
        return payload

    def to_vector_texts(self) -> dict[str, str]:
        """Return Tier C fields as {field_name: text} for separate embedding."""
        return {k: v for k, v in self.tier_c.model_dump(exclude_none=True).items()}

    def field_coverage(self) -> dict[str, float]:
        """Return fill rate for each tier."""
        def _rate(model: BaseModel) -> float:
            d = model.model_dump()
            filled = sum(1 for v in d.values() if v is not None and v != [] and v != "")
            return round(filled / len(d) * 100, 1) if d else 0.0
        return {
            "tier_a_pct": _rate(self.tier_a),
            "tier_b_pct": _rate(self.tier_b),
            "tier_c_pct": _rate(self.tier_c),
        }
