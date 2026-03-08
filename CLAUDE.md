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

## Directory Structure (Target)

```
├── CLAUDE.md
├── plans.md
├── src/
│   ├── pipelines/           # crawl4ai extractors (one per site)
│   │   ├── supreme_court/
│   │   ├── lahore_hc/
│   │   ├── sindh_hc/
│   │   ├── islamabad_hc/
│   │   ├── peshawar_hc/
│   │   ├── balochistan_hc/
│   │   ├── federal_shariat/
│   │   ├── pakistan_code/
│   │   ├── national_assembly/
│   │   ├── senate/
│   │   ├── legislation_pk/
│   │   ├── provincial_assemblies/
│   │   └── commonlii/
│   ├── extractors/          # Structured field extractors
│   │   ├── judgment_extractor.py
│   │   ├── statute_extractor.py
│   │   ├── citation_parser.py
│   │   └── metadata_extractor.py
│   ├── qdrant/              # Vector store layer
│   │   ├── collections.py
│   │   ├── embeddings.py
│   │   ├── ingestion.py
│   │   └── search.py
│   ├── agents/              # LangGraph agents
│   │   ├── supervisor.py
│   │   ├── case_researcher.py
│   │   ├── statute_analyst.py
│   │   ├── precedent_matcher.py
│   │   ├── judgment_analyzer.py
│   │   ├── legal_reasoner.py
│   │   └── response_synthesizer.py
│   ├── personas/            # Lawyer persona configs
│   │   ├── criminal_defense.py
│   │   ├── criminal_prosecution.py
│   │   ├── civil_litigation.py
│   │   ├── corporate.py
│   │   ├── family.py
│   │   ├── constitutional.py
│   │   ├── tax.py
│   │   └── labor.py
│   ├── api/                 # FastAPI backend
│   └── frontend/            # React UI
├── config/
├── tests/
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
