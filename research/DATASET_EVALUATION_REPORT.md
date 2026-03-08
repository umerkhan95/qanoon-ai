# Dataset Evaluation Report — Ticket #13

## Evaluated: 2026-03-08

---

## 1. HuggingFace: `Ibtehaj10/supreme-court-of-pak-judgments`

| Property | Value |
|----------|-------|
| Records | 1,414 |
| Format | Parquet (25.1 MB) |
| License | MIT |
| Fields | `text`, `case_details`, `citation_number`, `embeddings` |
| Embedding Model | `mixedbread-ai/mxbai-embed-large-v1` (1024-dim) |
| Source | SC judgments (PDF-extracted text) |

### Quality Findings

**Text Quality:**
- Text lengths: min=2, max=632,725, avg=21,330 chars
- p5=2,544, p25=5,457, p50=9,407, p75=20,307, p95=78,439
- 6 records have text < 100 chars (garbage: whitespace, "Scanned with CamScanner")
- 206 empty records = 0% (these 6 are near-empty, ~0.4%)
- All 6/6 sampled contain "SUPREME COURT" header, 5/6 have "Justice" names, 6/6 have date patterns

**Metadata Quality:**
- `case_details` and `citation_number` are IDENTICAL in all 1,414 records (100% redundant)
- Format: `{'id': 'C.A.10_2021.pdf', 'url': ''}` — url is always empty
- All 1,414 case_details are unique (no duplicates by ID)
- 5 potential duplicate groups detected by text content hash

**Case Type Distribution:**
| Type | Count | Description |
|------|-------|-------------|
| C.A. | 322 | Civil Appeals |
| Crl.P.L.A. | 288 | Criminal Petition for Leave to Appeal |
| C.P.L.A. | 233 | Civil Petition for Leave to Appeal |
| Crl.A. | 149 | Criminal Appeals |
| C.P. | 90 | Constitutional Petitions |
| S.M.C. | 69 | Suo Motu Cases |
| C.M.A. | 68 | Civil Miscellaneous Applications |
| J.P. | 66 | Jail Petitions |
| C.R.P. | 35 | Civil Revision Petitions |
| H.R.C. | 27 | Human Rights Cases |

**Year Distribution:**
- Covers 1898-2023 (mostly 2005-2023)
- Peak: 2020 (160 cases), 2016 (135), 2017 (133)
- Sparse before 2005 (< 10 per year)
- No 2024 data despite being published July 2024

**Embedding Quality:**
- L2 norms: min=15.92, max=18.22, avg=17.25, stdev=0.45
- No zero/degenerate embeddings detected
- CRITICAL: Model has 512-token max input. Judgments avg 21,330 chars (~5,000+ tokens). **Embeddings only represent first ~1-2 pages of each judgment**
- These embeddings are NOT suitable for production retrieval — must re-embed

### Verdict: USEFUL FOR TEXT, DISCARD EMBEDDINGS

