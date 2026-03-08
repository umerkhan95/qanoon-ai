# Research Sources & Citations

**Complete bibliography for embedding models research (March 2026)**

---

## Official Documentation & Pricing

### Voyage AI
- [Voyage AI Pricing](https://docs.voyageai.com/docs/pricing) — Current pricing for all models
- [Voyage AI Embeddings](https://docs.voyageai.com/docs/embeddings) — Model specifications (context length, dimensions)
- [Voyage 3 Large Blog](https://blog.voyageai.com/2025/01/07/voyage-3-large/) — Model release, performance metrics
- [Voyage 3.5 Blog](https://blog.voyageai.com/2025/05/20/voyage-3-5/) — Latest model, pricing, performance
- [Voyage Context 3 Blog](https://blog.voyageai.com/2025/07/23/voyage-context-3/) — Chunk-level embeddings

### OpenAI
- [OpenAI Embeddings Pricing](https://openai.com/api/pricing/) — Current pricing per million tokens
- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings) — Model details, context length
- [OpenAI Embedding Long Inputs](https://developers.openai.com/cookbook/examples/embedding_long_inputs/) — Chunking strategies

### Cohere
- [Cohere Embed 4 Blog](https://cohere.com/blog/embed-4) — Model announcement, specifications
- [Cohere Pricing](https://docs.cohere.com/docs/how-does-cohere-pricing-work) — Pricing structure
- [AWS Bedrock Embed v4](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-embed-v4.html) — Technical specs

### Jina AI
- [Jina Embeddings v3 Guide](https://zilliz.com/ai-models/jina-embeddings-v3) — Model specifications
- [Jina Embeddings API](https://jina.ai/embeddings/) — Pricing and capabilities

---

## Legal Embedding Benchmarks

### MLEB (Massive Legal Embedding Benchmark) — PRIMARY SOURCE

- [MLEB Leaderboard](https://isaacus.com/mleb) — 2025 rankings
- [MLEB Paper (ArXiv)](https://arxiv.org/abs/2510.19365) — Full methodology
- [MLEB GitHub](https://github.com/isaacus-dev/mleb) — Code and data
- [MLEB on Hugging Face](https://huggingface.co/blog/isaacus/introducing-mleb) — Blog announcement
- [MLEB Review](https://liner.com/review/massive-legal-embedding-benchmark-mleb) — Quick review

**Key Data:**
- 1st: Kanon 2 Embedder (86.03 NDCG@10)
- 2nd: Voyage 3 Large (85.71)
- 3rd: Voyage 3.5 (84.07)
- 8th: Voyage Law 2 (79.63)

### MTEB (Massive Text Embedding Benchmark) — GENERAL BASELINE

- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard) — Live leaderboard
- [MTEB GitHub](https://github.com/embeddings-benchmark/mteb) — Code and methodology
- [MTEB Results GitHub](https://github.com/embeddings-benchmark/results) — Raw data
- [Modal MTEB Article](https://modal.com/blog/mteb-leaderboard-article) — Tutorial and analysis
- [GeeksforGeeks MTEB](https://www.geeksforgeeks.org/artificial-intelligence/mteb-leaderboard/) — Educational overview
- [Maintaining MTEB Paper](https://arxiv.org/html/2506.21182v1) — Recent benchmark improvements

---

## Legal-Specific Research Papers

### LegalBench
- [LegalBench Website](https://hazyresearch.stanford.edu/legalbench/) — Official site
- [LegalBench Paper](https://arxiv.org/pdf/2308.11462) — Full methodology
- [LegalBench GitHub](https://github.com/HazyResearch/legalbench) — Code and datasets
- [LegalBench on Hugging Face](https://huggingface.co/datasets/nguha/legalbench) — Dataset download

### CaseHOLD
- [Legal Fact-Checking and Precedent Retrieval](https://arxiv.org/html/2601.17230) — Benchmark paper
- [CaseHOLD Dataset](https://case.law/download/) — 53K+ legal holdings

### Other Legal NLP
- [LawBench Paper](https://aclanthology.org/2024.emnlp-main.452.pdf) — Law-specific benchmark
- [Reliable Legal Retrieval](https://arxiv.org/html/2510.06999v1) — Recent research on legal RAG

---

## Model-Specific Research

### Kanon 2 Embedder
- [Kanon 2 Announcement](https://isaacus.com/blog/introducing-kanon-2-embedder) — Official announcement
- [Kanon 2 on Hugging Face](https://huggingface.co/blog/isaacus/kanon-2-embedder) — "Australian-made LLM beats OpenAI"
- [Kanon 2 on AWS Marketplace](https://aws.amazon.com/marketplace/pp/prodview-qoz2rxyqhtewu) — Pricing and deployment
- [Isaacus Funding](https://www.artificiallawyer.com/2025/09/16/isaacus-legal-ai-foundation-model-builder-bags-700k/) — Company background

### Voyage Models
- [voyage-law-2 Blog](https://blog.voyageai.com/2024/04/15/domain-specific-embeddings-and-retrieval-legal-edition-voyage-law-2/) — Legal domain adaptation
- [Harvey AI Partnership](https://www.harvey.ai/blog/harvey-partners-with-voyage-to-build-custom-legal-embeddings) — Legal RAG use case

### BGE-M3
- [BGE Documentation](https://bge-model.com/bge/bge_m3.html) — Official specs
- [BGE-M3 on Hugging Face](https://huggingface.co/BAAI/bge-m3) — Model card
- [BGE Performance Article](https://elephas.app/blog/best-embedding-models) — Comparison

### Nomic Embed Text
- [Nomic Embed Blog](https://www.nomic.ai/blog/posts/nomic-embed-text-v1) — Announcement
- [Nomic Embed Paper](https://arxiv.org/pdf/2402.01613) — Technical report
- [Nomic Embed on Hugging Face](https://huggingface.co/nomic-ai/nomic-embed-text-v1) — Model card

### Snowflake Arctic Embed
- [Snowflake Arctic Blog](https://www.snowflake.com/en/engineering-blog/introducing-snowflake-arctic-embed-snowflakes-state-of-the-art-text-embedding-models/) — Official announcement
- [Arctic Embed GitHub](https://github.com/Snowflake-Labs/arctic-embed) — Code and research
- [Arctic Embed on Hugging Face](https://huggingface.co/Snowflake/snowflake-arctic-embed-l-v2.0) — Models

---

## Chunking & RAG Best Practices

### Chunking Strategies
- [Weaviate Chunking Guide](https://weaviate.io/blog/chunking-strategies-for-rag) — Comprehensive overview
- [Pinecone Chunking Strategies](https://www.pinecone.io/learn/chunking-strategies/) — Detailed guide
- [Milvus Legal Chunking](https://milvus.io/ai-quick-reference/what-are-best-practices-for-chunking-lengthy-legal-documents-for-vectorization) — Legal-specific advice
- [FireCrawl Chunking (2026)](https://www.firecrawl.dev/blog/best-chunking-strategies-rag) — Latest 2026 article
- [Medium: From Zero to RAG](https://medium.com/@jesvinkjustin/from-zero-to-rag-the-art-of-document-chunking-and-embedding-for-rag-d9764695cc46) — Tutorial
- [IBM Chunking with Granite](https://www.ibm.com/think/tutorials/chunking-strategies-for-rag-with-langchain-watsonx-ai/) — Framework tutorial

### Legal-Specific RAG
- [Towards Reliable Legal Retrieval](https://arxiv.org/html/2510.06999v1) — Recent research

---

## Comparison & Analysis Articles

- [Best Embedding Models 2025](https://elephas.app/blog/best-embedding-models) — Detailed comparison
- [13 Best Embedding Models 2026](https://elephas.app/blog/best-embedding-models) — Updated guide
- [Top Embedding Models](https://modal.com/blog/mteb-leaderboard-article) — Technical analysis
- [OpenAI Embeddings Calculator](https://costgoat.com/pricing/openai-embeddings) — Cost tool
- [Voyage AI Pricing Landscape](https://www.oreateai.com/blog/voyage-ai-embeddings-navigating-the-pricing-landscape-for-2025/) — Pricing analysis
- [Best Open-Source Models](https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models-in-2026) — BentoML overview

---

## Marketplace & Deployment

### AWS Marketplace
- [voyage-law-2](https://aws.marketplace.amazon.com/pp/prodview-bknagyko2vl7a) — Legal model
- [voyage-3-large](https://aws.marketplace.amazon.com/pp/prodview-bwfhiokkdhb76) — General model
- [voyage-3.5-lite](https://aws.marketplace.amazon.com/pp/prodview-xj76cqxng4wyw) — Lite variant
- [Kanon 2 Embedder](https://aws.marketplace.amazon.com/pp/prodview-qoz2rxyqhtewu) — Legal-specific

### Microsoft Azure
- [Voyage 3.5](https://ai.azure.com/catalog/models/voyage-3.5-embedding-model) — Azure listing
- [Jina v3](https://marketplace.microsoft.com/marketplace/apps/jinaai.jina-embeddings-v3-vm) — Azure VM

---

## Ollama & Local Deployment

- [Ollama BGE-M3](https://ollama.com/library/bge-m3) — Local CPU/GPU
- [Ollama Nomic Embed](https://ollama.com/library/nomic-embed-text) — Local deployment
- [Ollama Arctic Embed 2](https://ollama.com/library/snowflake-arctic-embed2) — Local

---

## Tools & Calculators

- [liteLLM Providers](https://docs.litellm.ai/docs/providers/voyage) — Multi-provider routing
- [LLM Pricing Table](https://llmpricingtable.com/models/cohere-embed-v4.0/) — Cohere pricing
- [CloudPrice](https://cloudprice.net/models/voyage/voyage-3.5) — Model pricing
- [Bifrost Cost Calculator](https://www.getmaxim.ai/bifrost/llm-cost-calculator/) — Multi-model calculator

---

## Related Technologies

### Qdrant Vector Database
- [Qdrant Docs](https://qdrant.io) — Official documentation
- [Pinecone Docs](https://docs.pinecone.io/models/voyage-law-2) — Integration guide

### BM25 & Hybrid Search
- [Rank-BM25 Library](https://github.com/dorianbrown/rank_bm25) — Python implementation

---

## News & Announcements

- [NVIDIA Embedding Model](https://developer.nvidia.com/blog/nvidia-text-embedding-model-tops-mteb-leaderboard/) — Oct 2025 release
- [Voyage 3.5 & lite](https://www.mongodb.com/company/blog/product-release-announcements/introducing-voyage-3-5-voyage-3-5-lite-improved-quality-new-retrieval-frontier/) — May 2025
- [Hacker News: Cohere Embed 4](https://news.ycombinator.com/item?id=43694546) — Discussion thread
- [MarkTechPost: Voyage 3](https://www.marktechpost.com/2024/09/27/voyage-ai-introduces-voyage-3-and-voyage-3-lite-a-new-generation-of-small-embedding-models-that-outperforms-openai-v3-large-by-7-55/) — Model comparison

---

## Research Data Quality

### Data Freshness

| Source | Last Updated | Confidence |
|--------|--------------|-----------|
| MLEB Leaderboard | October 2025 | **HIGH** — Official |
| Voyage API Docs | Current | **HIGH** — Official |
| OpenAI Pricing | March 2026 | **HIGH** — Official |
| MTEB Leaderboard | Ongoing | **HIGH** — Live |
| Cohere Pricing | March 2026 | **HIGH** — Official |
| Kanon 2 Benchmarks | Oct 2025 | **HIGH** — Paper |
| Context length enforcement (OpenAI) | Jan 2025 | **MEDIUM** — User reports |
| Open-source legal performance | Not tested | **LOW** — Estimated |

---

## Citation Format

**For academic use:**

```bibtex
@article{mleb2025,
  title={The Massive Legal Embedding Benchmark (MLEB)},
  author={Isaacus},
  journal={arXiv preprint arXiv:2510.19365},
  year={2025}
}

@article{legal_retrieval2025,
  title={Towards Reliable Retrieval in RAG Systems for Large Legal Datasets},
  journal={arXiv preprint arXiv:2510.06999},
  year={2025}
}
```

---

## How to Verify Results

To reproduce this research:

1. **Download MLEB leaderboard** from [isaacus.com/mleb](https://isaacus.com/mleb)
2. **Check MTEB** at [huggingface.co/spaces/mteb/leaderboard](https://huggingface.co/spaces/mteb/leaderboard)
3. **Verify pricing** on official APIs:
   - [Voyage AI](https://docs.voyageai.com/docs/pricing)
   - [OpenAI](https://openai.com/api/pricing/)
   - [Cohere](https://docs.cohere.com/docs/how-does-cohere-pricing-work)
4. **Test context lengths** with model APIs

---

**Research Compiled:** March 8, 2026
**Total Sources Reviewed:** 80+
**Categories:** 8
**Primary Benchmark:** MLEB 2025
**Status:** Ready for citation
