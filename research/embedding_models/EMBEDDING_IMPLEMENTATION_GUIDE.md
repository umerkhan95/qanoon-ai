# Legal Embedding Implementation Guide for Pakistani Criminal Law

**Target:** Qdrant-based semantic search for criminal law judgments
**Scope:** 10,000+ judgments (5K-50K chars each)
**Language:** English with potential Urdu legal terminology

---

## Phase 1: MVP Setup (Voyage 3.5)

### 1.1 Install Dependencies

```bash
pip install qdrant-client voyageai python-dotenv
```

### 1.2 Setup Environment

```bash
# .env
VOYAGE_API_KEY=your_api_key_here
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

### 1.3 Initialize Qdrant

```bash
# Start Qdrant locally (Docker)
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant:latest
```

Or use Qdrant Cloud for production.

---

## Phase 1 Implementation: Basic Indexing

```python
# embedding_service.py
import os
import logging
from typing import List, Dict
from voyage import Voyage
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

logger = logging.getLogger(__name__)

class LegalEmbeddingService:
    """Pakistani criminal law judgment embedding & retrieval service."""

    def __init__(self,
                 api_key: str = None,
                 qdrant_host: str = "localhost",
                 qdrant_port: int = 6333,
                 model_name: str = "voyage-3.5"):
        """
        Initialize embedding service.

        Args:
            api_key: Voyage API key
            qdrant_host: Qdrant server host
            qdrant_port: Qdrant server port
            model_name: Embedding model ("voyage-3.5", "voyage-3-large", etc.)
        """
        self.api_key = api_key or os.getenv("VOYAGE_API_KEY")
        self.model_name = model_name
        self.embedding_dim = 1024  # Voyage 3.5 default

        # Initialize clients
        self.voyage_client = Voyage(api_key=self.api_key)
        self.qdrant_client = QdrantClient(
            host=qdrant_host,
            port=qdrant_port
        )

        self._initialize_collection()

    def _initialize_collection(self, collection_name: str = "judgments"):
        """Create Qdrant collection if not exists."""
        try:
            self.qdrant_client.get_collection(collection_name)
            logger.info(f"Collection '{collection_name}' already exists")
        except Exception:
            logger.info(f"Creating collection '{collection_name}'")
            self.qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE
                )
            )

    def embed_judgment(self, judgment_text: str) -> List[float]:
        """
        Embed a single judgment (no chunking for <16K tokens).

        Args:
            judgment_text: Full judgment text

        Returns:
            Embedding vector
        """
        # Truncate if exceeds 32K tokens (unlikely for single judgment)
        # Voyage 3.5 supports 32K context
        if len(judgment_text) > 200000:  # ~50K tokens max
            logger.warning(f"Judgment exceeds 50K tokens, truncating")
            judgment_text = judgment_text[:200000]

        embedding = self.voyage_client.embed(
            texts=[judgment_text],
            model=self.model_name,
            input_type="document"
        )
        return embedding.embeddings[0]

    def embed_query(self, query_text: str) -> List[float]:
        """Embed a search query."""
        embedding = self.voyage_client.embed(
            texts=[query_text],
            model=self.model_name,
            input_type="query"
        )
        return embedding.embeddings[0]

    def index_judgment(self,
                      judgment_id: str,
                      judgment_text: str,
                      metadata: Dict) -> None:
        """
        Index a judgment in Qdrant.

        Args:
            judgment_id: Unique identifier (e.g., "CA_123_2024")
            judgment_text: Full judgment text
            metadata: Dict with case info (court, year, judge, case_type, etc.)
        """
        # Embed
        embedding = self.embed_judgment(judgment_text)

        # Create point
        point = PointStruct(
            id=hash(judgment_id) % (2**31),  # Convert string ID to numeric
            vector=embedding,
            payload={
                **metadata,
                "judgment_id": judgment_id,
                "text_length": len(judgment_text),
                "char_count": len(judgment_text)
            }
        )

        # Upsert to Qdrant
        self.qdrant_client.upsert(
            collection_name="judgments",
            points=[point]
        )
        logger.info(f"Indexed judgment {judgment_id}")

    def search(self,
               query: str,
               limit: int = 10,
               score_threshold: float = 0.7) -> List[Dict]:
        """
        Semantic search for judgments.

        Args:
            query: Search query (e.g., "bail application for murder")
            limit: Number of results
            score_threshold: Minimum similarity score (0-1)

        Returns:
            List of matching judgments with scores
        """
        # Embed query
        query_embedding = self.embed_query(query)

        # Search Qdrant
        results = self.qdrant_client.search(
            collection_name="judgments",
            query_vector=query_embedding,
            limit=limit,
            score_threshold=score_threshold
        )

        # Format results
        return [
            {
                "judgment_id": hit.payload.get("judgment_id"),
                "court": hit.payload.get("court"),
                "year": hit.payload.get("year"),
                "case_type": hit.payload.get("case_type"),
                "judge": hit.payload.get("judge"),
                "similarity_score": hit.score,
                "text_preview": hit.payload.get("text_length", 0)
            }
            for hit in results
        ]

    def batch_index(self, judgments: List[Dict]) -> None:
        """
        Index multiple judgments efficiently.

        Args:
            judgments: List of dicts with keys:
                      - id: judgment ID
                      - text: judgment text
                      - metadata: dict with case info
        """
        # Extract texts for batch embedding
        texts = [j["text"] for j in judgments]

        # Batch embed (more efficient than one-by-one)
        embeddings_response = self.voyage_client.embed(
            texts=texts,
            model=self.model_name,
            input_type="document"
        )

        # Create points
        points = [
            PointStruct(
                id=hash(j["id"]) % (2**31),
                vector=emb,
                payload={
                    **j.get("metadata", {}),
                    "judgment_id": j["id"],
                    "char_count": len(j["text"])
                }
            )
            for j, emb in zip(judgments, embeddings_response.embeddings)
        ]

        # Upsert batch
        self.qdrant_client.upsert(
            collection_name="judgments",
            points=points
        )
        logger.info(f"Batch indexed {len(judgments)} judgments")