- Raw text: **KEEP** — 1,408 valid SC judgments with extractable metadata
- Embeddings: **DISCARD** — 512-token truncation makes them unreliable
- Metadata: **RE-EXTRACT** — must parse judges, dates, parties, citations from text
- Use as: Validation dataset for datapoint schema testing (#14-#17)

---

## 2. Kaggle: `shahsayesha/supreme-court-of-pakistan-judgment`

| Property | Value |
|----------|-------|
| Records | **2,809** (NOT 20,809 as claimed) |
| Format | Individual .txt files in ZIP (65.2 MB) |
| License | MIT |
| Fields | Raw text only (no structured metadata) |

### CRITICAL FINDING: Count Mismatch
**Dataset description claims 20,809 judgments. Actual file count: 2,809.**
The "20,809" appears to be a typo or miscount. This is a ~87% shortfall from expected.

### Quality Findings

**Text Quality:**
- File sizes: min=0, max=1.87 MB, avg=23 KB
- p25=5.5 KB, p50=10.7 KB, p75=21.8 KB
- **206 completely empty files (0 bytes)** = 7.3% garbage rate
- **215 files < 100 bytes** = 7.6% effectively useless
- Usable files: ~2,594

**Metadata (from text, not structured):**
- 9/10 sampled have judge names
- 9/10 have date patterns
- 9/10 have "Supreme Court" header
- 7/10 have "Versus" (party markers)
- 0/10 encoding issues

**Filename Problem:**
- ALL 2,809 files named `C.A_supreme (N).txt`
- Only Civil Appeal type — no criminal, constitutional, or other case types
- This is a SINGLE case type, not a comprehensive SC dataset

### Verdict: LIMITED VALUE — SINGLE CASE TYPE ONLY

- Only Civil Appeals (C.A.) — missing criminal, constitutional, tax, labour, family
- 7.3% empty files
- No structured metadata
- Count mismatch (2,809 vs claimed 20,809)
- Use as: Supplementary C.A. corpus only, after cleaning

---

## 3. Kaggle: `ammarshafiq/supreme-court-of-pakistan-judgments-dataset`

| Property | Value |
|----------|-------|
| Records | ~1,200 judgments |
| Format | CSV + PDF (393 MB) |
| License | MIT |
| Coverage | 25 named justices, up to May 2025 |
| Also on | IEEE DataPort (DOI: 10.21227/jt6c-wk29) |

### Status: NOT YET DOWNLOADED — needs evaluation
More recent than other datasets (May 2025). Has CSV structure + original PDFs. Worth investigating.

---

## 4. HuggingFace: `AyeshaJadoon/Pakistan_Laws_Dataset`

| Property | Value |
|----------|-------|
| Records | 967 laws/acts |
| Format | JSON (pdf_data.json) |
| License | ODC-BY |
| Source | Ministry of Law and Justice website (PDFs → JSON) |
| Fields | `file_name`, `text` |

### Quality Findings

**Text Quality:**
- 919/967 records have text > 100 chars (95% usable)
- Text lengths: min=28, max=2,578,313 chars, avg=45,411
- p25=7,082, p50=17,637, p75=39,810
- Well-structured legal text with section numbers, tables of contents

**Content Types Found:**
- Ordinances (Privatisation Commission Ordinance 2000)
- Land laws (Requisitioned Land Ordinance 1969)
- University acts (Foundation University Ordinance 2002)
- Court acts (Islamabad High Court Act 2010)
- International agreements and institutional charters

**Issues:**
- File names are hashed (`administrator00532129...pdf`) — not human-readable
- No structured metadata (act name, year, type must be extracted from text)
- ~48 records with very short text (< 100 chars) — likely failed PDF extraction

### Verdict: VALUABLE — UNIQUE STATUTE DATA

- Only dataset with Pakistani statute/act full text
- Covers 919+ laws from Ministry of Law and Justice
- Must extract: act name, year, type, sections from text
- Complementary to judgment datasets — fills the `pk_statutes` collection

---

## 5. HuggingFace: `mariamffatima/lawbridge-pakistan-legal-dataset`

| Property | Value |
|----------|-------|
| Records | 2,449 QA pairs (train: 2,200, test: 245) |
| License | Not specified |
| Fields | `input_text` (question), `target_text` (answer) |
| Coverage | Family law, criminal law, child marriage, domestic violence |

### Status: NOT YET DOWNLOADED
Useful for: evaluation dataset, fine-tuning QA models. Not for retrieval corpus.

---

## Quality Assessment Against Industry Standards

### Checklist Results

| Criterion | HF Judgments | Kaggle Judgments | HF Statutes |
|-----------|:---:|:---:|:---:|
| Unique case ID | Yes | No | No |
| Court name in text | Yes | Yes | N/A |
| Decision date extractable | Yes | Yes | Yes (act year) |
| Parties extractable | Mostly | Mostly | N/A |
| Judge names | Yes | Yes | N/A |
| Case type classification | From filename | No (all C.A.) | From text |
| Full text complete | Mostly | Mostly | Mostly |
| No truncation | Yes | Yes | Yes |
| UTF-8 encoding | Clean | Clean | Clean |
| No OCR artifacts | Clean | Clean | Clean |
| No duplicates | ~5 groups | Unknown | Unknown |
| Structured metadata | None | None | None |
| Citations extractable | From text | From text | From text |
| License clear | MIT | MIT | ODC-BY |

### Key Gap: ALL datasets lack structured metadata
Every dataset is raw text. None has pre-extracted:
- Judge names as separate field
- Decision dates as separate field
- Party names as separate field
- Citation numbers as separate field
- Case outcome (allowed/dismissed)
- Statutes cited

**This validates our metadata extraction pipeline (#34) as essential.**

---

## Recommended Action Plan

### Immediate (this session):
1. Save HF judgments dataset locally (1,414 records, discard embeddings)
2. Save HF statutes dataset locally (967 records)
3. Clean Kaggle dataset (remove 206 empty files)

### Next tickets to prioritize:
1. **#14 Criminal Datapoints** — validate schema against real Crl.A. and Crl.P.L.A. judgments from HF dataset
2. **#34 Shared Extraction Components** — build citation parser, judge extractor, date normalizer, section splitter — these are needed before ANY data can be ingested into Qdrant
3. **#19 Embedding Model Selection** — the HF embeddings (mxbai-embed-large-v1, 512 tokens) are inadequate. Need to benchmark Voyage-law-2 and others on these real texts

### Datasets to still download and evaluate:
- `ammarshafiq` Kaggle dataset (1,200 judgments with CSV structure + PDFs, up to May 2025)
- `mariamffatima` QA pairs (for evaluation dataset #33)
