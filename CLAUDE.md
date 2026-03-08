# Pakistani Legal Intelligence Platform (Qanoon AI)

## What This Is

A multi-agent legal intelligence platform for Pakistani law. LangGraph Deep Agent orchestrates specialist lawyer agents backed by Qdrant vector collections, fed by crawl4ai data pipelines extracting from all major Pakistani legal sources.

**Evolution**: Started as a simple OpenAI chat wrapper (v0). Now being rebuilt as a full legal AI stack.

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (React)                   │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              LangGraph Deep Agent                    │
│  ┌─────────────────────────────────────────────┐    │
│  │         Supervisor (Router + Planner)         │    │
│  └──────┬───────┬───────┬───────┬───────┬──────┘    │
│         │       │       │       │       │            │
│    Case    Statute  Precedent Judgment  Legal        │
│  Researcher Analyst  Matcher  Analyzer  Reasoner     │
│         │       │       │       │       │            │
│  ┌──────▼───────▼───────▼───────▼───────▼──────┐    │
│  │           Tool Layer (Qdrant Retrievers)      │    │
│  └──────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              Qdrant Vector Store                     │
│  Collections: case_law, statutes, judgments,         │
│  legal_commentary, persona_knowledge, ...            │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│           crawl4ai Data Pipelines                    │
│  Per-website extractors → classify → chunk → embed   │
│  Weekly scheduled crawls (reliable, not fast)        │
└─────────────────────────────────────────────────────┘
```

## Core Systems

### 1. Persona Pipeline
- Research → extract → summarize → central ideas → store
- Evolves over time as data improves
- Per-specialty personas (criminal, civil, corporate, family, constitutional, tax, labor)
- Frameworks: IRAC/FIRAC reasoning, CREAC arguments, Pakistani judgment standards

### 2. Data Ingestion (crawl4ai)
- One dedicated extractor per source website
- Weekly reliable crawls
- Structured extraction: metadata + full text + citations + sections
- Classification and quality checks before Qdrant ingestion

### 3. Qdrant Vector Architecture
- Hybrid search: Dense + Sparse + ColBERT reranking
- Scalar quantization (not binary)
- Rich payloads per document type
- Separate collections per legal data category
- Semantic data model designed for legal search patterns

### 4. LangGraph Deep Agent
- Supervisor pattern with specialist workers
- Multi-hop retrieval across collections
- Reflection loop for quality
- Human-in-the-loop for high-stakes
- Persistent state with PostgreSQL checkpointer

### 5. Frontend
- Replace old React chat with proper legal research UI
- Structured output display (not just chat bubbles)
- Case analysis views, citation links, reasoning chains

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Orchestration | LangGraph (supervisor + workers) |
| Vector Store | Qdrant (hybrid search, ColBERT) |
| Data Ingestion | crawl4ai |
| LLM | Claude / GPT-4 (configurable) |
| Backend | FastAPI |
| Frontend | React + Vite |
| Task Queue | Celery + Redis |
| Persistence | PostgreSQL (checkpoints) + Supabase |
| Embeddings | OpenAI / Cohere (dense) + BM25 (sparse) |

## Pakistani Legal Sources (Crawlable)

### Courts
- Supreme Court of Pakistan (supremecourt.gov.pk)
- Lahore High Court (lhc.gov.pk, data.lhc.gov.pk)
- Sindh High Court (sindhhighcourt.gov.pk, caselaw.shc.gov.pk)
- Islamabad High Court (ihc.gov.pk, mis.ihc.gov.pk)
- Peshawar High Court (peshawarhighcourt.gov.pk)
- Balochistan High Court (bhc.gov.pk)
- Federal Shariat Court (federalshariatcourt.gov.pk)

### Legislation
- Pakistan Code (pakistancode.gov.pk)
- National Assembly (na.gov.pk)
- Senate (senate.gov.pk)
- Legislation.pk
- Provincial Assemblies (Punjab, Sindh, KPK, Balochistan)

### Free Databases
- CommonLII (commonlii.org — cases from 2002+)

### Restricted (DO NOT crawl)
- Pakistan Law Site (pakistanlawsite.com) — ToS prohibits crawling

## Citation Formats

| Code | Full Name | Use |
|------|-----------|-----|
| PLD | Pakistan Legal Decisions | All courts |
| SCMR | Supreme Court Monthly Review | SC cases |
| CLC | Civil Law Cases | Civil |
| PCrLJ | Pakistan Criminal Law Journal | Criminal |
| PTD | Pakistan Tax Decisions | Tax |
| PLC | Pakistan Labour Cases | Labour |
| CLD | Corporate Law Decisions | Corporate |
| YLR | Yearly Law Reporter | Annual |
| MLD | Monthly Law Digest | Monthly |

## Implementation Status

### Completed
- **Three-tier criminal extraction pipeline** — Tier A (regex/NER), Tier B (LLM classification, 65 fields), Tier C (LLM reasoning texts, 17 fields)
- **Reasoning Point Decomposition** (#25) — Judgments decomposed into 5-50+ atomic reasoning points (facts, issues, arguments, evidence, court reasoning, ratio decidendi, obiter dicta, final order, dissent). Each point independently searchable in Qdrant with rich metadata.
- **Data Individuality** (#26) — Deterministic UUID3 point IDs from structured keys (`{court}:{case_number}:{point_type}:{sequence}`), multi-point ingestion, payload collision prevention via `reasoning_metadata` namespacing.
- **SAC Chunking** (#18) — Summary-Augmented Chunking with section-based splitting
- **pk_judgments Qdrant collection** (#20) — Hybrid search (dense + sparse BM25), 4 reasoning payload indexes
- **Voyage 3.5 embeddings** (#19) — Legal-specific embedding model
- **CommonLII crawler** (#8) — 2,906 SC cases from commonlii.org

### Key Modules
| Module | Path | Responsibility |
|--------|------|----------------|
| Tier A (regex) | `src/extractors/criminal/tier_a.py` | Fast deterministic extraction |
| Tier B (LLM) | `src/extractors/criminal/tier_b.py` | 65 reasoned classification fields |
| Tier C (LLM) | `src/extractors/criminal/tier_c.py` | 17 reasoning text fields |
| Reasoning Points | `src/extractors/criminal/reasoning_points.py` | Atomic point decomposition |
| Reasoning Schema | `src/extractors/criminal/reasoning_schema.py` | Pydantic models for reasoning |
| Pipeline | `src/extractors/criminal/pipeline.py` | Orchestrates all 4 passes |
| Point IDs | `src/qdrant/point_id.py` | Deterministic UUID generation |
| Ingestion | `src/qdrant/ingestion.py` | Multi-point Qdrant upsert |
| Collections | `src/qdrant/collections.py` | pk_judgments schema + indexes |
| Embeddings | `src/qdrant/embeddings.py` | Voyage 3.5 embedding service |

### Known LLM Patterns to Handle
- LLM returns literal `"null"`, `"None"`, `"N/A"` strings instead of JSON null — must filter before Pydantic validation
- LLM returns `"null"` inside lists (e.g., `["null", "first_offense"]`) — must filter per-element
- LLM errors propagate from Tier B/C/Reasoning → pipeline catches `LLMContentRefused`, `LLMParsingError`, `LLMError`

## Code Rules

- Never add Co-Authored-By or any co-author lines in git commit messages
- **Single Responsibility Principle (SRP)**: Every module, function, and file does exactly ONE thing. Split early, split often. One file = one concern. One function = one job. This is non-negotiable for maintainability in Claude Code workflows.
- One extractor per website — no shared extraction logic
- Plain functions preferred over classes (use classes only for data models like Pydantic schemas)
- All config via environment variables
- No hardcoded URLs or API keys
- Reusable components across pipelines (shared utilities in `common/`)
- Every pipeline module independently testable — each extractor works standalone
- Qdrant collections follow semantic data model (see plans.md)
- All legal data must preserve original citation format
- Never discard metadata — extract everything, filter later
- Type hints on all function signatures
- Pydantic models for all data structures crossing module boundaries

## Directory Structure

```
├── CLAUDE.md
├── plans.md
├── src/
│   ├── pipelines/           # crawl4ai extractors (one per site)
│   │   └── commonlii/      # ✓ IMPLEMENTED — 2,906 SC cases
│   ├── extractors/          # Structured field extractors
│   │   ├── common/          # Shared utilities (llm_client, json_utils)
│   │   └── criminal/        # ✓ IMPLEMENTED — 4-pass extraction
│   │       ├── tier_a.py    # Regex/NER extraction
│   │       ├── tier_b.py    # LLM classification (65 fields)
│   │       ├── tier_c.py    # LLM reasoning texts (17 fields)
│   │       ├── reasoning_points.py   # Atomic point decomposition
│   │       ├── reasoning_schema.py   # Pydantic models for reasoning
│   │       ├── schema.py    # CriminalExtractionResult, TierA/B/C
│   │       ├── pipeline.py  # Orchestrates all 4 passes
│   │       └── chunker.py   # SAC chunking
│   ├── qdrant/              # ✓ IMPLEMENTED — Vector store layer
│   │   ├── collections.py   # pk_judgments schema + indexes
│   │   ├── embeddings.py    # Voyage 3.5 embedding service
│   │   ├── ingestion.py     # Multi-point upsert (full_text, chunk, tier_c, reasoning)
│   │   ├── point_id.py      # Deterministic UUID3 generation
│   │   └── search.py        # Hybrid search (dense + sparse)
│   ├── agents/              # TODO — LangGraph agents
│   ├── personas/            # TODO — Lawyer persona configs
│   ├── api/                 # TODO — FastAPI backend
│   └── frontend/            # TODO — React UI
├── data/                    # Local data files (gitignored)
├── tests/                   # 99 tests passing
└── research/                # Research notes and findings
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| OPENAI_API_KEY | Yes | For embeddings and LLM |
| QDRANT_URL | Yes | Qdrant instance URL |
| QDRANT_API_KEY | Yes | Qdrant auth |
| DATABASE_URL | Yes | PostgreSQL for checkpoints |
| REDIS_URL | Yes | Celery broker |
| CRAWL4AI_* | No | crawl4ai specific configs |
