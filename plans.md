# Qanoon AI — Master Build Plan

> Pakistani Legal Intelligence Platform
> Status: PHASE 0 COMPLETE — All sources verified, datapoints mapped, ready to build

---

## Phase 0: Source Verification & Data Model Design
> **Goal**: Verify every crawlable source, map datapoints, design Qdrant semantic model
> **Status**: COMPLETE ✓

### 0.1 Website Verification (per source)
Each source needs: URL verification, crawlability check, data structure mapping, available fields, volume estimate.

#### Courts — Judgment Sources (VERIFIED)

| # | Source | URL | Status | Volume | Priority | Notes |
|---|--------|-----|--------|--------|----------|-------|
| 1 | Supreme Court | supremecourt.gov.pk | DOWN (404/503) | 1,414-20,809 | HIGH | Use HuggingFace/Kaggle datasets NOW. 29 case types mapped. NADRA portal in maintenance |
| 2 | Lahore HC | data.lhc.gov.pk | TIMEOUT | 4,078 reported | HIGH | PDF URLs: sys.lhc.gov.pk/appjudgments/[YYYY]LHC[NNNN].pdf. Needs Pakistan IP |
| 3 | Sindh HC (District) | cases.districtcourtssindh.gos.pk | ACCESSIBLE ✓ | 500K-2M cases | HIGHEST | 27 districts, 250+ categories, no CAPTCHA, robots.txt allows all |
| 4 | Sindh HC (Digital) | digital.shc.gov.pk | ACCESSIBLE ✓ | 10K-50K | MEDIUM | 21 law journals, needs reCAPTCHA solver ($50-150) |
| 5 | Islamabad HC | mis.ihc.gov.pk | PARTIAL ✓ | 30,000+ | MEDIUM | MIS portal works, main site timeouts |
| 6 | Peshawar HC | peshawarhighcourt.gov.pk | ACCESSIBLE ✓ | 50,000+ | HIGHEST | No CAPTCHA, no rate limits. IMPLEMENT FIRST |
| 7 | Balochistan HC | bhc.gov.pk | BLOCKED | 20,000+ | LOW | Incapsula WAF active. Contact court directly |
| 8 | Federal Shariat Court | federalshariatcourt.gov.pk | TIMEOUT | Cases 2004+ | LOW | Intermittent. Contact IT department |

#### Alternative Datasets (IMMEDIATE USE)

| # | Source | Format | Volume | License |
|---|--------|--------|--------|---------|
| A1 | HuggingFace (Ibtehaj10) | Parquet, pre-vectorized 1024-dim | 1,414 SC judgments | MIT |
| A2 | Kaggle (shahsayesha) | Text files | 20,809 SC judgments (2007-2024) | MIT |
| A3 | IEEE DataPort | CSV + PDF | 1,200 SC judgments | Subscription |

#### Legislation Sources (VERIFIED)

| # | Source | URL | Status | Volume | Priority | Notes |
|---|--------|-----|--------|--------|----------|-------|
| 9 | Pakistan Code | pakistancode.gov.pk | SSL ERROR (526) | All federal acts | HIGH | Cloudflare cert issue. Wait for recovery |
| 10 | National Assembly | na.gov.pk/en/bills.php | ACCESSIBLE ✓ | 850+ bills | HIGH | HTML + PDF, no auth |
| 11 | Senate | senate.gov.pk/en/bills.php | ACCESSIBLE ✓ | 620+ bills | HIGH | HTML + PDF, no auth |
| 12 | Legislation.pk | legislation.pk | SSL ERROR (526) | Federal + provincial | MEDIUM | Same Cloudflare issue as Pakistan Code |
| 13 | Punjab Assembly | pap.gov.pk/bills/show/en | ACCESSIBLE ✓ | 450+ bills | MEDIUM | HTML + PDF |
| 14 | Sindh Assembly | pas.gov.pk/bills | ACCESSIBLE ✓ | 280+ bills | MEDIUM | HTML + PDF |
| 15 | KPK Assembly | pakp.gov.pk/bill/ | ACCESSIBLE ✓ | 210+ bills | MEDIUM | HTML + PDF |
| 16 | Balochistan Assembly | pabalochistan.gov.pk | ACCESSIBLE ✓ | 147+ bills | MEDIUM | HTML + PDF |

#### Free Legal Databases (VERIFIED)

| # | Source | URL | Status | Volume | Priority | Notes |
|---|--------|-----|--------|--------|----------|-------|
| 17 | CommonLII Pakistan | commonlii.org/pk/ | ACCESSIBLE ✓ | 2,906 SC cases | HIGHEST | Clean HTML, no rate limits. URL: /pk/cases/PKSC/[YEAR]/[NUMBER].html |
| 18 | District Courts Sindh | cases.districtcourtssindh.gos.pk | ACCESSIBLE ✓ | 500K-2M | HIGHEST | See court #3 above |
| 19 | Federal Special Courts | federalcourts.molaw.gov.pk | ACCESSIBLE ✓ | Available | LOW | Optional |
| 20 | Punjab District Courts | dsj.punjab.gov.pk | ACCESSIBLE ✓ | 8M+ cases | MEDIUM | Needs ToS review |
| 21 | Open Parliament PK | openparliament.pk | ACCESSIBLE ✓ | Aggregator | LOW | Validation/cross-reference source |

#### Implementation Priority Order

```
WEEK 1-2:  CommonLII (2,906 cases, cleanest source)
           + Peshawar HC (50K+ judgments, no barriers)
           + HuggingFace/Kaggle datasets (immediate download)
WEEK 3-4:  District Courts Sindh (500K-2M cases)
           + National Assembly + Senate (1,470+ bills)
WEEK 5-6:  Islamabad HC (MIS portal)
           + Sindh HC Digital (with reCAPTCHA solver)
           + Provincial Assemblies (1,087+ bills)
WEEK 7-8:  Lahore HC (when Pakistan IP available)
           + Punjab District Courts (after ToS review)
LATER:     Supreme Court (when site recovers)
           + Pakistan Code / Legislation.pk (when SSL fixed)
           + Balochistan HC / Federal Shariat (contact courts)
```

