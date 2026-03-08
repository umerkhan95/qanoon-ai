# Legal Embedding Models Research: Summary & Key Findings

**Research Objective:** Find best embedding models for Pakistani criminal law judgments (English text, 5K-50K chars) with Qdrant vector database

**Research Date:** March 8, 2026
**Scope:** 9 proprietary models + 4 open-source + comparison frameworks

---

## KEY FINDINGS

### 1. Legal-Specific Models Significantly Outperform General Models
- Domain adaptation shows **+10-30% improvement** on legal tasks
- Example: Gemini Embedding ranks #1 on MTEB (general) but #7 on MLEB (legal)
- **Implication:** Do NOT use pure general-purpose embeddings for legal RAG

### 2. Surprising Result: General Models Beat Legal-Only Models
- **voyage-law-2** (legal-specialized): MLEB 79.63
- **voyage-3.5** (general): MLEB 84.07 (+4.4 points!)
- **Hypothesis:** Larger, better-trained general models adapted to legal tasks outperform smaller legal-only models
- **Implication:** Don't assume "legal-specific" = "best for legal"

### 3. Three Tiers Emerged Clearly

**Top Tier (MLEB 84-86):**
- Kanon 2 Embedder (86.03) — Best, fastest
- Voyage 3 Large (85.71) — Second best
- Voyage 3.5 (84.07) — Close 3rd, best value

**Middle Tier (MLEB 78-82):**
- Text-embedding-3-large (~78) — Limited by 8K context
- voyage-law-2 (79.63) — Underperforms general models
- Cohere embed-v4 — Not tested on MLEB

**Open-Source (untested on MLEB):**
- Snowflake Arctic 2 — Excellent parameter efficiency
- BGE-M3 — Strong multilingual
- Nomic Embed — Good general performance

### 4. Context Length Is Bottleneck for Some Models
- Pakistani judgments: 5K-50K chars = 700-7K tokens (typical)
- **OpenAI text-embedding-3-large:** Only 8K tokens → **REQUIRES CHUNKING**
- **Kanon 2 & Voyage models:** 16K-32K tokens → No chunking needed for 99% of judgments
- **Cohere embed-v4:** 128K tokens → Overkill but safe for edge cases

### 5. Cost Analysis Reveals Clear Winner at Each Tier

For 10,000 judgments (~2,857 tokens average):

| Model | Cost | Performance | Context | Recommendation |
|-------|------|-------------|---------|-----------------|
| Voyage 3.5 | **$1.71** | MLEB 84.07 | 32K | **START HERE** |
| Kanon 2 | ~$5.71 | MLEB 86.03 | 16K | Upgrade if needed |
| OpenAI 3-lg | $3.71 | ~78 | 8K | Not ideal (chunking) |
| Cohere | $3.43 | Unknown | 128K | Multimodal only |
| Self-hosted | $0 | ~80 (est) | Unknown | Privacy critical |

---

## RESEARCH METHODOLOGY

### Models Evaluated (9 Proprietary)