```

### 1.4 Example Usage

```python
# main.py
from embedding_service import LegalEmbeddingService
import json

# Initialize service
service = LegalEmbeddingService(
    model_name="voyage-3.5"
)

# Load sample judgments
with open("sample_judgments.json") as f:
    judgments = json.load(f)

# Index first 100 for testing
test_judgments = judgments[:100]
service.batch_index(test_judgments)

# Search
results = service.search("bail application for murder charge", limit=5)
for result in results:
    print(f"{result['judgment_id']} ({result['court']}, {result['year']})")
    print(f"  Similarity: {result['similarity_score']:.4f}")
    print()
```

---

## Phase 2: Semantic Chunking for Long Documents

```python
# chunking_service.py
from typing import List, Tuple
import re

class JudgmentChunkingService:
    """Chunk long judgments while preserving legal structure."""

    @staticmethod
    def extract_sections(judgment_text: str) -> Dict[str, str]:
        """
        Extract standard sections from Pakistani judgment.

        Returns:
            Dict with keys: preamble, facts, law, judgment, order
        """
        sections = {
            "preamble": "",
            "facts": "",
            "law": "",
            "judgment": "",
            "order": ""
        }

        # Simple regex-based extraction
        # (in production, use more robust parsing)
        preamble_match = re.search(
            r"(CASE|Criminal Appeal|Writ Petition).*?(?=FACTS:|Facts:)",
            judgment_text,
            re.DOTALL | re.IGNORECASE
        )
        if preamble_match:
            sections["preamble"] = preamble_match.group(0)

        facts_match = re.search(
            r"(?:FACTS:|Facts:)(.*?)(?=LAW:|Law:|LEGAL|Legal)",
            judgment_text,
            re.DOTALL | re.IGNORECASE
        )
        if facts_match:
            sections["facts"] = facts_match.group(1)

        law_match = re.search(
            r"(?:LAW:|Law:)(.*?)(?=JUDGMENT:|Judgment:|DECISION:|Decision:)",
            judgment_text,
            re.DOTALL | re.IGNORECASE
        )
        if law_match:
            sections["law"] = law_match.group(1)

        # Judgment is typically the rest
        judgment_match = re.search(
            r"(?:JUDGMENT:|Judgment:|DECISION:|Decision:)(.*)",
            judgment_text,
            re.DOTALL | re.IGNORECASE
        )
        if judgment_match:
            sections["judgment"] = judgment_match.group(1)

        return sections

    @staticmethod
    def chunk_with_context(judgment_text: str,
                          chunk_size: int = 1000,
                          overlap: int = 200) -> List[Tuple[str, Dict]]:
        """
        Chunk judgment with sliding window and context preservation.

        Args:
            judgment_text: Full judgment
            chunk_size: Tokens per chunk (~4 chars per token)
            overlap: Overlapping tokens between chunks

        Returns:
            List of (chunk_text, metadata) tuples
        """
        # Convert to character-based splitting (1 token ≈ 4 chars)
        char_chunk_size = chunk_size * 4
        char_overlap = overlap * 4
        stride = char_chunk_size - char_overlap

        chunks = []
        for i in range(0, len(judgment_text), stride):
            chunk = judgment_text[i:i + char_chunk_size]
            if len(chunk) < 200:  # Skip very small chunks
                continue

            chunks.append((chunk, {
                "chunk_index": len(chunks),
                "start_char": i,
                "chunk_size_chars": len(chunk)
            }))

        return chunks

    @staticmethod
    def chunk_by_section(judgment_text: str) -> List[Tuple[str, Dict]]:
        """
        Chunk at section boundaries (preferred for legal documents).

        Returns:
            List of (section_text, metadata) tuples
        """
        sections = JudgmentChunkingService.extract_sections(judgment_text)
        chunks = []

        section_order = ["preamble", "facts", "law", "judgment", "order"]
        prev_section = None

        for section_name in section_order:
            section_text = sections[section_name]
            if not section_text.strip():
                continue

            # Add previous section's last 500 chars for context
            context = ""
            if prev_section:
                prev_text = sections[prev_section]
                context = f"\n[Previous: ...{prev_text[-500:]}...]\n"

            chunk = context + section_text
            chunks.append((chunk, {
                "section": section_name,
                "context_included": prev_section is not None
            }))

            prev_section = section_name

        return chunks

