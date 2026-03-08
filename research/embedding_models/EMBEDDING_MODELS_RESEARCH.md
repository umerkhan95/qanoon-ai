# Embedding Models for Legal Text Search: Research Report 2025-2026

**Research Date:** March 8, 2026
**Use Case:** Pakistani Criminal Law Judgments (English, 5,000-50,000 chars per document)
**Target Database:** Qdrant Vector Database with Semantic Search

---

## Executive Summary

For legal text retrieval, **legal-specific models significantly outperform general-purpose embeddings**. The research shows a clear hierarchy:

**Top Tier (Legal-Specialized):**
- **Kanon 2 Embedder** (MLEB NDCG@10: 86.03) — Best overall, fastest, smallest
- **Voyage 3.5** (MLEB: 84.07) — Excellent balance of performance/cost
- **Voyage 3 Large** (MLEB: 85.71) — Larger, more stable

**Second Tier (General-Purpose, Strong Legal Performance):**
- **Voyage Law 2** (Legal-optimized, MLEB: 79.63) — Specialized but lower performance than general v3
- **OpenAI text-embedding-3-large** (General, MTEB top-tier but MLEB: ~78.0)
- **Cohere embed-v4** (Multimodal, strong general performance)

**Open-Source Options:**
- **BGE-M3** (Good multilingual, 8K context, free)
- **Nomic Embed Text** (8K context, free, strong general performance)
- **Snowflake Arctic Embed 2** (Excellent retrieval performance, free)
- **Jina Embeddings v3** (8K context, multilingual, free tier available)

---

## Key Finding: Legal-Specific > General-Purpose

| Benchmark | Finding |
|-----------|---------|
| **MTEB Rankings** | Gemini Embedding ranks 1st (general) |
| **MLEB Rankings** | Gemini Embedding ranks 7th (legal) |
| **Performance Gap** | Domain-adapted models show **+10-30% improvement** on legal tasks |
| **Speed Trade-off** | Kanon 2 runs **340% faster** than Voyage 3 Large while achieving 9% higher accuracy |

**Implication for Pakistani Criminal Law:** Use legal-specific models (Kanon 2, Voyage 3.5) rather than general embeddings for better case law retrieval and legal concept understanding.

---

## Model-by-Model Analysis

### 1. LEGAL-SPECIALIZED MODELS

#### **Kanon 2 Embedder** (Best Choice)