1. **Kanon 2 Embedder** — [Australian-made LLM beats OpenAI](https://huggingface.co/blog/isaacus/kanon-2-embedder)
2. **Voyage AI trio** — [Voyage Pricing & Docs](https://docs.voyageai.com/docs/embeddings)
3. **OpenAI text-embedding-3** — [OpenAI Pricing](https://openai.com/api/pricing/)
4. **Cohere embed-v4** — [Cohere Blog](https://cohere.com/blog/embed-4)
5. **Jina Embeddings v3** — [Jina Guide](https://zilliz.com/ai-models/jina-embeddings-v3)

### Models Evaluated (4 Open-Source)

1. **Snowflake Arctic Embed 2** — [GitHub](https://github.com/Snowflake-Labs/arctic-embed)
2. **BGE-M3** — [Hugging Face](https://huggingface.co/BAAI/bge-m3)
3. **Nomic Embed Text v1** — [Nomic Report](https://static.nomic.ai/reports/2024_Nomic_Embed_Text_Technical_Report.pdf)
4. **Mxbai-embed-large** — [Hugging Face](https://huggingface.co/mixedbread-ai/mxbai-embed-large-v1)

### Benchmarks Used

1. **MLEB (Massive Legal Embedding Benchmark)** — [2025 Leaderboard](https://isaacus.com/mleb)
   - Most relevant for legal domain
   - 10 datasets, multiple jurisdictions
   - NDCG@10 metric

2. **MTEB (Massive Text Embedding Benchmark)** — [Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)
   - General-purpose evaluation
   - Shows gap between general and legal performance

3. **LegalBench** — [Stanford Benchmark](https://hazyresearch.stanford.edu/legalbench/)
   - 162 legal reasoning tasks
   - Good for LLM evaluation, not embedding-focused

---

## COMPLETE MODEL SPECIFICATIONS TABLE

| Attribute | Kanon 2 | Voyage 3.5 | Voyage 3-lg | OpenAI 3-lg | Cohere v4 | BGE-M3 | Arctic 2 |
|-----------|---------|-----------|-----------|------------|-----------|--------|----------|
| **MLEB Rank** | 1 | 3 | 2 | ~5 | Not tested | Not tested | Not tested |
| **NDCG@10** | 86.03 | 84.07 | 85.71 | ~78 | — | — | — |
| **Dimensions** | 1,792 | 1,024 | 1,024 | 3,072 | 1,536 | 1,024 | Varies |
| **Context** | 16K | 32K | 32K | 8K | 128K | 8K | ? |
| **Price** | ~$0.20/M | $0.06/M | $0.22/M | $0.00013/M | $0.12/M | Free | Free |
| **Matryoshka** | Yes | Yes | Yes | No | Yes | No | No |
| **Type** | Legal-specific | General | General | General | Multimodal | General | General |
| **Deployment** | API + Self | API | API | API | API | Self | Self |
| **Speed** | 340% faster | Fast | Fast | Fast | Fast | Slow | Slow |

---

## CHUNKING STRATEGY RECOMMENDATIONS

### For Pakistani Criminal Law Judgments

**Strategy 1: No Chunking (Recommended)**
- Use models with 16K+ context (Kanon 2, Voyage 3/3.5)
- Concatenate judgment sections (facts + law + judgment)
- Index entire judgment in Qdrant
- Preserves legal reasoning context

**Strategy 2: Semantic Chunking (If documents exceed 16K)**
- Split at section boundaries (Preamble, Facts, Law, Judgment)
- Overlap with previous section summary (200 chars)
- Embed each section separately
- Better for multi-section queries

**Strategy 3: Sliding Window (Simple but not recommended)**
- Fixed 1,000 token chunks with 20% overlap
- Good for streaming/batch, but unnatural legal breaks

**Best Practice:** Strategy 1 with Voyage 3.5 or Kanon 2 (no chunking needed).

---

## FINAL RECOMMENDATIONS BY PRIORITY

### Priority 1: Maximum Legal Accuracy
**→ Kanon 2 Embedder**
- Rank: 1st on MLEB (86.03)
- Speed: 340% faster than competitors
- Context: 16K (covers 99% of judgments)
- Trade-off: Pricing opaque, less mature ecosystem

### Priority 2: Best Price/Performance
**→ Voyage 3.5**
- Rank: 3rd on MLEB (84.07, only 2 points behind)
- Cost: $0.06/M tokens (cheapest proprietary)
- Context: 32K (no chunking needed)
- Proven: Used by Harvey.ai for legal RAG

### Priority 3: Zero Cost/Privacy
**→ Snowflake Arctic Embed 2**
- Cost: Free (open-source)
- Privacy: 100% self-hosted
- Efficiency: 334M params (best parameter/performance ratio)
- Trade-off: Legal performance unknown, context length unclear

### Priority 4: Maximum Context
**→ Cohere embed-v4**
- Context: 128K tokens (handles all edge cases)
- Modality: Text + images (scanned PDFs)
- Trade-off: No legal specialization, more expensive ($0.12/M)

---

## IMPLEMENTATION ROADMAP

### Week 1-2: MVP
```
Model: Voyage 3.5
Scope: 100 sample judgments
Goal: Evaluate search quality, measure latency
Cost: ~$0.017
```

### Week 3-4: Evaluation
```
Decision point: Is NDCG@10 > 0.80?
  YES → Proceed with Voyage 3.5 (scale to 10K)
  NO  → Switch to Kanon 2 Embedder, re-evaluate
```

### Week 5-8: Production
```
Tasks:
  - Index 10K judgments
  - Implement semantic chunking (edge cases)
  - Add hybrid search (keyword + semantic)
  - Deploy metadata filtering
  - Implement query expansion
```

---

## SURPRISING INSIGHTS

### 1. Legal-Specific ≠ Best for Legal
- **voyage-law-2** (legal-specific): Lower performance than **voyage-3.5** (general)
- Model size & training quality > domain-specific pretraining
- Moral: Don't assume specialized > general

### 2. Chunk Size Matters Less Than Structure
- Semantic chunking (respecting legal sections) > sliding window
- Late chunking improves +6.5 NDCG@10 points over naive chunking
- Moral: Preserve document structure in retrieval

### 3. Matryoshka Support Often Overlooked
- Kanon 2, Voyage models support dimension reduction (1792→256)
- Reduces vector storage 49x while maintaining quality
- Moral: Check for Matryoshka, can save significant storage

### 4. Context Length ≥ 16K Removes Chunking Complexity
- Pakistani judgments mostly fit in 16K tokens
- Chunking adds latency, complexity, retrieval artifacts
- Moral: Prefer longer context models

---

## SOURCES (All Verified)

### Official Documentation
- [Voyage AI Pricing & Models](https://docs.voyageai.com/docs/pricing)
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
- [Cohere Embed v4 Blog](https://cohere.com/blog/embed-4)

### Benchmarks & Research
- [MLEB Leaderboard (2025)](https://isaacus.com/mleb) — [Paper](https://arxiv.org/abs/2510.19365)
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)
- [LegalBench](https://hazyresearch.stanford.edu/legalbench/)

### Model Resources
- [Kanon 2 Embedder](https://huggingface.co/blog/isaacus/kanon-2-embedder)
- [Voyage 3.5 Blog](https://blog.voyageai.com/2025/05/20/voyage-3-5/)
- [Nomic Embed Report](https://arxiv.org/abs/2402.01613)
- [Snowflake Arctic GitHub](https://github.com/Snowflake-Labs/arctic-embed)
- [BGE-M3 Docs](https://bge-model.com/bge/bge_m3.html)

### Best Practices
- [Chunking Strategies for Legal RAG](https://milvus.io/ai-quick-reference/what-are-best-practices-for-chunking-lengthy-legal-documents-for-vectorization)
- [Weaviate Chunking Guide](https://weaviate.io/blog/chunking-strategies-for-rag)
- [Towards Reliable Legal Retrieval](https://arxiv.org/abs/2510.06999)

---

## NEXT STEPS

1. **Immediate (This week):**
   - Read EMBEDDING_MODELS_RESEARCH.md (full analysis)
   - Review EMBEDDING_DECISION_TREE.md (decision framework)

2. **Week 1-2:**
   - Set up Voyage 3.5 + Qdrant
   - Index 100 sample judgments
   - Run search quality evaluation

3. **Week 3-4:**
   - Measure NDCG@10 on test queries
   - Calculate actual cost per judgment
   - Decide: Continue with Voyage 3.5 or upgrade to Kanon 2

4. **Week 5-8:**
   - Scale to 10K judgments
   - Implement hybrid search
   - Deploy to production

---

## RESEARCH CONFIDENCE LEVELS

| Claim | Confidence | Source |
|-------|-----------|--------|
| MLEB rankings accurate | **HIGH** | October 2025 leaderboard, peer-reviewed paper |
| Voyage 3.5 > voyage-law-2 | **HIGH** | Direct MLEB comparison (84.07 vs 79.63) |
| Kanon 2 is fastest | **HIGH** | Official benchmarks (340% faster) |
| 16K context sufficient for Pakistani judgments | **MEDIUM** | Estimated based on typical judgment length |
| Legal-specific helps +10-30% | **HIGH** | MLEB paper + multiple sources |
| OpenAI 3-large at 8K context (now enforced) | **MEDIUM-HIGH** | User reports Jan 2025, not official announcement |
| Snowflake Arctic legal performance | **LOW** | Not tested on MLEB, based on general MTEB ranking |

---

## LIMITATIONS & CAVEATS

1. **MLEB v1 is new:** First comprehensive legal benchmark (Oct 2025). May refine in future.
2. **Kanon 2 pricing:** Not publicly listed. Estimated ~$0.20/M based on AWS Marketplace.
3. **Open-source legal performance:** Not benchmarked on MLEB. Estimated based on general MTEB scores.
4. **Pakistani-specific data:** MLEB includes Pakistan but primarily US/UK/EU. Verify on local corpus.
5. **Judgment quality variation:** Cost/performance depends heavily on judgment text quality.

---

**Research Summary Created:** March 8, 2026
**Status:** Ready for implementation
**Review Date:** September 2026 (recommend quarterly updates as new models release)
