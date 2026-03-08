# Qanoon AI

Pakistani Legal Intelligence Platform — multi-agent legal research powered by LangGraph, Qdrant, and crawl4ai.

## What It Does

Qanoon AI decomposes Pakistani court judgments into independently searchable atomic reasoning points, enabling precise legal research across 850+ structured datapoints.

**Example queries it enables:**
- "Find all cases where recovery memo evidence was challenged and excluded"
- "How did the Supreme Court reason about Section 302 PPC in honour killing cases?"
- "What mitigating factors led to sentence reduction in drug trafficking appeals?"

## Architecture

```
crawl4ai Pipelines → Extraction (4-pass) → Qdrant (hybrid search) → LangGraph Agents → React UI
```

### Extraction Pipeline (Criminal Law — Implemented)

Each judgment goes through 4 extraction passes:

| Pass | Method | Output |
|------|--------|--------|
| Tier A | Regex/NER | Case number, court, judges, dates, sections, precedents |
| Tier B | LLM Classification | 65 reasoned fields (judgment type, offense category, evidence classification, etc.) |
| Tier C | LLM Reasoning | 17 long-form text fields (facts, arguments, court reasoning, ratio decidendi) |
| Reasoning Points | LLM Decomposition | 5-50+ atomic points per judgment (10 types) |

### Reasoning Point Types

Each judgment is decomposed into independent, searchable atoms:

- **Facts** — Factual narrative summary
- **Issues** — Each distinct legal question addressed
- **Petitioner Arguments** — Each argument with supporting precedents
- **Respondent Arguments** — Each counter-argument with precedents
- **Evidence** — Each evidence item with admissibility and weight
- **Court Reasoning** — Judge's analysis per issue (most valuable)
- **Ratio Decidendi** — Binding legal principle established
- **Obiter Dicta** — Non-binding observations
- **Final Order** — Conviction/acquittal/remand/sentence
- **Dissent** — Dissenting opinion if any

### Qdrant Storage

Each judgment produces N points in Qdrant with deterministic UUIDs:

```
{court}:{case_number}:full_text:0     → Full judgment vector
{court}:{case_number}:chunk:{N}       → Paragraph-split chunks (long judgments)
{court}:{case_number}:tier_c:{field}  → Each Tier C reasoning text
{court}:{case_number}:reasoning:{N}   → Each atomic reasoning point
```

Hybrid search: Dense (Voyage 3.5) + Sparse (BM25) vectors per point.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Orchestration | LangGraph (supervisor + workers) |
| Vector Store | Qdrant (hybrid search) |
| Data Ingestion | crawl4ai |
| LLM | OpenAI (configurable) |
| Embeddings | Voyage 3.5 (legal-optimized) |
| Backend | FastAPI |
| Frontend | React + Vite |

## Data Sources

18 Pakistani legal sources mapped. Currently implemented:
- **CommonLII** — 2,906 Supreme Court cases (2002+)
- **HuggingFace** — 1,414 SC judgments (pre-vectorized)
- **Kaggle** — 20,809 SC judgment texts (2007-2024)

Planned: Lahore HC, Sindh HC, Islamabad HC, Peshawar HC, Balochistan HC, Federal Shariat Court, Pakistan Code, National/Provincial Assemblies.

## Project Structure

```
src/
├── pipelines/commonlii/          # Court website crawlers
├── extractors/
│   ├── common/                   # Shared LLM client, JSON utils
│   └── criminal/                 # 4-pass criminal extraction
│       ├── tier_a.py             # Regex/NER
│       ├── tier_b.py             # LLM classification (65 fields)
│       ├── tier_c.py             # LLM reasoning (17 fields)
│       ├── reasoning_points.py   # Atomic decomposition
│       ├── reasoning_schema.py   # Pydantic models
│       ├── schema.py             # TierA/B/C + ExtractionResult
│       ├── pipeline.py           # Orchestrator
│       └── chunker.py            # SAC chunking
├── qdrant/
│   ├── collections.py            # Schema + indexes
│   ├── embeddings.py             # Voyage 3.5
│   ├── ingestion.py              # Multi-point upsert
│   ├── point_id.py               # Deterministic UUIDs
│   └── search.py                 # Hybrid search
tests/                            # 99 tests passing
research/                         # Legal source research
```

## Setup

```bash
# Clone
git clone https://github.com/umerkhan95/qanoon-ai.git
cd qanoon-ai

# Install dependencies
pip install -r requirements.txt

# Environment variables
export OPENAI_API_KEY=sk-xxx
export QDRANT_URL=http://localhost:6333
export QDRANT_API_KEY=xxx

# Run tests
pytest tests/ -v

# Run extraction on a judgment
python -c "
from src.extractors.criminal.pipeline import extract_criminal_judgment
result = extract_criminal_judgment(open('judgment.txt').read())
print(result.field_coverage())
"
```

## License

MIT
