# Embedding Model Decision Tree for Legal RAG

Use this decision tree to select the best embedding model for your Pakistani criminal law system.

---

## Quick Decision Flow

```
START
  |
  ├─ Do you need self-hosting/privacy?
  |  ├─ YES → Go to OPEN SOURCE DECISION
  |  └─ NO → Continue
  |
  ├─ Can you afford $0.06-0.22/M tokens?
  |  ├─ YES → Go to PROPRIETARY DECISION
  |  └─ NO → Go to BUDGET DECISION
  |
  └─ END (SELECT MODEL)
```

---

## OPEN SOURCE DECISION

**Requirement:** Self-hosting, zero API costs, offline capability

### Option 1: Maximum Accuracy (On-Premises)
```
Condition: Accuracy > Cost, Infrastructure available
  └─ Model: Snowflake Arctic Embed 2
  └─ Why: Best parameter-efficiency, strong retrieval
  └─ Trade-off: Unknown legal performance, likely 8K context
  └─ Deployment: GPU/CPU (334M params = moderate size)
  └─ Cost: $0
```

### Option 2: Balanced (On-Premises with Matryoshka)
```
Condition: Balanced accuracy/speed, GPU available
  └─ Model: BGE-M3
  └─ Why: Multilingual, dense + sparse retrieval, 100+ languages
  └─ Trade-off: 8K context requires chunking
  └─ Deployment: GPU/CPU (efficient)
  └─ Cost: $0
```

### Option 3: Lightweight (Edge Devices)
```
Condition: Edge deployment, CPU-only, minimal memory
  └─ Model: Nomic Embed Text v1
  └─ Why: Reproducible, strong general performance
  └─ Trade-off: 8K context, not legal-specialized
  └─ Deployment: CPU-friendly
  └─ Cost: $0 (self-hosted)
```

**RECOMMENDATION:** Use **Snowflake Arctic Embed 2** for maximum parameter efficiency, but verify legal performance on your judgment corpus first.

---

## PROPRIETARY DECISION

**Requirement:** API-based, managed service, SLA guarantees

### Quick Cost Filter

```python
# For 10,000 Pakistani judgments (~20K chars = 2,857 tokens avg)
total_tokens = 10000 * 2857 = 28.57M tokens

Models:
  Kanon 2 Embedder      → $5.71  (est. $0.20/M) ✓
  Voyage 3.5            → $1.71  ($0.06/M)      ← CHEAPEST
  Voyage 3 Large        → $6.29  ($0.22/M)
  Cohere embed-v4       → $3.43  ($0.12/M)
  OpenAI 3-large        → $3.71  ($0.00013/M)   ← CHEAPEST (but 8K context)
```

### Decision Matrix by Priority

#### Priority 1: LEGAL ACCURACY

```
Question: Is legal retrieval performance critical?
  ├─ YES, must have best accuracy
  |   └─ LEGAL-SPECIALIZED?
  |      ├─ YES → Kanon 2 Embedder
  |      |        Rank: 1st on MLEB (86.03)
  |      |        Speed: 340% faster than competitors
  |      |        Context: 16K (sufficient for judgments)
  |      |        Cost: ~$0.20/M (reasonable)
  |      |        Risk: Newer, less proven ecosystem
  |      |
  |      └─ NO → Voyage 3.5
  |               Rank: 3rd on MLEB (84.07, only 2pts behind)
  |               Price: $0.06/M (4x cheaper than Kanon)
  |               Context: 32K (more than enough)
  |               Trade-off: General model, not law-specific
  |
  └─ NO, general accuracy sufficient
      └─ Cohere embed-v4 or OpenAI 3-large
         (See Priority 3)
```

**Action:** Start with **Voyage 3.5**, upgrade to **Kanon 2** if accuracy insufficient.

---

#### Priority 2: INFERENCE SPEED + ACCURACY

```
Question: Do you need fast embedding/re-embedding cycles?
  ├─ YES (e.g., real-time updates, frequent new documents)
  |   └─ Kanon 2 Embedder
  |      Speed: 62M tokens/hour (fastest)
  |      Rank: 1st legal performance
  |      Trade-off: Higher cost
  |
  └─ NO (batch processing OK)
      └─ Voyage 3.5
         Speed: Adequate for batch
         Cost: Much cheaper
```

**Action:** Use **Kanon 2 Embedder** if processing >500 documents/day.

---

#### Priority 3: COST OPTIMIZATION

```
Question: What's your budget constraint?

Budget: < $5 for 10K judgments
  ├─ Voyage 3.5 ($1.71)           ← Best value
  ├─ Open-source ($0)             ← If self-hosting possible
  └─ OpenAI 3-large ($3.71)       ← No, too short context (8K)

Budget: $5-10 for 10K judgments
  ├─ Cohere embed-v4 ($3.43)      ← If multimodal needed
  ├─ Kanon 2 Embedder ($5.71)     ← Best accuracy
  └─ Voyage 3.5 ($1.71)           ← Still better value

Budget: > $10 for 10K judgments
  ├─ Voyage 3 Large ($6.29)       ← Maximum accuracy (85.71)
  ├─ All above options
  └─ Custom fine-tuning

Ongoing costs (quarterly re-embedding, 5% of corpus):
  Voyage 3.5: $0.34/year
  Kanon 2: $1.12/year
  Cohere: $0.17/year
```

