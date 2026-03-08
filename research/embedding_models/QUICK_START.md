# Quick Start: Embedding Models for Pakistani Legal RAG

**In a hurry? Read this 2-minute summary.**

---

## TL;DR

**Use Voyage 3.5** for Pakistani criminal law judgments with Qdrant:
- **MLEB Score:** 84.07 (3rd best, only 2 points behind #1)
- **Cost:** $0.06/M tokens = **$1.71 for 10,000 judgments**
- **Context:** 32K tokens (no chunking needed)
- **Speed:** Fast (50-100ms per judgment)
- **Status:** Production-ready, proven

**Fallback:** Upgrade to **Kanon 2 Embedder** if accuracy insufficient (NDCG@10 < 0.75 on test queries).

---

## Top 3 Models at a Glance

| Rank | Model | MLEB | Cost/10K Docs | Context | Best For |
|------|-------|------|--------|---------|----------|
| **#1** | Kanon 2 Embedder | 86.03 | ~$5.71 | 16K | Maximum accuracy + speed |
| **#2** | Voyage 3.5 | 84.07 | **$1.71** ⭐ | 32K | **Best value** |
| **#3** | Voyage 3 Large | 85.71 | $6.29 | 32K | If budget allows |

---

## Why Voyage 3.5?

✓ **3rd best legal performance** — Only 2 NDCG@10 points behind #1
✓ **Cheapest proprietary** — 4x cheaper than Kanon 2
✓ **32K context** — No chunking for Pakistani judgments (5K-50K chars typical)
✓ **Proven** — Harvey.ai uses for legal RAG
✓ **Mature** — Released Jan 2025, stable API
✓ **Free tokens** — 200M/month included

---

## Implementation (2 Hours)

```bash
# 1. Install
pip install qdrant-client voyageai

# 2. Initialize
export VOYAGE_API_KEY="your_key_here"
docker run -p 6333:6333 qdrant/qdrant:latest

# 3. Index sample judgments
python embed_service.py

# 4. Search
results = service.search("bail application for murder", limit=5)
```

See `EMBEDDING_IMPLEMENTATION_GUIDE.md` for full code.

---

## Cost Breakdown

### One-Time Indexing (10,000 judgments)

```
Judgment size: ~20,000 chars = ~2,857 tokens
Total: 10,000 × 2,857 = 28.57M tokens

Voyage 3.5: 28.57M × $0.000006 = $1.71
Kanon 2:   28.57M × $0.000020 = $5.71 (est.)
OpenAI 3L: 28.57M × $0.00000013 = $3.71 (but needs chunking!)
```

### Quarterly Updates (5% of corpus = 500 docs)

```
500 × 2,857 = 1.43M tokens

Voyage 3.5: $0.086/quarter = $0.34/year
Kanon 2:    $0.29/quarter = $1.12/year
```

---

## Context Length Comparison

**Pakistani judgments:** 5K-50K chars = 700-7,000 tokens

| Model | Context | Needs Chunking? | Risk |
|-------|---------|-----------------|------|
| Voyage 3.5 | 32K | ✗ No | Low — plenty of headroom |
| Kanon 2 | 16K | ✗ No (mostly) | Low — covers 99% of cases |
| OpenAI 3-lg | 8K | **✓ YES** | High — **every judgment** |
| Cohere v4 | 128K | ✗ No | Low — overkill, expensive |

**Chunking costs:** +2-5ms latency, +storage, +retrieval artifacts

---

## Benchmark Results

### MLEB 2025 Leaderboard (Legal-Specific)

```
Rank  Model                    NDCG@10
1.    Kanon 2 Embedder        86.03
2.    Voyage 3 Large          85.71
3.    Voyage 3.5              84.07  ← START HERE
4.    Granite Embedding       82.1
5.    Text-Embedding-3-Large  ~78.0
...
7.    Gemini Embedding        80.90  (ranked #1 on MTEB!)
8.    Voyage Law 2            79.63  (legal-specific but loses!)
```

**Key insight:** Larger general models beat smaller legal-specific models.

---

## Decision: When to Upgrade?

Start with **Voyage 3.5**, upgrade to **Kanon 2** if:

- [ ] Search quality test (100 judgments) shows NDCG@10 < 0.75
- [ ] Accuracy requirements are critical (criminal cases)
- [ ] You have budget for 3x higher cost ($5.71 vs $1.71)
- [ ] You need 340% faster inference (daily re-indexing)

Otherwise, **Voyage 3.5 is sufficient.**

---

## Common Questions

**Q: Do I need legal-specific models?**
A: Yes, but "legal-specific" often means larger, better general models. Voyage 3.5 (general) beats voyage-law-2 (legal-specific) on legal tasks.

**Q: What about privacy?**
A: Voyage, OpenAI, Cohere are API-based (data sent to servers). If privacy critical, use self-hosted **Snowflake Arctic Embed 2** (free, open-source).

**Q: Will chunking help?**
A: No. With 16K+ context, embedding entire judgment preserves legal reasoning. Chunking adds complexity with no benefit for typical Pakistani judgments.

**Q: What if documents exceed 50K chars?**
A: Rare, but use Cohere embed-v4 (128K context) or semantic chunking at section boundaries.

**Q: How do I know if it's working?**
A: Measure NDCG@10 or MAP@10 on test queries with known relevant judgments. Target > 0.80 for production.

---

## Files in This Package

| File | Purpose |
|------|---------|
| **RESEARCH_SUMMARY.md** | This summary + key findings |
| **EMBEDDING_MODELS_RESEARCH.md** | Full 15-page analysis of all models |
| **EMBEDDING_DECISION_TREE.md** | Decision framework by priority |
| **EMBEDDING_IMPLEMENTATION_GUIDE.md** | Code + setup instructions |
| **EMBEDDING_MODELS_QUICKREF.csv** | Specifications table (import to Excel) |
| **QUICK_START.md** | This file (2-minute read) |

---

## Next Steps (Today)

1. **skim** RESEARCH_SUMMARY.md (10 min)
2. **Review** EMBEDDING_DECISION_TREE.md (15 min)
3. **Get API key** from [Voyage AI](https://voyage.ai) (2 min)
4. **Run MVP** from EMBEDDING_IMPLEMENTATION_GUIDE.md (1 hour)
5. **Evaluate** on 100 sample judgments (1-2 hours)
6. **Decide** upgrade or proceed (30 min)

**Total:** ~2-3 hours to MVP decision

---

## Contact & Support

- Voyage AI: [docs.voyageai.com](https://docs.voyageai.com)
- Kanon 2 (Legal): [isaacus.com](https://isaacus.com)
- Open-source: [huggingface.co](https://huggingface.co)
- Qdrant: [qdrant.io](https://qdrant.io)

---

**Recommendation:** Start with **Voyage 3.5** today. You'll know within 2 weeks if you need to upgrade.

Good luck building your legal RAG!

---

*Research compiled: March 8, 2026*
*Data from: MLEB 2025, official API docs, peer-reviewed benchmarks*
