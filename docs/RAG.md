# Adaptive Multi-Stage RAG Pipeline

## Overview

The RAG pipeline implements a 5-stage adaptive retrieval system optimized for legal queries. It combines dense vector search (BGE-M3), knowledge graph traversal (Neo4j), citation extraction, and lexical matching (BM25) with intent-adaptive weighting and cross-encoder reranking.

## Pipeline Stages

### Stage 1: Intent Detection
Classifies queries into 6 legal intent categories:
- `case_understanding` - Summarizing case facts/documents
- `section_lookup` - Finding specific legal sections/provisions
- `precedent_search` - Searching case law and judgments
- `legal_reasoning` - Applying legal principles
- `strategy_advice` - Seeking litigation strategies
- `procedural_check` - Checking procedural compliance

Hybrid approach: fast keyword matching first, LLM (Qwen3) fallback for ambiguous queries.

### Stage 2: Query Rewriting
Expands original query into 3-5 variants:
- Original (as-is)
- Expanded (legal terminology, synonyms)
- Section-focused (statutory references)
- Precedent-focused (case law emphasis)
- Simplified (keyword-only)

LLM-based rewriting with rule-based fallback.

### Stage 3: 4-Way Parallel Retrieval

| Retriever | Backend | Strengths |
|-----------|---------|-----------|
| Vector Search | Qdrant HNSW + BGE-M3 | Semantic similarity, multilingual |
| KG Search | Neo4j Cypher traversal | Legal relationships, cross-references |
| Citation Search | Regex + direct lookup | Exact section matching |
| Keyword Search | BM25 (custom impl.) | Lexical matching, exact terms |

All 4 execute in parallel via `asyncio.gather`.

### Stage 4: Reciprocal Rank Fusion
Merges results using weighted RRF:
\[ \text{RRF}(d) = \sum_{i} \frac{w_i}{k + \text{rank}_i(d)} \]

Weights adapt to detected intent:
- Section lookup: citation > vector > kg > keyword
- Precedent search: vector > keyword > citation > kg
- Procedural check: kg > citation > keyword > vector

### Stage 5: Cross-Encoder Reranking
Re-ranks top candidates using a cross-encoder model:
- Primary: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Fallback: Score-based combination (original score + RRF + term overlap)

## Implementation

```python
class RAGPipeline:
    def __init__(self):
        self.intent_detector = IntentDetector()
        self.query_rewriter = QueryRewriter()
        self.vector_retriever = VectorRetriever()
        self.kg_retriever = KnowledgeGraphRetriever()
        self.citation_retriever = CitationRetriever()
        self.keyword_retriever = KeywordRetriever()
        self.merger = ResultMerger(k=60)
        self.reranker = CrossEncoderReranker()
    
    async def search(self, query: str, top_k: int = 10) -> list[dict]:
        # Stage 1: Intent
        intent = self.intent_detector.detect(query)
        weights = self.intent_detector.get_retriever_weights(intent)
        
        # Stage 2: Rewrite
        variants = self.query_rewriter.rewrite(query, intent)
        
        # Stage 3: Parallel retrieval
        vector, kg, citation, keyword = await asyncio.gather(
            self.vector_retriever.search(variants[0], top_k * 3),
            self.kg_retriever.search(query, top_k * 2),
            self.citation_retriever.search(query, top_k),
            self.keyword_retriever.search(variants[0], top_k * 2),
        )
        
        # Stage 4: RRF merge
        merged = self.merger.merge([vector, kg, citation, keyword], weights)
        
        # Stage 5: Rerank
        return self.reranker.rerank(query, merged, top_k)
```