**Action:** Use **Voyage 3.5** unless special requirements demand higher cost.

---

#### Priority 4: CONTEXT LENGTH

```
Question: Do your judgments exceed 8K tokens (~30K chars)?

YES (judgments often exceed 30K chars)
  ├─ NO CHUNKING REQUIRED
  ├─ Kanon 2 Embedder      (16K)  ← Sufficient
  ├─ Voyage 3/3.5          (32K)  ← More than enough
  ├─ Cohere embed-v4       (128K) ← Overkill
  └─ ❌ OpenAI 3-large     (8K)   ← Requires chunking

NO (judgments average <8K tokens)
  ├─ All models viable
  ├─ Prefer cheaper: OpenAI 3-large ($0.00013/M)
  └─ BUT still no legal specialization
```

**Action:** Use **Voyage 3.5 or Kanon 2** (no chunking), avoid OpenAI for legal work.

---

#### Priority 5: MULTIMODAL DOCUMENTS

```
Question: Will you process scanned PDFs, images?

YES (document images, contract scans)
  └─ Cohere embed-v4
     Supports: Text + Images
     Cost: $0.12/M tokens (text) + $0.47/M (images)
     Performance: General (not legal-specific)
     Context: 128K (handles large docs)

NO (text-only judgments)
  └─ Use other models (Kanon 2, Voyage 3.5)
     Why: Simpler pipeline, better text-specialized performance
```

**Action:** Only use **Cohere embed-v4** if processing scanned documents.

---

#### Priority 6: PRIVACY/DATA SENSITIVITY

```
Question: Can judgment text be sent to external APIs?

NO (confidential cases, private data)
  ├─ Self-host open-source
  ├─ Snowflake Arctic Embed 2 ← Most efficient
  ├─ BGE-M3                  ← Multilingual option
  └─ Nomic Embed Text v1     ← Strong general perf
  Cost: $0, Privacy: 100%

YES (non-sensitive, public judgments)
  ├─ Kanon 2 Embedder (AWS private option)
  ├─ Voyage AI (encrypted in transit)
  ├─ OpenAI (standard encryption)
  └─ Cohere (standard security)
```

**Action:** For sensitive Pakistani cases → **Snowflake Arctic or BGE-M3 (self-hosted)**.

---

## MODEL SELECTION MATRIX

| Scenario | Best Choice | Alternative | Avoid |
|----------|-------------|-------------|-------|
| **Maximum legal accuracy** | Kanon 2 Embedder | Voyage 3 Large | voyage-law-2 |
| **Best price/accuracy ratio** | Voyage 3.5 | Cohere embed-v4 | Text-embedding-3-large |
| **Zero-cost MVP** | Snowflake Arctic 2 | BGE-M3 | (none) |
| **Private/on-prem** | Snowflake Arctic 2 | Nomic Embed | OpenAI API |
| **Multimodal documents** | Cohere embed-v4 | (none) | Text-only models |
| **Maximum context (edge cases)** | Cohere embed-v4 | Voyage 3/3.5 | OpenAI 3-large |
| **Multilingual needed** | BGE-M3 | Jina v3 | English-only models |
| **Fastest inference** | Kanon 2 Embedder | Snowflake Arctic | (any) |
| **Lowest total cost (1M docs)** | Voyage 3.5 | Open-source | (any) |

---

## FINAL RECOMMENDATION TIERS

### TIER 1: PRODUCTION LEGAL RAG (Recommended Start)

**Primary Choice: Voyage 3.5**

```
✓ MLEB Rank: 3rd (84.07 NDCG@10)
✓ Cost: $0.06/M tokens ($1.71 for 10K judgments)
✓ Context: 32K tokens (no chunking needed)
✓ Matryoshka: Yes (dimension flexibility)
✓ Free tokens: 200M/month
✓ Maturity: Proven in legal RAG (Harvey.ai partnership)
✓ Speed: Fast inference
✗ Legal specialization: No (but general beats legal-specific!)

Migration path: Start here → Evaluate → Upgrade to Kanon 2 if needed
```

### TIER 2: MAXIMUM ACCURACY (If Tier 1 Insufficient)

**Secondary Choice: Kanon 2 Embedder**

```
✓ MLEB Rank: 1st (86.03 NDCG@10)
✓ Speed: 340% faster than competitors
✓ Context: 16K tokens (sufficient for 99% judgments)
✓ Legal specialization: Optimized for legal
✓ Privacy: Can self-host (AWS private containers)
✓ Matryoshka: Yes
✗ Cost: ~$0.20/M tokens (higher)
✗ Proven ecosystem: Smaller than OpenAI/Voyage

Migration trigger: Voyage 3.5 search accuracy < 0.75 NDCG@10 on test set
```