# Example usage
chunking_service = JudgmentChunkingService()
long_judgment = "... full judgment text ..."

# Option 1: Section-based chunking (recommended)
chunks = chunking_service.chunk_by_section(long_judgment)
for chunk_text, metadata in chunks:
    print(f"Section: {metadata['section']}, Chars: {len(chunk_text)}")

# Option 2: Sliding window chunking
chunks = chunking_service.chunk_with_context(long_judgment, chunk_size=1000, overlap=200)
for chunk_text, metadata in chunks:
    print(f"Chunk {metadata['chunk_index']}, Chars: {len(chunk_text)}")
```

---

## Phase 3: Hybrid Search (Keyword + Semantic)

```python
# hybrid_search_service.py
from rank_bm25 import BM25Okapi
from typing import List, Dict
import re

class HybridSearchService:
    """Combine BM25 keyword search with semantic embedding search."""

    def __init__(self, embedding_service: LegalEmbeddingService):
        self.embedding_service = embedding_service
        self.judgments = []  # In-memory corpus for BM25
        self.bm25 = None

    def load_corpus(self, judgments: List[Dict]) -> None:
        """Load judgments for BM25 indexing."""
        self.judgments = judgments

        # Tokenize for BM25
        tokenized_judgments = [
            self._tokenize(j["text"]) for j in judgments
        ]

        self.bm25 = BM25Okapi(tokenized_judgments)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple tokenization for BM25."""
        # Lowercase, split, remove special chars
        tokens = re.findall(r'\b[a-z]+\b', text.lower())
        return tokens

    def hybrid_search(self,
                     query: str,
                     limit: int = 10,
                     bm25_weight: float = 0.4,
                     semantic_weight: float = 0.6) -> List[Dict]:
        """
        Hybrid search: combine BM25 and semantic scores.

        Args:
            query: Search query
            limit: Number of results
            bm25_weight: Weight for keyword relevance (0-1)
            semantic_weight: Weight for semantic similarity (0-1)

        Returns:
            Ranked results
        """
        query_tokens = self._tokenize(query)

        # BM25 scores
        bm25_scores = self.bm25.get_scores(query_tokens)
        bm25_normalized = (bm25_scores - bm25_scores.min()) / (bm25_scores.max() - bm25_scores.min() + 1e-6)

        # Semantic scores
        semantic_results = self.embedding_service.search(query, limit=len(self.judgments))
        semantic_scores = {}
        for result in semantic_results:
            judgment_id = result["judgment_id"]
            # Find matching judgment index
            idx = next(
                (i for i, j in enumerate(self.judgments) if j.get("id") == judgment_id),
                None
            )
            if idx is not None:
                semantic_scores[idx] = result["similarity_score"]

        # Combine scores
        combined_scores = []
        for i, judgment in enumerate(self.judgments):
            bm25_score = bm25_normalized[i] if i < len(bm25_normalized) else 0
            semantic_score = semantic_scores.get(i, 0)

            combined_score = (
                bm25_weight * bm25_score +
                semantic_weight * semantic_score
            )

            combined_scores.append({
                "judgment_id": judgment.get("id"),
                "court": judgment.get("court"),
                "year": judgment.get("year"),
                "combined_score": combined_score,
                "bm25_score": bm25_score,
                "semantic_score": semantic_score
            })

        # Sort by combined score
        combined_scores.sort(key=lambda x: x["combined_score"], reverse=True)

        return combined_scores[:limit]
```

---

## Phase 4: Query Expansion for Legal Concepts

```python
# legal_query_expansion.py
from typing import List, Set

class LegalQueryExpander:
    """Expand legal queries with synonyms and related concepts."""

    LEGAL_SYNONYMS = {
        "bail": [
            "bail application", "bail petition", "anticipatory bail",
            "default bail", "regular bail", "bail bond"
        ],
        "murder": [
            "qatl", "homicide", "culpable homicide",
            "premeditated murder", "murder charge"
        ],
        "theft": [
            "dacoity", "robbery", "burglary", "larceny",
            "theft charge", "petty theft"
        ],
        "appeal": [
            "criminal appeal", "appeal petition", "appellate review",
            "writ petition", "intra-court appeal"
        ],
        "fir": [
            "First Information Report", "complaint", "case registration",
            "police report"
        ],
        "evidence": [
            "documentary evidence", "oral evidence", "circumstantial evidence",
            "direct evidence", "admissible evidence"
        ],
        "mens rea": [
            "criminal intent", "guilty mind", "mens rea",
            "intention", "criminal knowledge"
        ],
        "actus reus": [
            "guilty act", "criminal act", "actus reus",
            "overt act", "wrongful act"
        ]
    }

    @classmethod
    def expand_query(cls, query: str) -> Set[str]:
        """
        Expand a legal query with synonyms.

        Args:
            query: Original query

        Returns:
            Set of expanded queries
        """
        expanded = {query}  # Include original

        # Check each legal term
        for term, synonyms in cls.LEGAL_SYNONYMS.items():
            if term.lower() in query.lower():
                # Add all synonyms
                for synonym in synonyms:
                    expanded.add(query.replace(term, synonym, flags=re.IGNORECASE))
                    expanded.add(query.replace(term, synonym))

        return expanded

    @classmethod
    def get_related_concepts(cls, query: str) -> List[str]:
        """Get broader legal concepts related to query."""
        related = []

        if "bail" in query.lower():
            related.extend([
                "conditions of bail",
                "bail conditions",
                "surety",
                "recognizance"
            ])

        if "murder" in query.lower():
            related.extend([
                "culpable homicide",
                "voluntary injury",
                "premeditation",
                "evidence in murder trials"
            ])

        return related

# Usage
expander = LegalQueryExpander()
original_query = "bail application for murder charge"
expanded_queries = expander.expand_query(original_query)
related = expander.get_related_concepts(original_query)

print(f"Original: {original_query}")
print(f"Expanded: {expanded_queries}")
print(f"Related: {related}")
```

---

## Phase 5: Metadata Filtering in Qdrant

```python
# metadata_filter_service.py
from qdrant_client.models import Filter, FieldCondition, MatchValue

class MetadataFilterService:
    """Apply metadata filters to Qdrant searches."""

    @staticmethod
    def build_court_filter(courts: List[str]) -> Filter:
        """Filter by court (Supreme, High, District)."""
        from qdrant_client.models import HasIdCondition, MatchAny

        return Filter(
            should=[
                FieldCondition(
                    key="court",
                    match=MatchValue(value=court)
                )
                for court in courts
            ]
        )

    @staticmethod
    def build_year_range_filter(min_year: int, max_year: int) -> Filter:
        """Filter by year range."""
        from qdrant_client.models import Range

        return Filter(
            must=[
                FieldCondition(
                    key="year",
                    range=Range(gte=min_year, lte=max_year)
                )
            ]
        )

    @staticmethod
    def build_case_type_filter(case_types: List[str]) -> Filter:
        """Filter by case type."""
        return Filter(
            should=[
                FieldCondition(
                    key="case_type",
                    match=MatchValue(value=case_type)
                )
                for case_type in case_types
            ]
        )

    @staticmethod
    def combined_filter(courts: List[str] = None,
                       min_year: int = None,
                       max_year: int = None,
                       case_types: List[str] = None) -> Filter:
        """Combine multiple filters."""
        filters = []

        if courts:
            filters.append(MetadataFilterService.build_court_filter(courts))

        if min_year and max_year:
            filters.append(
                MetadataFilterService.build_year_range_filter(min_year, max_year)
            )

        if case_types:
            filters.append(
                MetadataFilterService.build_case_type_filter(case_types)
            )

        if not filters:
            return None

        return Filter(must=filters) if len(filters) == 1 else Filter(must=filters)

# Usage
# Filter for Supreme Court decisions on murder cases, 2020-2024
search_filter = MetadataFilterService.combined_filter(
    courts=["Supreme Court", "Lahore High Court"],
    min_year=2020,
    max_year=2024,
    case_types=["murder", "criminal"]
)

# Apply in search (requires qdrant_client update)
# results = qdrant_client.search(
#     collection_name="judgments",
#     query_vector=embedding,
#     query_filter=search_filter,
#     limit=10
# )
```

---

## Performance Benchmarks (Expected)

### Embedding Latency
- **Batch embed 100 judgments:** 2-3 seconds (Voyage 3.5 API)
- **Single embed:** 50-100ms
- **Search latency:** 10-50ms (Qdrant local)

### Cost (10,000 judgments × 2,857 tokens avg)
- **Voyage 3.5:** $1.71 (one-time)
- **Re-embedding (5% quarterly):** $0.086/quarter
- **Queries:** Free (index lookup only)

### Memory
- **10K judgments in Qdrant:** ~40 GB (1024-dim vectors × 8 bytes × 10K)
- **With metadata:** ~60-80 GB

---

## Monitoring & Metrics

```python
# monitoring.py
import time
from dataclasses import dataclass

@dataclass
class SearchMetrics:
    """Track search performance."""
    query: str
    latency_ms: float
    num_results: int
    top_similarity_score: float

    def log(self):
        print(
            f"Query: {self.query}\n"
            f"  Latency: {self.latency_ms:.2f}ms\n"
            f"  Results: {self.num_results}\n"
            f"  Top Score: {self.top_similarity_score:.4f}"
        )

# Usage
start = time.time()
results = service.search("bail for murder", limit=10)
latency = (time.time() - start) * 1000

metrics = SearchMetrics(
    query="bail for murder",
    latency_ms=latency,
    num_results=len(results),
    top_similarity_score=results[0]["similarity_score"] if results else 0
)
metrics.log()
```

---

## Troubleshooting

### Issue: Low similarity scores (< 0.5)
**Cause:** Query/document mismatch in embedding space
**Solution:**
1. Verify embedding model loaded correctly
2. Check if judgment text quality issues
3. Try query expansion
4. Use hybrid search (keyword + semantic)

### Issue: Slow search (> 100ms)
**Cause:** Large Qdrant collection
**Solution:**
1. Add metadata filters to reduce search space
2. Use limit parameter
3. Optimize Qdrant configuration
4. Consider multi-shard setup

### Issue: High API costs
**Cause:** Frequent re-embedding
**Solution:**
1. Cache embeddings in Qdrant (already done)
2. Batch embed new documents
3. Use cheaper model (Voyage 3.5 vs. 3-large)
4. Consider self-hosted open-source model

---

## Next Steps

1. **Week 1:** Set up Voyage 3.5 + Qdrant, index 100 test judgments
2. **Week 2:** Evaluate search quality, measure latency/cost
3. **Week 3:** Implement semantic chunking + hybrid search
4. **Week 4:** Add metadata filtering, query expansion
5. **Week 5:** Scale to 10K judgments, monitor performance
6. **Week 6:** Consider upgrade to Kanon 2 if accuracy insufficient

---

**Created:** March 8, 2026
**Status:** Ready for implementation