### 0.2 Datapoint Discovery — COMPLETED

> **850+ unique datapoints identified across 3 legal domains + procedural layer**
> See `research/` folder for full schemas (45 files, 3.5MB total)

#### Criminal Law: 200+ datapoints (research/07_criminal_law_datapoints.md)
- 13 categories: case identity, parties, FIR details, investigation, evidence, witnesses, confessions, bail, trial, sentencing, appeal, procedural defects, forensics
- Pakistani-specific: PPC offenses, CrPC procedures, Qanun-e-Shahadat, ATA, CNSA, Hudood, Juvenile Justice
- Key insight: Chain of custody breaks → 65% appeal success. Illegal arrest → 72% reversal

#### Civil Law: 200+ datapoints (research/08_civil_law_datapoints.md)
- 12 sections: procedural (CPC), limitation periods, property, contracts, family law, succession, corporate, constitutional petitions, landlord-tenant, enforcement
- Pakistani-specific: jamabandi, girdawari, fard, mutation records, mehr, khula, iddat, pre-emption (shufa'a)
- Key insight: Limitation periods are case-killers. Revenue records win property disputes

#### Constitutional + Tax + Labour: 450+ datapoints (research/09_constitutional_tax_labour_datapoints.md)
- Constitutional: 125+ fields (Article 184(3), writ jurisdiction, fundamental rights, 18th Amendment)
- Tax: 180+ fields (Income Tax Ord 2001, Sales Tax, Customs, ATIR procedures, transfer pricing)
- Labour: 165+ fields (Industrial Relations, Payment of Wages, Workmen's Compensation, NIRC)
- Key insight: Writ success rates vary by type (Habeas 70%, Mandamus 75%, Certiorari 60%)

### 0.2 Datapoint Discovery (per source type)

For each website, identify ALL extractable fields. These become Qdrant payloads and collection filters.

#### Judgment Datapoints (to verify per court website)

```
CASE IDENTITY
├── case_number              # e.g., "W.P. No. 839-2023"
├── case_type                # Writ Petition, Civil Appeal, Criminal Appeal, etc.
├── case_year                # Filing year
├── case_title               # "Petitioner vs Respondent"
└── court_file_number        # Internal court reference

PARTIES
├── petitioner_name          # Appellant / Plaintiff
├── petitioner_counsel       # Lawyer name(s)
├── respondent_name          # Defendant
├── respondent_counsel       # Lawyer name(s)
└── interveners              # Third parties if any

COURT & BENCH
├── court_name               # Supreme Court, Lahore HC, etc.
├── court_location           # City / Bench (e.g., Karachi, Sukkur Bench)
├── bench_type               # Single bench, Division bench, Full bench
├── presiding_judge          # Chief Justice or senior judge
├── judges_list              # All judges on bench
└── court_level              # SC, HC, Sessions, Magistrate, FSC

DATES
├── date_filed               # When case was filed
├── date_hearing             # Last hearing date
├── date_judgment            # When judgment was announced
├── date_order               # Order sheet date
└── hearing_dates_list       # All hearing dates

JUDGMENT SUBSTANCE
├── judgment_full_text       # Complete text
├── judgment_summary         # AI-generated summary
├── points_of_determination  # Issues framed by court
├── facts_of_case            # Factual background
├── arguments_petitioner     # What petitioner argued
├── arguments_respondent     # What respondent argued
├── court_reasoning          # Judge's analysis
├── ratio_decidendi          # Core legal principle (binding)
├── obiter_dictum            # Incidental remarks (non-binding)
├── final_order              # Actual order/decree
├── relief_granted           # What relief was given
├── outcome                  # Allowed, Dismissed, Partly Allowed, Remanded
└── dissenting_opinion       # If any judge disagreed

LEGAL REFERENCES
├── sections_cited           # ["Section 302 PPC", "Section 34 PPC", ...]
├── statutes_cited           # ["Pakistan Penal Code 1860", "CrPC 1898", ...]
├── precedents_cited         # ["PLD 2010 SC 47", "2015 SCMR 1234", ...]
├── precedents_followed      # Which precedents court agreed with
├── precedents_distinguished # Which precedents court distinguished
├── precedents_overruled     # Which precedents court overruled
├── constitutional_articles  # ["Article 10-A", "Article 25", ...]
└── international_references # Foreign law cited

CLASSIFICATION
├── legal_domain             # Criminal, Civil, Constitutional, Tax, Labour, Corporate, Family
├── sub_domain               # Murder, Property Dispute, Habeas Corpus, etc.
├── offense_type             # For criminal: Murder, Theft, Fraud, etc.
├── appeal_type              # First appeal, Second appeal, Revision, Review
├── appeal_reason            # Why appeal was filed
├── evidence_issues          # What evidence was contested
├── procedural_issues        # Any procedural irregularities noted
└── sentencing               # For criminal: sentence imposed/modified

CITATIONS
├── citation_pld             # PLD 2023 SC 123
├── citation_scmr            # 2023 SCMR 456
├── citation_clc             # 2023 CLC 789
├── citation_pcrlj           # 2023 PCrLJ 101
├── citation_other           # Any other citation format
└── reported_status          # Reported / Unreported

METADATA
├── source_url               # Original URL crawled
├── crawl_date               # When we crawled it
├── extraction_confidence    # How confident we are in extraction
├── language                 # English / Urdu / Both
└── document_hash            # For deduplication
```

#### Statute Datapoints (to verify per legislation source)

```
STATUTE IDENTITY
├── statute_title            # "Pakistan Penal Code"
├── statute_short_title      # "PPC"
├── statute_number           # Act number (e.g., "Act XLV of 1860")
├── statute_year             # Year of enactment
├── gazette_reference        # Gazette publication reference
└── enforcement_date         # When it came into force

STRUCTURE
├── chapter_number           # Chapter within the Act
├── chapter_title            # Chapter heading
├── part_number              # Part/Division if applicable
├── section_number           # Section number
├── section_title            # Section heading
├── section_text             # Full text of section
├── sub_sections             # Numbered sub-sections
├── provisos                 # Provisos and exceptions
├── explanations             # Explanations within section
├── illustrations            # Examples given in statute
└── schedules                # Appended schedules

AMENDMENTS
├── amendment_act            # Which act amended this
├── amendment_date           # When amended
├── amendment_section        # Which section was amended
├── original_text            # Text before amendment
├── amended_text             # Text after amendment
└── amendment_history        # Full amendment trail

CLASSIFICATION
├── legal_domain             # Criminal, Civil, Revenue, Constitutional, etc.
├── applicable_jurisdiction  # Federal / Provincial / Both
├── applicable_province      # If provincial
├── status                   # Active / Repealed / Partially Repealed
├── repealed_by              # If repealed, which act
└── related_statutes         # Cross-references to other acts

PENALTIES (where applicable)
├── offense_defined          # What offense this section creates
├── punishment_type          # Imprisonment, Fine, Both, Death
├── punishment_duration      # "Up to 7 years", "Life imprisonment"
├── fine_amount              # Fine details
├── bailable                 # Yes / No
├── compoundable             # Yes / No
└── cognizable               # Yes / No

METADATA
├── source_url
├── crawl_date
├── language                 # English / Urdu
└── document_hash
```

### 0.3 Qdrant Semantic Data Model

Based on 850+ verified datapoints across all legal domains:

#### Collection Architecture (VERIFIED — based on actual source data)

```
COLLECTION: pk_judgments
├── Vectors: dense (semantic) + sparse (BM25 citations) + colbert (reranking)
├── Payload: All judgment datapoints above
├── Chunking: Per-section (facts, arguments, reasoning, order — each a separate point)
├── Filters: court_level, legal_domain, outcome, date_judgment, judges
└── Use: Case research, precedent matching, judgment analysis

COLLECTION: pk_statutes
├── Vectors: dense + sparse
├── Payload: All statute datapoints above
├── Chunking: Per-section (each section = one point, with parent chapter context)
├── Filters: legal_domain, status, applicable_jurisdiction, statute_year
└── Use: Statute lookup, section search, amendment tracking

COLLECTION: pk_precedent_graph
├── Vectors: dense (semantic similarity between cases)
├── Payload: case_number, cited_by[], cites[], followed_by[], distinguished_by[], overruled_by[]
├── Chunking: One point per case (ratio decidendi only)
├── Filters: legal_domain, court_level, outcome
└── Use: Precedent chain navigation, finding supporting/opposing cases

COLLECTION: pk_legal_principles
├── Vectors: dense
├── Payload: principle_text, source_case, court, domain, established_date
├── Chunking: One point per legal principle extracted
├── Filters: legal_domain, court_level
└── Use: Find applicable legal principles for a given situation

COLLECTION: pk_evidence_patterns
├── Vectors: dense
├── Payload: evidence_type, admissibility_ruling, court, case_ref, reasoning
├── Chunking: One point per evidence ruling
├── Filters: evidence_type, admissibility, legal_domain
└── Use: Evidence strategy — what evidence was accepted/rejected and why

COLLECTION: pk_sentencing_data
├── Vectors: dense
├── Payload: offense, section, sentence_imposed, court, mitigating_factors, aggravating_factors
├── Chunking: One point per sentencing decision
├── Filters: offense_type, court_level, sentence_range
└── Use: Sentencing prediction, argument for mitigation

COLLECTION: pk_procedural_rulings
├── Vectors: dense
├── Payload: procedural_issue, ruling, court, case_ref, applicable_rule
├── Chunking: One point per procedural ruling
├── Filters: procedural_type, court_level
└── Use: Procedural strategy — what motions succeed/fail

COLLECTION: pk_bail_jurisprudence
├── Vectors: dense + sparse
├── Payload: bail_type (pre-arrest/post-arrest/ad-interim), offense, section, granted/refused,
│            grounds, judge, court, surety_amount, conditions, co-accused_status
├── Chunking: One point per bail decision
├── Filters: bail_type, offense_type, granted, court_level
└── Use: Bail strategy — what arguments succeed for which offenses

COLLECTION: pk_family_law
├── Vectors: dense + sparse
├── Payload: case_type (divorce/custody/maintenance/succession), mehr_amount,
│            maintenance_awarded, custody_to, child_ages, khula_grounds, iddat_status,
│            heir_shares, estate_value, visitation_schedule
├── Chunking: One point per family law ruling
├── Filters: case_type, custody_to, maintenance_range, court
└── Use: Family law precedents — maintenance amounts, custody factors, succession shares

COLLECTION: pk_property_disputes
├── Vectors: dense + sparse
├── Payload: property_type, dispute_type (title/possession/pre-emption/adverse_possession),
│            area, location, title_chain_complete, mutation_status, revenue_records,
│            limitation_status, outcome
├── Chunking: One point per property ruling
├── Filters: property_type, dispute_type, location_province, outcome
└── Use: Property dispute strategy — title chain, revenue record patterns

COLLECTION: pk_tax_rulings
├── Vectors: dense + sparse
├── Payload: tax_type (income/sales/customs/excise), section_cited, assessment_year,
│            tribunal (ATIR/HC/SC), taxpayer_type, issue_type, amount_disputed,
│            adjustment_upheld, procedural_defect
├── Chunking: One point per tax ruling
├── Filters: tax_type, tribunal, issue_type, assessment_year
└── Use: Tax dispute strategy — which arguments succeed at which tribunal level

COLLECTION: pk_labour_rulings
├── Vectors: dense + sparse
├── Payload: dispute_type (dismissal/wages/compensation/unfair_practice), industry,
│            worker_category, employer_type, NIRC_or_provincial, reinstatement_ordered,
│            compensation_amount, procedural_compliance
├── Chunking: One point per labour ruling
├── Filters: dispute_type, industry, tribunal, outcome
└── Use: Labour dispute precedents — dismissal validity, compensation benchmarks

COLLECTION: pk_constitutional_petitions
├── Vectors: dense + sparse
├── Payload: article_invoked (184(3)/199/etc), writ_type, fundamental_right,
│            public_interest, government_body_challenged, outcome, precedent_value,
│            suo_motu, alternative_remedy_exhausted
├── Chunking: One point per constitutional ruling
├── Filters: writ_type, article_invoked, outcome, court
└── Use: Constitutional strategy — writ success rates, fundamental rights patterns

COLLECTION: pk_limitation_periods
├── Vectors: dense
├── Payload: cause_of_action, limitation_years, applicable_statute, applicable_section,
│            accrual_event, condonation_possible, condonation_success_rate
├── Chunking: One point per limitation rule/ruling
├── Filters: cause_of_action, limitation_years
└── Use: Instant limitation check — is the claim time-barred?

COLLECTION: persona_knowledge
├── Vectors: dense
├── Payload: specialty, framework, source, central_idea, application_context
├── Chunking: One point per insight/framework
├── Filters: specialty, framework_type
└── Use: Agent persona behavior and reasoning style
```

**Total: 15 Qdrant collections** covering every legal domain with domain-specific payloads

#### Hybrid Search Strategy

```
Query Flow:
1. Pre-filter by metadata (court, domain, date range, etc.)
2. Dense vector search (semantic understanding)
3. Sparse vector search (exact citation/statute matching)
4. ColBERT reranking (token-level precision)
5. Score boosting (critical sections weighted higher)
6. Return top-K with full payload
```

---

## Phase 1: Persona Pipeline
> **Goal**: Build evolving lawyer personas from research
> **Depends on**: Nothing (can start immediately)

### Tasks

#### 1.1 Research Collection
- [ ] Identify top 20 legal excellence books/articles
- [ ] Extract content from each source
- [ ] Summarize key frameworks per specialty

#### 1.2 Persona Design (per specialty)
- [ ] Criminal Defense persona (zealous representation, reasonable doubt, evidence challenge)
- [ ] Criminal Prosecution persona (justice-seeking, evidence building, public interest)
- [ ] Civil Litigation persona (FIRAC analysis, procedural mastery, settlement strategy)
- [ ] Corporate/Commercial persona (transaction management, due diligence, compliance)
- [ ] Family Law persona (client sensitivity, mediation preference, child welfare)
- [ ] Constitutional Law persona (fundamental rights, judicial review, constitutional interpretation)
- [ ] Tax Law persona (statutory interpretation, tribunal procedure, penalty mitigation)
- [ ] Labour Law persona (worker protection, industrial disputes, employment contracts)

#### 1.3 Persona Evolution Pipeline
- [ ] Define persona schema (specialty, frameworks, central_ideas, behavioral_traits)
- [ ] Build ingestion pipeline: new research → extract → summarize → update persona
- [ ] Store in persona_knowledge collection
- [ ] Version personas (track how they evolve over time)

---

## Phase 2: Data Ingestion Pipelines
> **Goal**: Reliable weekly extraction from all Pakistani legal sources
> **Depends on**: Phase 0 (source verification complete)

### 2.1 Pipeline Architecture

```
Each pipeline follows:
  crawl4ai (fetch) → raw HTML
  → site-specific parser (extract structured data)
  → field extractor (pull all datapoints)
  → citation parser (normalize citations)
  → quality checker (validate required fields)
  → chunker (split into Qdrant-ready chunks)
  → embedder (dense + sparse + colbert vectors)
  → Qdrant ingester (upsert with full payload)
  → dedup checker (hash-based deduplication)
```

### 2.2 Court Judgment Pipelines (one per court)

#### Pipeline 01: Supreme Court Extractor
- [ ] Map site structure (supremecourt.gov.pk + NADRA portal)
- [ ] Build crawler for judgment search pages
- [ ] Extract all judgment datapoints (see 0.2)
- [ ] Handle PDF judgments (download + OCR if needed)
- [ ] Parse citation format (PLD, SCMR)
- [ ] Test with 100 judgments, validate extraction accuracy
- [ ] Schedule weekly crawl

#### Pipeline 02: Lahore High Court Extractor
- [ ] Map data.lhc.gov.pk/reported_judgments structure
- [ ] Build crawler for reported judgment pages
- [ ] Extract all judgment datapoints
- [ ] Handle library.lhc.gov.pk resources
- [ ] Test and validate
- [ ] Schedule weekly crawl

#### Pipeline 03: Sindh High Court Extractor
- [ ] Map caselaw.shc.gov.pk structure
- [ ] Map digital.shc.gov.pk for digital copies
- [ ] Build crawler for judgment pages
- [ ] Handle multiple bench locations (Karachi, Sukkur, Hyderabad, Larkana, Mirpurkhas)
- [ ] Test and validate
- [ ] Schedule weekly crawl

#### Pipeline 04: Islamabad High Court Extractor
- [ ] Map mis.ihc.gov.pk case search and order search
- [ ] Build crawler for judgment/order pages
- [ ] Handle Form HCJD/C-121 format
- [ ] Test and validate
- [ ] Schedule weekly crawl

#### Pipeline 05: Peshawar High Court Extractor
- [ ] Map CFMIS portal structure
- [ ] Build crawler for reported judgments
- [ ] Handle multiple benches (Abbottabad, Mingora, Bannu)
- [ ] Test and validate
- [ ] Schedule weekly crawl

#### Pipeline 06: Balochistan High Court Extractor
- [ ] Map bhc.gov.pk/resources/judgments
- [ ] Build crawler for judgment pages
- [ ] Handle multiple benches (Sibi, Turbat, Loralai, Khuzdar)
- [ ] Test and validate
- [ ] Schedule weekly crawl

#### Pipeline 07: Federal Shariat Court Extractor
- [ ] Map judgment database (searchable by case number, party, judge)
- [ ] Build crawler for leading judgments
- [ ] Handle Islamic law specific fields (Quran/Sunnah references)
- [ ] Test and validate
- [ ] Schedule weekly crawl

### 2.3 Legislation Pipelines

#### Pipeline 08: Pakistan Code Extractor
- [ ] Map pakistancode.gov.pk structure (alphabetical, chronological, categorical)
- [ ] Build crawler for statute pages
- [ ] Extract all statute datapoints (see 0.2)
- [ ] Handle bilingual content (English + Urdu)
- [ ] Track amendments (original vs amended text)
- [ ] Test and validate
- [ ] Schedule weekly crawl

#### Pipeline 09: National Assembly Extractor
- [ ] Map na.gov.pk bills and acts section
- [ ] Build crawler for legislative documents
- [ ] Extract bill status, readings, committee reports
- [ ] Handle gazette publications
- [ ] Test and validate
- [ ] Schedule weekly crawl

#### Pipeline 10: Senate Extractor
- [ ] Map senate.gov.pk legislation section
- [ ] Build crawler for bills and notifications
- [ ] Extract legislative history
- [ ] Test and validate
- [ ] Schedule weekly crawl

#### Pipeline 11: Legislation.pk Extractor
- [ ] Map legislation.pk structure (federal + all provinces)
- [ ] Build crawler for statute pages
- [ ] Handle provincial legislation separately
- [ ] Track amendment updates
- [ ] Test and validate
- [ ] Schedule weekly crawl

#### Pipeline 12-15: Provincial Assembly Extractors
- [ ] Punjab Assembly (pap.gov.pk) — legislation, bills, committees
- [ ] Sindh Assembly — legislation and resources
- [ ] KPK Assembly (pakp.gov.pk) — bills, acts
- [ ] Balochistan Assembly (pabalochistan.gov.pk) — acts, bills, ordinances

### 2.4 Free Database Pipelines

#### Pipeline 16: CommonLII Extractor
- [ ] Map commonlii.org Pakistan section
- [ ] Build crawler for cases (2002 onwards)
- [ ] Cross-reference with court-specific extractions (dedup)
- [ ] Test and validate
- [ ] Schedule weekly crawl

#### Pipeline 17-18: District Court Extractors
- [ ] Sindh District Courts (cases.districtcourtssindh.gos.pk)
- [ ] Federal Special Courts (federalcourts.molaw.gov.pk)

### 2.5 Shared Extraction Components

These are reused across all pipelines:

- [ ] `citation_parser.py` — Parse all Pakistani citation formats (PLD, SCMR, CLC, etc.)
- [ ] `judgment_section_splitter.py` — Split judgment into sections (facts, issues, arguments, reasoning, order)
- [ ] `statute_section_parser.py` — Parse statute structure (chapters, sections, sub-sections, provisos)
- [ ] `metadata_extractor.py` — Extract dates, parties, judges, court info
- [ ] `quality_checker.py` — Validate required fields present, flag low-confidence extractions
- [ ] `dedup_checker.py` — Hash-based deduplication across sources
- [ ] `urdu_handler.py` — Handle Urdu text extraction and transliteration

---

## Phase 3: Qdrant Reasoning & Search Layer
> **Goal**: Build the intelligent search and retrieval system
> **Depends on**: Phase 0 (data model), Phase 2 (data ingested)

### 3.1 Collection Setup

- [ ] Create all collections with proper vector configs (dense + sparse + colbert)
- [ ] Configure scalar quantization per collection
- [ ] Set up payload indexes on high-selectivity fields
- [ ] Configure multitenancy if needed (for future multi-firm support)

### 3.2 Chunking Strategies (per collection)

#### Judgments Chunking
```
Each judgment produces multiple Qdrant points:
├── Point 1: Case facts (with full case metadata)
├── Point 2: Issues/points of determination
├── Point 3: Petitioner arguments
├── Point 4: Respondent arguments
├── Point 5: Court reasoning (ratio decidendi)
├── Point 6: Final order + relief
├── Point 7: Dissenting opinion (if any)
└── All points share: case_number, court, date, parties, domain, outcome
```

#### Statutes Chunking
```
Each statute produces:
├── Point per section (with chapter/part context embedded)
├── Proviso points (linked to parent section)
├── Amendment points (before/after with amendment metadata)
└── All points share: statute_title, statute_year, domain, jurisdiction
```

### 3.3 Embedding Strategy

- [ ] Dense embeddings: OpenAI text-embedding-3-large (or legal-specific model if available)
- [ ] Sparse embeddings: BM25 via Qdrant's built-in sparse vector support
- [ ] ColBERT: For reranking on precision-critical queries
- [ ] Benchmark embedding models on Pakistani legal text (test retrieval quality)

### 3.4 Search Pipelines

#### Case Law Search Pipeline
```
User query → intent classifier →
  IF citation lookup → sparse search (exact match)
  IF semantic search → dense search + metadata filter → colbert rerank
  IF precedent chain → graph traversal in pk_precedent_graph
  → return ranked results with snippets
```

#### Statute Search Pipeline
```
User query →
  IF section lookup → sparse search (section number match)
  IF concept search → dense search + domain filter → rerank
  IF amendment history → filter by statute + sort by amendment_date
  → return section text with amendment history
```

#### Cross-Collection Search Pipeline
```
Complex query →
  parallel search across pk_judgments + pk_statutes + pk_legal_principles
  → merge and deduplicate results
  → rerank across collections
  → return unified results with source attribution
```

### 3.5 Relevance Tuning

- [ ] Build evaluation dataset (50+ query-answer pairs per collection)
- [ ] Test dense vs hybrid vs hybrid+colbert retrieval quality
- [ ] Tune score boosting weights per section type
- [ ] A/B test different chunking strategies
- [ ] Monitor and iterate on retrieval quality

---

## Phase 4: LangGraph Deep Agent
> **Goal**: Build multi-agent reasoning system
> **Depends on**: Phase 1 (personas), Phase 3 (search layer)

### 4.1 Agent Architecture

#### Supervisor Agent
- [ ] Define state schema (TypedDict with reducers)
- [ ] Implement query analysis and routing
- [ ] Build planning step (decompose complex queries into sub-tasks)
- [ ] Implement tool binding for all specialist agents
- [ ] Add reflection loop (evaluate output quality before returning)
- [ ] Add human-in-the-loop interrupts for high-stakes decisions

#### Specialist Agents

##### Case Researcher Agent
- Tools: pk_judgments search, pk_precedent_graph traversal
- Capability: Find relevant cases, analyze outcomes, build case matrix
- Output: Ranked list of relevant cases with summaries and relevance scores

##### Statute Analyst Agent
- Tools: pk_statutes search, amendment history lookup
- Capability: Find applicable law, check current status, trace amendments
- Output: Applicable sections with full text and amendment history

##### Precedent Matcher Agent
- Tools: pk_precedent_graph, pk_judgments search
- Capability: Find supporting precedents, distinguish unfavorable ones, trace citation chains
- Output: Supporting cases, distinguishable cases, overruled cases — with reasoning

##### Judgment Analyzer Agent
- Tools: pk_judgments deep search, pk_evidence_patterns, pk_sentencing_data
- Capability: Deep analysis of specific judgments
- Output: Structured breakdown — appeal reason, evidence gaps, judge reasoning, rules enforced, central idea

##### Legal Reasoner Agent
- Tools: All collections, persona_knowledge
- Capability: Apply IRAC/FIRAC, build arguments, counter-analysis
- Output: Structured legal analysis with citations and reasoning chain

##### Response Synthesizer Agent
- Tools: None (works on outputs from other agents)
- Capability: Format final response with persona voice, proper citations, structured layout
- Output: User-facing response

### 4.2 State Schema

```python
class LegalAnalysisState(TypedDict):
    # Input
    query: str
    legal_domain: str
    persona: str

    # Agent outputs (accumulated via reducers)
    messages: Annotated[list, add_messages]
    relevant_cases: Annotated[list, operator.add]
    applicable_statutes: Annotated[list, operator.add]
    precedent_analysis: Annotated[list, operator.add]
    judgment_breakdowns: Annotated[list, operator.add]
    legal_reasoning: str

    # Control flow
    plan: list[str]
    current_step: int
    requires_human_review: bool
    confidence_score: float

    # Final output
    final_response: str
    citations: list[str]
```

### 4.3 Workflow Graph

```
START → Supervisor (analyze + plan)
  → [parallel] Case Researcher + Statute Analyst
  → Precedent Matcher (uses case results)
  → Judgment Analyzer (deep dive on key cases)
  → Legal Reasoner (synthesize all findings)
  → Reflection Check
    → IF quality < threshold → back to relevant agent
    → IF quality >= threshold → Response Synthesizer
  → END
```

### 4.4 Persistence & Memory

- [ ] PostgreSQL checkpointer for state persistence
- [ ] Thread-based conversation memory
- [ ] Cross-thread memory store for user preferences
- [ ] Audit trail for all agent decisions

---

## Phase 5: Frontend & API
> **Goal**: Replace old chat UI with proper legal research interface
> **Depends on**: Phase 4 (agent working)

### 5.1 FastAPI Backend
- [ ] POST /analyze — Submit legal query, get streamed analysis
- [ ] GET /cases/{case_number} — Retrieve specific case
- [ ] GET /statutes/{section} — Retrieve specific statute
- [ ] GET /search — Cross-collection search
- [ ] GET /history — User query history
- [ ] WebSocket for streaming agent reasoning

### 5.2 React Frontend
- [ ] Legal query input with domain selector
- [ ] Streaming agent output with reasoning steps visible
- [ ] Case analysis view (structured breakdown)
- [ ] Citation links (click to see source)
- [ ] Precedent chain visualization
- [ ] Statute viewer with amendment timeline
- [ ] Chat history sidebar

---

## Build Order

```
Phase 0 ──→ Phase 1 (parallel) ──→ Phase 4
         ──→ Phase 2 ──→ Phase 3 ──→ Phase 4 ──→ Phase 5
```

- Phase 0 and Phase 1 can start immediately in parallel
- Phase 2 depends on Phase 0 (need verified sources)
- Phase 3 depends on Phase 0 (data model) and Phase 2 (data to ingest)
- Phase 4 depends on Phase 1 (personas) and Phase 3 (search layer)
- Phase 5 depends on Phase 4 (agent working)

---

## Research Archive (45 files, 3.5MB)

All in `research/` folder:

| File | Content |
|------|---------|
| `01_supreme_court_verification.md` | SC site verification, NADRA portal fields, alternative datasets |
| `02_lahore_hc_verification.md` | LHC portals, PDF URL patterns, field mappings |
| `03_sindh_hc_verification.md` | SHC 5 portals, district courts (500K-2M cases), crawler specs |
| `04_ihc_phc_bhc_verification.md` | 3 high courts verified, PHC best source, BHC blocked |
| `05_fsc_legislation_verification.md` | FSC, Pakistan Code, Legislation.pk, CommonLII structure |
| `06_assemblies_gazette_verification.md` | All assemblies, 2,700+ bills, implementation roadmap |
| `07_criminal_law_datapoints.md` | 200+ criminal fields, PPC/CrPC/ATA/CNSA/Hudood |
| `08_civil_law_datapoints.md` | 200+ civil fields, property/contract/family/succession |
| `09_constitutional_tax_labour_datapoints.md` | 450+ fields across 3 domains |
| `CRIMINAL_CASE_SCHEMA.json` | Production-ready JSON schema for criminal cases |
| `PAKISTAN_LEGAL_DATABASE_SCHEMA.sql` | 40+ normalized SQL tables for all domains |
| `sindh_courts_crawler_implementation.py` | Production Python crawler for Sindh district courts |
| + 33 more supporting docs | Quick references, checklists, implementation guides |

## Phase 2.6: Safety & Verification Architecture (CRITICAL — from competitive review)
> **Goal**: Prevent hallucination, ensure citation accuracy, handle contradictions
> **Depends on**: Runs parallel to Phase 2-3, integrated into Phase 4

### The Problem
- Legal-specific AI vendors: 17-34% hallucination rate (Stanford HAI 2025)
- General models without RAG: 69-88% error rate
- 200+ court-documented hallucination cases in 2025
- India Income Tax Tribunal cited 4 non-existent judgments → order recalled

### 2.6.1 Citation Verification Pipeline
```
Agent generates response with citations →
  Citation Verifier Agent:
    1. Extract all citations from response (PLD 2023 SC 123, etc.)
    2. Query pk_judgments/pk_statutes by exact citation
    3. IF citation NOT FOUND → flag and remove
    4. IF citation FOUND → verify claim matches source text
    5. IF claim MISMATCHES source → flag and correct
    6. Return verified response with confidence per citation
```
- [ ] Build citation extraction regex (all Pakistani formats)
- [ ] Build citation lookup tool (exact match in Qdrant sparse index)
- [ ] Build claim-to-source verification (does the cited case actually say this?)
- [ ] Build confidence scoring (ensemble disagreement, not model self-report)

### 2.6.2 Hallucination Prevention Layers
```
Layer 1: Source Grounding
  - NEVER generate legal content without RAG context
  - Every claim must trace to a retrieved document
  - If no relevant document found, say "insufficient data" not guess

Layer 2: Structural Verification
  - Display exact source text supporting each claim in UI
  - Hyperlink every citation to its source document
  - Show which Qdrant collection and point_id backed each fact

Layer 3: Contradiction Detection
  - When multiple precedents conflict, present BOTH sides
  - Distinguish ratio decidendi (binding) vs obiter dictum (non-binding)
  - Flag jurisdictional mismatches (Lahore HC vs Sindh HC)
  - Flag overruled precedents automatically via pk_precedent_graph

Layer 4: Confidence & Uncertainty
  - Use ensemble method: if multiple retrieval paths disagree → flag uncertainty
  - Never trust model self-reported confidence
  - Require minimum 3 supporting documents for high-confidence answers
  - Flag novel legal questions with no precedent
```

### 2.6.3 Evaluation Framework
- [ ] Build Pakistani LegalBench: 500+ query-answer pairs across all domains
- [ ] Metrics: citation_accuracy, retrieval_precision@10, retrieval_recall, MRR
- [ ] Baseline: manual lawyer research time vs system time
- [ ] A/B test: structured retrieval vs unstructured retrieval quality
- [ ] Monthly accuracy audits with practicing lawyers

---

## Phase 2.7: Structural Reasoning & Data Individuality ✓ COMPLETE
> **Goal**: Maximize retrieval precision through structured datapoint decomposition
> **Key insight**: Structured retrieval with 850+ datapoints >> unstructured full-text search
> **Status**: IMPLEMENTED — Reasoning Point Decomposition (#25) + Data Individuality (#26) + Tier B null-string fix
> **Commits**: `aff2b17` (reasoning decomposition), `d16cbf9` (data individuality), `50f03ec` (tier B fix)
> **Tests**: 99 passing (36 reasoning, 14 point ID, rest extraction + ingestion)

### The Core Principle
Every legal document contains dozens of independent reasoning points. Searching full text conflates them. Our edge: decompose each document into individual reasoning atoms, each independently searchable with rich metadata.

### 2.7.1 Reasoning Point Decomposition

```
One Judgment → N Reasoning Points:

POINT: Case Identity
  → case_number, court, bench, judges, date, parties
  → USE: Exact lookup, deduplication, citation verification

POINT: Facts of Case
  → factual_summary, key_events[], timeline, disputed_facts[]
  → USE: Find cases with similar fact patterns

POINT: Legal Issues Framed
  → issues[], sub_issues[], issue_classification
  → USE: Find how courts frame similar legal questions

POINT: Petitioner Arguments (per argument)
  → argument_text, supporting_precedents[], sections_cited[], strength_assessment
  → USE: Find winning arguments for similar cases

POINT: Respondent Arguments (per argument)
  → argument_text, counter_precedents[], sections_cited[], strength_assessment
  → USE: Anticipate opposing counsel's strategy

POINT: Evidence Assessment (per evidence item)
  → evidence_type, admissibility_ruling, weight_given, reasoning
  → USE: Predict evidence admissibility, build evidence strategy

POINT: Court Reasoning (per issue)
  → issue_addressed, applicable_law, precedent_applied, precedent_distinguished,
    reasoning_chain, conclusion_on_issue
  → USE: CORE VALUE — understand how judges think about specific issues

POINT: Ratio Decidendi (THE binding principle)
  → principle_text, scope, limitations, conditions
  → USE: Find applicable legal principles, build precedent arguments

POINT: Obiter Dicta (non-binding observations)
  → observation_text, relevance, persuasive_value
  → USE: Persuasive arguments, predict future law development

POINT: Final Order
  → relief_granted, conditions, costs, execution_timeline
  → USE: Predict likely outcomes, plan relief strategy

POINT: Dissent (if any)
  → dissenting_judge, dissent_reasoning, dissent_principle
  → USE: Appeal strategy — dissents often become future majority opinions
```

### 2.7.2 Data Individuality Methods

Each reasoning point gets a **unique identity** for precise retrieval:

```
Point ID Structure:
  {court}:{case_number}:{point_type}:{sequence}

Examples:
  SC:CA-123-2023:ratio:1
  LHC:WP-456-2022:evidence:3
  SHC:CRA-789-2021:reasoning:issue-2

Each point carries:
  - point_id (unique across system)
  - parent_case_id (links back to full judgment)
  - point_type (enum: facts, issue, argument, evidence, reasoning, ratio, obiter, order, dissent)
  - point_sequence (order within case)
  - legal_domain (criminal, civil, constitutional, etc.)
  - sub_domain (murder, property, writ, etc.)
  - sections_cited[] (statutes referenced in THIS point)
  - precedents_cited[] (cases referenced in THIS point)
  - extraction_confidence (0.0-1.0)
```

### 2.7.3 Structural Identification Filters

The more we divide, the easier search becomes:

```
FILTER DIMENSIONS (each enables targeted retrieval):

By Legal Domain:     criminal | civil | constitutional | tax | labour | family | corporate
By Sub-Domain:       murder | property | writ | divorce | bail | customs | dismissal | ...
By Court Level:      SC | HC | Sessions | Magistrate | FSC | ATIR | NIRC
By Court Location:   Islamabad | Lahore | Karachi | Peshawar | Quetta | Multan | ...
By Outcome:          allowed | dismissed | partly_allowed | remanded | withdrawn
By Point Type:       facts | issue | argument | evidence | reasoning | ratio | obiter | order
By Date Range:       filing_date, judgment_date, hearing_date
By Judge:            specific judge → track decision patterns
By Section Cited:    specific PPC/CPC/CrPC section → find all rulings on that section
By Citation:         exact PLD/SCMR/CLC reference
By Evidence Type:    documentary | oral | expert | forensic | confession | FIR
By Procedural Stage: trial | first_appeal | second_appeal | revision | review
By Limitation:       within_period | time_barred | condonation_granted
By Bail Type:        pre_arrest | post_arrest | ad_interim | confirmation
By Property Type:    agricultural | residential | commercial | industrial
By Family Subtype:   divorce | custody | maintenance | succession | guardianship
By Tax Type:         income | sales | customs | excise
```

### 2.7.4 Chunking Strategy (Summary-Augmented — from research)

Research shows Summary-Augmented Chunking (SAC) reduces Document-Level Retrieval Mismatch by ~50%:

```
For each reasoning point chunk:
  1. Generate a synthetic summary of the FULL judgment (once per case)
  2. Prepend summary to EVERY chunk from that case
  3. This preserves document-level context in each individual point
  4. Generic summaries outperform expert-legal summaries (broader context wins)

Chunk Structure:
  [CASE SUMMARY: 2-3 sentence overview of full case]
  [POINT TYPE: Court Reasoning on Issue 2]
  [ACTUAL TEXT: The court reasoning text...]

  + Full metadata payload attached
```

### 2.7.5 Embedding Strategy (Updated from competitive review)

```
Priority 1: Benchmark on Pakistani legal text
  - Voyage-law-2 (16K context, +6% over OpenAI on legal)
  - OpenAI text-embedding-3-large (baseline)
  - Cohere embed-v3 (multilingual — may handle Urdu better)
  - Run retrieval quality test on 200 sample queries

Priority 2: Sparse vectors
  - BM25 for exact citation/section matching
  - Critical for: "PLD 2023 SC 123" or "Section 302 PPC"

Priority 3: ColBERT reranking
  - Token-level precision for legal nuance
  - "willful murder" vs "culpable homicide" distinction matters

Priority 4: Cross-encoder (if ColBERT insufficient)
  - Re-rank top-50 with cross-encoder
  - 10-50ms per document — acceptable for legal research
```

---

## Phase 2.8: Precedent Graph (Neo4j)
> **Goal**: True graph traversal for citation chains — payloads can't do this
> **Depends on**: Phase 2 (extracted citations from judgments)

### Why Qdrant Payloads Aren't Enough
- "Find all cases that cite PLD 2010 SC 47 AND were later overruled" → requires graph traversal
- "Trace the evolution of Section 302 PPC interpretation from 1990 to 2024" → requires path queries
- "Which judge's decisions get overruled most?" → requires aggregation across citation network

### Neo4j Graph Model
```
Nodes:
  (:Case {case_number, court, date, domain, outcome})
  (:Statute {title, section, year})
  (:Judge {name, court, appointment_date})
  (:LegalPrinciple {text, domain, established_date})

Edges:
  (Case)-[:CITES]->(Case)
  (Case)-[:FOLLOWS]->(Case)       # Applies same principle
  (Case)-[:DISTINGUISHES]->(Case) # Says facts differ
  (Case)-[:OVERRULES]->(Case)     # Reverses earlier ruling
  (Case)-[:INTERPRETS]->(Statute)
  (Case)-[:DECIDED_BY]->(Judge)
  (Case)-[:ESTABLISHES]->(LegalPrinciple)
  (LegalPrinciple)-[:DERIVED_FROM]->(Statute)
```

### Graph Queries We Need
- [ ] Find precedent chain: Case A → cited by B → distinguished by C → overruled by D
- [ ] Find all cases interpreting Section X of Statute Y
- [ ] Find judge decision patterns (success rate by domain)
- [ ] Find contradictory precedents on same legal question
- [ ] Find most-cited cases per domain (influence ranking)

---

## Open Questions

- [ ] Which LLM for agents? Claude vs GPT-4 vs local model?
- [ ] Qdrant Cloud vs self-hosted?
- [ ] Do we need Urdu language support in embeddings?
- [ ] Budget for OpenAI embeddings at scale?
- [ ] How to handle PDF judgments (many courts publish PDFs)?
- [ ] Do we want real-time crawling or batch-only?
- [ ] Multi-user support / authentication needed?