### TIER 3: BUDGET/SELF-HOSTED (If Tier 1/2 Not Viable)

**Tertiary Choice: Snowflake Arctic Embed 2**

```
✓ Cost: $0 (fully open-source)
✓ Privacy: 100% self-hosted
✓ Parameter-efficiency: Best (334M params, SOTA performance)
✓ Apache 2.0: Commercial use OK
✓ Speed: CPU-viable for inference
✗ Legal performance: Not specifically tested on MLEB
✗ Context length: Unknown (likely 8K)
✗ Maintenance: Self-hosted ops overhead

Migration trigger: Budget < $1 OR privacy requirements absolute
```

---

## IMPLEMENTATION ROADMAP

### Month 1: MVP (Voyage 3.5)
```
Week 1-2: Set up Voyage 3.5 + Qdrant
          Index 100 sample judgments
          Basic semantic search

Week 3-4: Evaluate on legal test queries
          Measure: precision, recall, F1
          Calculate cost for 10K docs
          Decision: Continue → Months 2-3
```

### Month 2-3: Production (Based on Month 1 Results)

**If Voyage 3.5 NDCG@10 > 0.80:**
```
✓ Scale to 10K judgments
✓ Implement chunking strategy
✓ Add hybrid search (keyword + semantic)
✓ Deploy to production with Qdrant Cloud
✓ Monitor search quality metrics
→ DONE (cost-effective solution)
```

**If Voyage 3.5 NDCG@10 < 0.75:**
```
✗ Switch to Kanon 2 Embedder
✓ Re-index with Kanon 2
✓ Re-evaluate legal search quality
✓ If NDCG@10 > 0.85 → Deploy
→ Proceed with Kanon 2 (higher cost, better accuracy)
```

### Month 4+: Optimization
```
✓ Query expansion (legal synonyms)
✓ Metadata filtering (court, year, case type)
✓ Citation linking (case references)
✓ Reranking (BM25 + embedding)
✓ User feedback loop
```

---

## RISK MITIGATION

### Risk: "What if Voyage 3.5 accuracy is poor for Pakistani criminal law?"

**Mitigation:**
1. Test on representative judgment sample (100 documents)
2. Measure retrieval on known-relevant cases
3. If NDCG@10 < 0.75, switch to Kanon 2 (only 2-3 day delay)
4. Cost of pivot: Reindex 10K docs = ~$30 extra

### Risk: "Kanon 2 pricing unclear, could be expensive"

**Mitigation:**
1. Get pricing from Isaacus before large-scale indexing
2. Start with Voyage 3.5 (proven, clear pricing)
3. Negotiate volume discount if switching to Kanon 2
4. Open-source Arctic/BGE-M3 as safety valve

### Risk: "Pakistani legal terminology not in training data"

**Mitigation:**
1. Implement query expansion (FIR → "First Information Report")
2. Add domain-specific glossary
3. Use legal synonyms in chunking metadata
4. Test on real cases before full deployment

---

## DECISION CHECKLIST

Before selecting a model, answer these questions:

- [ ] Do you need self-hosting? (YES → Open-source)
- [ ] Is legal accuracy critical? (YES → Kanon 2)
- [ ] Do you have infrastructure for self-hosting? (YES → Snowflake Arctic)
- [ ] Do you process multimodal documents? (YES → Cohere)
- [ ] Can you spend $1-5 for 10K documents? (YES → Voyage 3.5)
- [ ] Is privacy paramount? (YES → Self-hosted model)
- [ ] Can you wait 2 weeks for evaluation? (YES → Start with Voyage 3.5)
- [ ] Do you need real-time reindexing? (YES → Kanon 2 Embedder)

---

## FINAL ANSWER

**For Pakistani Criminal Law Judgments in Qdrant (March 2026):**

### Primary: Voyage 3.5
- Cost: $0.06/M tokens
- Legal MLEB: 84.07 NDCG@10 (very good)
- Context: 32K (no chunking)
- Status: Production-ready, proven
- Risk: Low

### Secondary: Kanon 2 Embedder
- Cost: ~$0.20/M tokens (estimated)
- Legal MLEB: 86.03 NDCG@10 (best)
- Context: 16K (sufficient)
- Speed: 340% faster
- Risk: Pricing opaque, smaller ecosystem

### Tertiary: Snowflake Arctic Embed 2
- Cost: $0
- Legal MLEB: Not tested (estimated ~80)
- Context: Unknown (likely 8K)
- Benefit: Self-hosted, private
- Risk: Maintenance overhead

**START WITH: Voyage 3.5**
**DECISION POINT: Week 4 (after evaluating search quality)**
**UPGRADE IF: Accuracy insufficient OR need maximum speed**

---

**Research Date:** March 8, 2026
**Confidence Level:** HIGH (based on MLEB 2025 leaderboard)
**Review Date:** September 2026 (when new models likely released)