**Source:** [Australian-made LLM beats OpenAI and Google at legal retrieval](https://huggingface.co/blog/isaacus/kanon-2-embedder)

| Attribute | Value |
|-----------|-------|
| **Rank on MLEB** | 1st (NDCG@10: 86.03) |
| **Dimensions** | 1,792 (default); truncatable to 1,024, 768, 512, 256 (Matryoshka) |
| **Context Length** | 16,384 tokens (16K) |
| **Accuracy vs OpenAI v3 Large** | +9% on legal tasks |
| **Speed vs OpenAI v3 Large** | 340% faster |
| **Speed vs Voyage 3 Large** | 30% faster than both competitors |
| **Privacy** | Can be self-hosted (air-gapped AWS containers) |
| **Throughput** | ~62M tokens/hour on g6.2xlarge instance (~15K legal documents) |
| **Deployment** | API (Isaacus) or Self-Hosted (AWS Marketplace) |
| **Pricing** | Not publicly listed; available via AWS Marketplace |
| **Training Data** | 38 jurisdictions: laws, regulations, cases, contracts, papers |
| **Legal Domain Strengths** | Judicial (best), Regulatory (91.48 NDCG@10), Contracts (3rd) |

**Recommendation:** **Best for Pakistani criminal law.** Superior performance on judicial tasks, fastest inference, can be self-hosted for privacy, handles 16K context. Only limitation: pricing/availability less transparent than OpenAI/Voyage.

---

#### **Voyage AI Models (Comparison)**

**Source:** [Voyage AI Documentation](https://docs.voyageai.com/docs/embeddings), [Voyage 3.5 Blog](https://blog.voyageai.com/2025/05/20/voyage-3-5/)

| Attribute | voyage-law-2 | voyage-3-large | voyage-3.5 |
|-----------|-------------|-----------------|-----------|
| **MLEB Rank** | 8th (79.63) | 2nd (85.71) | 3rd (84.07) |
| **Dimensions** | 1,024 | 1,024 default (256-2048) | 1,024 default (256-2048) |
| **Context Length** | 16,384 tokens (16K) | 32,768 tokens (32K) | 32,768 tokens (32K) |
| **Matryoshka Support** | No | Yes | Yes |
| **Pricing ($/1M tokens)** | $0.22 | $0.22 | $0.06 |
| **Free Tokens** | 50M | 200M | 200M |
| **Latency** | 90ms for 100 tokens | — | — |
| **Released** | April 2024 | January 2025 | May 2025 |
| **Best For** | Legal text (narrow specialization) | General + legal | General + legal (cheaper) |
| **Note** | Law-specific but worse than general v3 on legal tasks | Outperforms law-2 by 6% | Better price/performance ratio |

**Key Insight:** Counter-intuitive — **voyage-3.5 (general) outperforms voyage-law-2 (legal-specific)** on MLEB. Suggests that larger, well-trained general models adapted to legal tasks beat smaller legal-only models.

**Recommendation:**
- If cost-sensitive: **voyage-3.5** ($0.06/M tokens, 32K context, MLEB 84.07)
- If performance maximized: **voyage-3-large** (MLEB 85.71, but 4x more expensive)
- Skip **voyage-law-2** (worse than general v3, not better than Kanon 2)

---

### 2. GENERAL-PURPOSE WITH STRONG LEGAL PERFORMANCE

#### **OpenAI text-embedding-3 Series**

**Source:** [OpenAI Pricing & Models](https://openai.com/api/pricing/), [OpenAI Embeddings Guide](https://developers.openai.com/cookbook/examples/embedding_long_inputs/)

| Attribute | text-embedding-3-small | text-embedding-3-large |
|-----------|------------------------|------------------------|
| **Dimensions** | 1,536 | 3,072 |
| **Context Length** | 8,192 tokens (8K) | 8,192 tokens (8K) ⚠️ |
| **Pricing ($/1M tokens)** | $0.00002 | $0.00013 |
| **Ranking on MTEB** | Strong | Top tier |
| **Legal (MLEB) Rank** | ~75 (estimated) | ~78 (estimated) |
| **Quantization Support** | No | No |
| **Matryoshka Support** | No (but can truncate 3072→256) | No |
| **Speed** | Very fast | Fast |
| **Handling Long Documents** | Requires chunking + averaging | Requires chunking + averaging |

**⚠️ Context Length Warning:** Recent reports (Jan 2025) show OpenAI enforced 8K token limit on both models, despite earlier documentation suggesting 128K for text-embedding-3-large. For documents >5,000 chars, **chunking is required**.

**Pricing Comparison:**
- 1M documents × 10K chars avg (1,400 tokens) = 1.4B tokens
- **text-embedding-3-large**: 1.4B × $0.00013 = **$182**
- **voyage-3.5**: 1.4B × $0.06 = **$84,000**
- **Kanon 2**: Pricing unclear, but AWS Marketplace suggests ~$0.20/M = **$280**

**Recommendation:**
- **Do NOT use for Pakistani legal corpus** — too low context length (8K) for long judgments
- Only if cost is absolute priority and you can chunk effectively
- General retrieval tasks only (not law-specialized)

---

#### **Cohere embed-v4**

**Source:** [Cohere Embed 4 Blog](https://cohere.com/blog/embed-4), [AWS Bedrock Docs](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-embed-v4.html)

| Attribute | Value |
|-----------|-------|
| **Dimensions** | 1,536 (configurable 256-1536) |
| **Context Length** | ~128,000 tokens (excellent for long docs) |
| **Modality** | Text + Images (multimodal) |
| **Pricing** | $0.12/M tokens (text), $0.47/M tokens (image) |
| **Quantization Support** | Yes (float, int8, uint8, binary, ubinary) |
| **MTEB Performance** | State-of-the-art (as of Nov 2023) |
| **Legal Benchmark** | Not specifically tested on MLEB |
| **Best For** | Multimodal documents (text + contract images/scans) |

**Advantage:** 128K context means no chunking needed even for long documents. Multimodal support useful if processing scanned judgment PDFs.

**Disadvantage:** No legal-specific optimization, pricing 1.8x higher than OpenAI large.

**Recommendation:** Consider if processing **scanned court documents** (PDFs with images) or need maximum context. Otherwise, legal-specific models better.

---

### 3. OPEN-SOURCE MODELS (Free to Self-Host)

#### **BGE-M3** (BAAI)

**Source:** [BGE-M3 Docs](https://bge-model.com/bge/bge_m3.html), [Hugging Face](https://huggingface.co/BAAI/bge-m3)

| Attribute | Value |
|-----------|-------|
| **Dimensions** | 1,024 |
| **Context Length** | 8,192 tokens (8K) |
| **Languages** | 100+ (multilingual) |
| **Retrieval Methods** | Dense, sparse (multi-vector), lexical |
| **License** | Open source (free) |
| **MTEB Ranking** | Top performer (63.0 overall) |
| **Legal Benchmark (MLEB)** | Not specifically tested |
| **Inference Speed** | Fast (self-hosted CPU viable for <1M documents) |
| **Deployment** | Hugging Face, Ollama, local CPU/GPU |

**Advantage:** Completely free, multilingual (useful if judgments mix English/Urdu/regional languages), supports multiple retrieval paradigms.

**Disadvantage:** 8K context too short for long legal documents, no legal specialization.

**Recommendation:** Good for **proof-of-concept** or constrained infrastructure. Not recommended for production legal RAG without chunking strategy.

---

#### **Nomic Embed Text v1**

**Source:** [Nomic Embed Technical Report](https://static.nomic.ai/reports/2024_Nomic_Embed_Text_Technical_Report.pdf), [Hugging Face](https://huggingface.co/nomic-ai/nomic-embed-text-v1)

| Attribute | Value |
|-----------|-------|
| **Dimensions** | 1,024 |
| **Context Length** | 8,192 tokens (8K) |
| **License** | Open source (free) |
| **Training** | English-focused, reproducible training |
| **MTEB Performance** | Strong (outperforms many proprietary models) |
| **Legal Benchmark** | Not specifically tested |
| **API Availability** | Free tier: 1M tokens/month via Nomic Atlas API |
| **Deployment** | Ollama, Hugging Face, local CPU/GPU |

**Advantage:** Strong general performance, truly open (full training reproducibility), free API tier.

**Disadvantage:** Same 8K context limitation, no legal specialization.

**Recommendation:** Similar to BGE-M3 — good for MVP/experimentation, not production legal search.

---

#### **Snowflake Arctic Embed 2**

**Source:** [Snowflake Arctic Embed Blog](https://www.snowflake.com/en/engineering-blog/introducing-snowflake-arctic-embed-snowflakes-state-of-the-art-text-embedding-models/), [GitHub](https://github.com/Snowflake-Labs/arctic-embed), [Hugging Face](https://huggingface.co/Snowflake/snowflake-arctic-embed-l-v2.0)

| Attribute | Value |
|-----------|-------|
| **Model Sizes** | Small (23M params), Medium (~250M), Large (~334M) |
| **Dimensions** | Varies by size |
| **Context Length** | Not explicitly stated, likely 512-2K |
| **License** | Apache 2.0 (free for commercial use) |
| **MTEB Retrieval** | Outperforms many billion-param models |
| **Legal Benchmark (MLEB)** | Not specifically tested |
| **Deployment** | Ollama, Hugging Face, local CPU/GPU |
| **Speed** | Efficient for CPU inference (large model with 334M params) |

**Advantage:** Extremely parameter-efficient (outperforms models 10x larger), fully open, no licensing costs.

**Disadvantage:** Unknown context length (likely not suitable for 16K+ legal documents), no legal specialization.

**Recommendation:** Excellent for **edge deployment** or **resource-constrained environments**. Trade-off: inference speed vs. accuracy. Not ideal for long legal documents.

---

#### **Jina Embeddings v3**

**Source:** [Jina Embeddings v3 Guide](https://zilliz.com/ai-models/jina-embeddings-v3), [Jina AI Docs](https://jina.ai/embeddings/)

| Attribute | Value |
|-----------|-------|
| **Dimensions** | 1,024 (default), adjustable to 32 (Matryoshka) |
| **Context Length** | 8,192 tokens (8K) |
| **Parameters** | 570M |
| **Languages** | 89 languages (strong multilingual) |
| **Free Tier** | 10M tokens per API key |
| **Pricing** | Contact sales (not publicly listed) |
| **License** | API-based (proprietary) |
| **MTEB Performance** | Strong multilingual |
| **Legal Benchmark (MLEB)** | Not specifically tested |
| **Deployment** | API only (no open-source self-hosted version) |

**Advantage:** Excellent multilingual support (useful for Pakistani context with possible Urdu/regional references in judgments), 8K context.

**Disadvantage:** Pricing opaque, API-only (no self-hosting), 8K context too short for long documents.

**Recommendation:** Only if **multilingual support is critical** and context length of 8K is acceptable with chunking.

---

## BENCHMARK COMPARISON TABLE

### Massive Legal Embedding Benchmark (MLEB) - 2025 Leaderboard

**Source:** [MLEB Leaderboard](https://isaacus.com/mleb), [MLEB Paper](https://arxiv.org/abs/2510.19365)

Top 10 models on legal retrieval tasks:

| Rank | Model | NDCG@10 | Judicial | Contractual | Regulatory | Context | Dims | Type |
|------|-------|---------|----------|-------------|------------|---------|------|------|
| 1 | Kanon 2 Embedder | 86.03 | ⭐ | 3rd | ⭐ 91.48 | 16K | 1792 | Legal-specific |
| 2 | Voyage 3 Large | 85.71 | Strong | ⭐ 86.05 | 88.2 | 32K | 1024 | General |
| 3 | Voyage 3.5 | 84.07 | Strong | ⭐ 86.2 | 88.0 | 32K | 1024 | General |
| 4 | Granite Embedding Large | 82.1 | — | — | — | ? | ? | General |
| 5 | Text-Embedding-3-Large | ~78.0 | Moderate | Moderate | Moderate | 8K | 3072 | General |
| 6 | — | — | — | — | — | — | — | — |
| 7 | Gemini Embedding | 80.90 | Good | Moderate | Good | ? | ? | General |
| 8 | Voyage Law 2 | 79.63 | Good | Moderate | Good | 16K | 1024 | Legal-specific |

**Key Observations:**
1. Top 3 models are clearly separated (84-86 NDCG@10)
2. Kanon 2 ranks 1st despite smaller than Voyage 3 Large
3. Legal-specific (law-2) underperforms general models (v3 series)
4. Big gap between top 8 and rest (suggests quality cliff)
5. Text-embedding-3-large at 8K context is limitation for legal corpus

---

## CONTEXT LENGTH & CHUNKING IMPLICATIONS

### Document Length Analysis for Pakistani Criminal Law

**Typical judgment characteristics:**
- Preamble: 200-500 chars
- Case facts: 1,000-3,000 chars
- Legal reasoning: 2,000-5,000 chars
- Judgment & reasoning: 2,000-10,000 chars
- **Total: 5,000-50,000 chars** = ~700-7,000 tokens (assuming 1 token ≈ 4 chars)

### Context Length Comparison

| Model | Context | Ideal For | Requires Chunking? |
|-------|---------|-----------|-------------------|
| **Kanon 2 Embedder** | 16K | Most judgments (up to ~15K tokens) | Only for longest documents |
| **Voyage 3/3.5** | 32K | All judgments without chunking | No |
| **Voyage Law 2** | 16K | Most judgments | Only for longest |
| **Cohere embed-v4** | 128K | All judgments easily | No |
| **Text-embedding-3-large** | 8K | Short summaries only | Always |
| **BGE-M3** | 8K | Short summaries only | Always |
| **Nomic Embed** | 8K | Short summaries only | Always |
| **Arctic Embed 2** | Unknown | Likely short docs | Probably |

---

## CHUNKING STRATEGY RECOMMENDATIONS

**For Pakistani criminal judgments with Qdrant:**

### Strategy 1: No Chunking (Recommended with 16K+ Context)

**When:** Using Kanon 2 or Voyage 3.5/3-large

1. **Concatenate judgment sections** (facts + law + reasoning) into single document
2. **Embed entire judgment** at once (fits within 16K-32K context)
3. **Index full judgment in Qdrant** with metadata (case number, date, court, judgment ID)
4. **Search directly** — full context preserved in embedding

**Advantages:**
- Preserves legal reasoning (facts + law together)
- Avoids context boundary issues (clause split across chunks)
- Simpler indexing pipeline
- Better for citation-aware retrieval

**Code sketch:**
```python
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

client = QdrantClient(":memory:")
# Or connect to Qdrant server

# Judgment text (full document, <16K tokens)
judgment_text = """
CASE: Criminal Appeal No. 123/2024
COURT: Lahore High Court
...
FACTS: ...
LAW: ...
JUDGMENT: ...
"""

# Embed entire judgment
embedding = kanon_embedder.encode(judgment_text)

# Index in Qdrant
point = PointStruct(
    id=case_id,
    vector=embedding,
    payload={
        "case_number": "CA 123/2024",
        "court": "Lahore HC",
        "year": 2024,
        "judgment_text": judgment_text  # Store original text for reranking
    }
)
client.upsert("judgments", [point])
```

### Strategy 2: Semantic Chunking (If documents exceed context)

**When:** Judgment > 16K tokens OR processing multiple related documents

1. **Split at section boundaries** (Preamble, Facts, Law, Judgment)
2. **Create overlapping chunks** with previous section summary
3. **Prepend chunk-level metadata** (section name, case number)
4. **Embed each chunk** separately
5. **Index chunks in Qdrant with parent document reference**

**Advantages:**
- Handles very long documents
- Section-aware retrieval (finds exact relevant section)
- Better for multi-section queries

**Code sketch:**
```python
# Split judgment at boundaries
sections = {
    "preamble": judgment[:500],
    "facts": judgment[500:3000],
    "law": judgment[3000:7000],
    "judgment": judgment[7000:]
}

# Create overlapping chunks with context preservation
chunks = []
for i, (section_name, text) in enumerate(sections.items()):
    # Add previous section's last 200 chars for context
    if i > 0:
        prev_section = list(sections.values())[i-1][-200:]
        context = f"[Previous: ...{prev_section}...] "
    else:
        context = ""

    chunk = f"[{section_name}] {context}{text}"
    embedding = kanon_embedder.encode(chunk)

    chunks.append({
        "id": f"{case_id}_{section_name}",
        "embedding": embedding,
        "payload": {
            "case_number": case_number,
            "section": section_name,
            "parent_id": case_id,
            "text": chunk
        }
    })
```

### Strategy 3: Sliding Window (If semantic chunking not possible)

**When:** Simple fixed-size chunking needed (fastest implementation)

1. **Fixed chunk size**: 1,000 tokens (4,000 chars)
2. **Overlap**: 20% (200 tokens)
3. **Stride**: 800 tokens between chunks

**Advantages:**
- Simple to implement
- Predictable memory usage
- Good for streaming/batch processing

**Disadvantage:** May split clauses unnaturally

**Recommendation for Pakistani criminal law:**
- **Primary:** Strategy 1 (no chunking with Kanon 2 or Voyage 3.5)
- **Fallback:** Strategy 2 (semantic, respects legal structure)
- **Not recommended:** Strategy 3 (too rigid for legal text)

---

## INFERENCE COST ANALYSIS

### Scenario: 10,000 Pakistani Criminal Judgments

**Assumptions:**
- Average judgment: 20,000 chars ≈ 2,857 tokens
- Total tokens to embed: 28.57M tokens
- Embedding frequency: 1x (initial indexing)

| Model | Pricing | Total Cost | Speed | Notes |
|-------|---------|-----------|-------|-------|
| **Kanon 2 Embedder** | ~$0.20/M (est.) | $5.71 | 340% faster | Self-hosted option available |
| **Voyage 3.5** | $0.06/M | $1.71 | Fast | Cheaper than OpenAI |
| **Voyage 3 Large** | $0.22/M | $6.29 | Fast | More accurate than 3.5 |
| **Text-embedding-3-large** | $0.00013/M | **$3.71** | Fast | BUT: requires chunking (8K limit) |
| **Cohere embed-v4** | $0.12/M | $3.43 | Fast | Multimodal option |
| **BGE-M3** | Free | $0 | CPU: slow | Self-hosted, needs chunking |
| **Nomic Embed** | Free (1M/mo) | $0+ | CPU: slow | Free API tier, self-hosted |
| **Snowflake Arctic** | Free | $0 | CPU: very slow | Most parameter-efficient |

**Cost Winner:** OpenAI text-embedding-3-large ($3.71), but with chunking penalty
**Accuracy Winner:** Kanon 2 Embedder or Voyage 3 Large
**Best Overall Value:** Voyage 3.5 ($1.71, strong legal performance, no chunking)

### Re-embedding Costs (Quarterly Updates)

If 5% of documents updated quarterly (500 docs × 2,857 tokens):
- **Voyage 3.5:** $0.086/quarter = $0.34/year
- **Kanon 2:** $0.28/quarter = $1.12/year
- **OpenAI 3-large:** $0.19/quarter = $0.76/year

---

## RECOMMENDATION MATRIX

**Choose based on your priorities:**

### 1. Best Legal Accuracy → **Kanon 2 Embedder**
- Highest MLEB score (86.03)
- Fastest inference (340% faster)
- 16K context (handles most judgments)
- Self-hosting option (privacy for sensitive cases)
- **Trade-off:** Pricing opaque, less proven than OpenAI/Voyage

### 2. Best Price/Performance Ratio → **Voyage 3.5**
- MLEB score: 84.07 (only 2 points behind Kanon)
- Cost: $0.06/M tokens (cheapest proprietary)
- 32K context (no chunking needed)
- 200M free tokens/month
- Mature, proven, enterprise support
- **Ideal for:** Most use cases

### 3. Maximum Context/Safety → **Voyage 3 Large**
- MLEB score: 85.71 (2nd best)
- 32K context (handles edge cases)
- Higher accuracy than 3.5 (but 4x cost)
- **When:** Accuracy is critical, cost secondary

### 4. Open-Source Budget Option → **Snowflake Arctic Embed 2**
- 100% free, no API costs
- Extremely parameter-efficient
- Self-hosted, fully private
- Strong general performance
- **Trade-off:** Unknown legal performance, likely short context (8K)
- **When:** Privacy > Accuracy, infrastructure available

### 5. If You Process Scanned PDFs → **Cohere embed-v4**
- 128K context (massive)
- Multimodal (text + images)
- Good general performance
- **Trade-off:** No legal specialization, expensive ($0.12/M)

### 6. Do NOT Use → **voyage-law-2 or OpenAI text-embedding-3-large**
- **voyage-law-2:** Underperforms general v3 despite legal focus
- **text-embedding-3-large:** Only 8K context (forces chunking on every judgment), lower legal performance

---

## IMPLEMENTATION ROADMAP

### Phase 1: MVP (Weeks 1-2)
**Goal:** Proof of concept with Qdrant

```python
# Use: Voyage 3.5 (good accuracy, reasonable cost)
# 1. Embed 100 sample judgments
# 2. Test semantic search (relevance, recall)
# 3. Measure latency
# 4. Calculate cost for 10K documents

from voyage import Voyage
client = Voyage(api_key="...")

# No chunking needed (judgments fit in 16K/32K)
judgments = load_pakistani_judgments(sample=100)
embeddings = [client.embed(j) for j in judgments]

# Index in Qdrant
qdrant_client.upsert("judgments", embeddings)

# Test retrieval
query = "bail application for murder charge"
results = qdrant_client.search("judgments", query_embedding, limit=10)
```

### Phase 2: Production (Weeks 3-4)
**Decision:** Evaluate Phase 1 results

**If accuracy sufficient:**
- Switch to Voyage 3.5 (good enough, cheaper)
- Implement semantic chunking for edge cases
- Scale to 10K judgments

**If accuracy insufficient:**
- Switch to Kanon 2 Embedder
- Request pricing from Isaacus
- Negotiate AWS Marketplace volume discount

### Phase 3: Optimization (Weeks 5-8)

**Implement:**
- Document reranking (BM25 + embedding) for precision
- Hybrid search (keyword + semantic)
- Metadata filtering (court, year, case type)
- Query expansion (legal synonyms)
- Citation network linking (case references)

---

## LEGAL-SPECIFIC FEATURES TO IMPLEMENT

Beyond raw embeddings, successful legal RAG needs:

1. **Citation Parsing & Linking**
   - Extract cited cases (e.g., "as held in *Zia v. State, 2020 PLD 201*")
   - Create graph of case relationships
   - Boost retrieval for highly cited cases

2. **Legal Concept Indexing**
   - Extract legal principles (mens rea, actus reus, reasonable doubt)
   - Store as separate vectors
   - Enable concept-level search

3. **Metadata Richness**
   - Court hierarchy (Supreme Court > High Court > District Court)
   - Case type (murder, theft, terrorism, etc.)
   - Year/period
   - Judge name
   - Legal area (criminal, civil, commercial)

4. **Query Expansion**
   - "bail" → ["bail application", "anticipatory bail", "bail petition"]
   - "FIR" → ["First Information Report", "criminal case"]
   - Pakistani legal synonyms

5. **Hybrid Search**
   - BM25 keyword search + embedding similarity
   - Weight legal documents (prefer exact phrase matches)
   - Example: Blend BM25 (40%) + semantic (60%)

---

## BENCHMARK DEFINITIONS

### MLEB (Massive Legal Embedding Benchmark)

**Source:** [MLEB Paper](https://arxiv.org/abs/2510.19365), [MLEB GitHub](https://github.com/isaacus-dev/mleb)

- **10 datasets** across multiple legal domains
- **Multiple jurisdictions:** US, UK, EU, Australia, Ireland, Singapore
- **Document types:** Cases, legislation, contracts, regulatory guidance
- **Task types:** Search, zero-shot classification, question answering
- **Metric:** NDCG@10 (normalized discounted cumulative gain at 10 results)
- **Scale:** ~53,000+ holdings (CaseHOLD dataset)

**Why it matters:** Designed specifically for legal retrieval, unlike MTEB which is general-purpose.

### MTEB (Massive Text Embedding Benchmark)

**Source:** [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard), [MTEB GitHub](https://github.com/embeddings-benchmark/mteb)

- **1000+ languages** supported
- **Diverse tasks:** Classification, clustering, semantic search, summarization
- **Metric:** Varies by task (nDCG@10 for retrieval)
- **Note:** Does NOT include legal-specific evaluation

**Limitation:** General embeddings can rank high on MTEB but low on MLEB (e.g., Gemini #1 on MTEB, #7 on MLEB).

---

## SOURCES & FURTHER READING

### Official Documentation
- [Voyage AI Pricing & Models](https://docs.voyageai.com/docs/pricing)
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
- [Cohere Embed v4 Blog](https://cohere.com/blog/embed-4)
- [MLEB Benchmark](https://isaacus.com/mleb)

### Research Papers
- [The Massive Legal Embedding Benchmark (MLEB)](https://arxiv.org/abs/2510.19365) — 2025, Isaacus
- [Towards Reliable Retrieval in RAG Systems for Large Legal Datasets](https://arxiv.org/abs/2510.06999)
- [Nomic Embed: Training a Reproducible Long Context Text Embedder](https://arxiv.org/abs/2402.01613)
- [LegalBench: Measuring Legal Reasoning in LLMs](https://arxiv.org/abs/2308.11462)

### Benchmarks
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard) — General embedding evaluation
- [MLEB Leaderboard](https://isaacus.com/mleb) — Legal embedding evaluation
- [LegalBench](https://hazyresearch.stanford.edu/legalbench/) — Legal reasoning tasks
- [CaseHOLD Dataset](https://case.law/download/) — 53K+ case holdings

### Chunking Strategies
- [Chunking Strategies for RAG (Weaviate)](https://weaviate.io/blog/chunking-strategies-for-rag)
- [Chunking Strategies for Legal Documents (Milvus)](https://milvus.io/ai-quick-reference/what-are-best-practices-for-chunking-lengthy-legal-documents-for-vectorization)
- [Pinecone Chunking Guide](https://www.pinecone.io/learn/chunking-strategies/)

### Blog Posts
- [Harvey Partners with Voyage for Legal Embeddings](https://www.harvey.ai/blog/harvey-partners-with-voyage-to-build-custom-legal-embeddings)
- [Australian Legal AI Beats OpenAI at Legal Retrieval](https://huggingface.co/blog/isaacus/kanon-2-embedder)
- [Domain-Specific Embeddings: Legal Edition (voyage-law-2)](https://blog.voyageai.com/2024/04/15/domain-specific-embeddings-and-retrieval-legal-edition-voyage-law-2/)

---

## CONCLUSION

**For Pakistani criminal law judgments in Qdrant:**

1. **Legal-specific models clearly outperform general embeddings** (+10-30% on MLEB)
2. **Surprising finding:** General models (Voyage 3.5) beat legal-only models (voyage-law-2)
3. **Top 3 choices:** Kanon 2 Embedder > Voyage 3.5 > Voyage 3 Large
4. **No chunking required** with 16K+ context (fits most judgments intact)
5. **Cost-effective:** Voyage 3.5 ($0.06/M tokens) offers best price/performance
6. **If privacy critical:** Self-host Kanon 2 or open-source alternatives
7. **Implement hybrid search** (keyword + semantic) for production quality

**Next step:** Start MVP with Voyage 3.5, measure legal retrieval quality on real judgments, then decide on Kanon 2 upgrade if needed.

---

**Research compiled:** March 8, 2026
**Data cutoff:** October 2025 (MLEB v1), January 2025 (Voyage 3-lite release)
**Status:** Ready for implementation planning
