import re
from typing import List, Dict, Any, Optional, Set
from rank_bm25 import BM25Plus, BM25Okapi

from backend.app.services.vector_store import query_vector_store, get_tenant_collection
from backend.app.knowledge_base.gst_statutes import GST_STATUTORY_CORPUS


# Indic and Accounting Query Expansion Dictionary
INDIC_EXPANSIONS = {
    "bijli": ["electricity", "power", "utility", "bescom", "mseb", "uppcl"],
    "kiraya": ["rent", "commercial property", "lease", "premise"],
    "kharcha": ["expense", "expenditure", "outflow", "debit", "cost"],
    "khareeda": ["purchase", "bought", "procurement", "inward supply"],
    "bikri": ["sales", "revenue", "turnover", "inflow", "credit"],
    "mal": ["goods", "raw materials", "stock", "inventory"],
    "maal": ["goods", "raw materials", "stock", "inventory"],
    "parchi": ["receipt", "invoice", "voucher", "bill"],
    "chalan": ["challan", "tax receipt", "payment slip"],
    "kamai": ["income", "earnings", "profit", "revenue"],
    "itc": ["input tax credit", "section 16", "cgst act", "eligible itc"],
    "rcm": ["reverse charge", "section 9 3", "unregistered supplier"],
    "tds": ["tax deducted at source", "section 51"],
    "tcs": ["tax collected at source", "section 52"],
    "gstr": ["gst return", "gstr-1", "gstr-3b", "tax liability"],
    "b2b": ["registered merchant", "table 4", "tax invoice"],
    "b2c": ["unregistered consumer", "retail sales", "table 7"],
    "dukaan": ["shop", "store", "office", "retail premise"],
    "vetan": ["salary", "wages", "staff compensation"],
    "vyapari": ["vendor", "supplier", "merchant", "counterparty"]
}


def expand_query_terms(query: str) -> str:
    """
    Expands vernacular Indic, Hinglish, and accounting shorthand into standard
    mercantile search terms without altering the user's original query intent.
    """
    tokens = re.findall(r"\w+", query.lower())
    expansions: Set[str] = set()

    for token in tokens:
        if token in INDIC_EXPANSIONS:
            expansions.update(INDIC_EXPANSIONS[token])

    if expansions:
        expanded_query = f"{query} " + " ".join(expansions)
        return expanded_query
    return query


def tokenize_corpus_text(text: str) -> List[str]:
    """Tokenizes text for BM25 ranking."""
    return [t.lower() for t in re.findall(r"\w+", text) if len(t) > 1]


def get_tenant_chunk_corpus(tenant_id: str, include_statutes: bool = False) -> List[Dict[str, Any]]:
    """
    Retrieves all text chunks belonging to a tenant from the persistent vector store,
    optionally combined with the statutory GST knowledge base, to build a dynamic BM25 index.
    """
    collection = get_tenant_collection(tenant_id)
    records = collection.get()

    corpus_chunks: List[Dict[str, Any]] = []

    if records and records.get("documents"):
        docs = records["documents"]
        ids = records["ids"]
        metas = records["metadatas"]

        for c_id, doc, meta in zip(ids, docs, metas):
            if not meta or meta.get("tenant_id") != tenant_id:
                continue
            corpus_chunks.append({
                "chunk_id": c_id,
                "doc_id": meta.get("doc_id", "unknown"),
                "source": meta.get("source", "document"),
                "document_type": meta.get("document_type", "DOCUMENT"),
                "date": meta.get("date"),
                "page_or_section": meta.get("page_or_section", "1"),
                "chunk_index": meta.get("chunk_index", 0),
                "snippet": doc,
                "tenant_id": tenant_id
            })

    # Include statutory corpus only when explicitly requested
    if include_statutes:
        for s_idx, stat in enumerate(GST_STATUTORY_CORPUS):
            stat_id = stat.get("id", f"stat_{s_idx}")
            stat_title = stat.get("title", "GST Statutory Provision")
            corpus_chunks.append({
                "chunk_id": f"statute_{stat_id}",
                "doc_id": stat_id,
                "source": stat.get("citation", stat_title),
                "document_type": "GST_STATUTE",
                "date": "2017-07-01",
                "page_or_section": stat_id,
                "chunk_index": s_idx,
                "snippet": f"{stat_title}\n{stat.get('content', '')}\nKeywords: {stat.get('keywords', '')}",
                "tenant_id": tenant_id
            })

    return corpus_chunks


def query_bm25_keyword_store(
    tenant_id: str,
    query_text: str,
    n_results: int = 5,
    doc_type: Optional[str] = None,
    include_statutes: bool = False
) -> List[Dict[str, Any]]:
    """
    Performs BM25 Okapi lexical retrieval over the tenant's chunk corpus.
    """
    corpus = get_tenant_chunk_corpus(tenant_id, include_statutes=include_statutes or (doc_type == "GST_STATUTE"))
    if not corpus:
        return []

    # Filter by doc_type if specified
    if doc_type:
        corpus = [c for c in corpus if c.get("document_type") == doc_type]
        if not corpus:
            return []

    tokenized_corpus = [tokenize_corpus_text(c["snippet"]) for c in corpus]
    bm25 = BM25Plus(tokenized_corpus)

    query_tokens = tokenize_corpus_text(query_text)
    if not query_tokens:
        return []

    scores = bm25.get_scores(query_tokens)

    # Pair with corpus items
    scored_items = []
    max_score = max(scores) if len(scores) > 0 and max(scores) > 0 else 1.0

    for idx, s in enumerate(scores):
        if s > 0:
            item = dict(corpus[idx])
            # Normalize BM25 score to 0..1
            item["similarity_score"] = round(min(1.0, float(s) / float(max_score)), 4)
            item["retrieval_method"] = "KEYWORD_BM25"
            scored_items.append((s, item))

    scored_items.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored_items[:n_results]]


def reciprocal_rank_fusion(
    ranked_lists: List[List[Dict[str, Any]]],
    k: int = 60,
    top_n: int = 5
) -> List[Dict[str, Any]]:
    """
    Combines ranked results from Dense Vector search and BM25 Keyword search
    using mathematically verified Reciprocal Rank Fusion:
        RRF_Score(d) = sum(1.0 / (k + rank_m(d)))
    """
    rrf_scores: Dict[str, float] = {}
    doc_map: Dict[str, Dict[str, Any]] = {}
    method_provenance: Dict[str, List[str]] = {}

    for r_list in ranked_lists:
        for rank, item in enumerate(r_list, start=1):
            chunk_id = item["chunk_id"]
            if chunk_id not in doc_map:
                doc_map[chunk_id] = item
                method_provenance[chunk_id] = []

            method = item.get("retrieval_method", "UNKNOWN")
            if method not in method_provenance[chunk_id]:
                method_provenance[chunk_id].append(method)

            score_contribution = 1.0 / (k + rank)
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + score_contribution

    # Sort items by fused RRF score
    sorted_chunks = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    fused_results = []
    for chunk_id, score in sorted_chunks[:top_n]:
        item = dict(doc_map[chunk_id])
        item["rrf_score"] = round(score, 6)
        item["retrieval_methods"] = method_provenance[chunk_id]
        item["retrieval_method"] = "HYBRID_RRF"
        fused_results.append(item)

    return fused_results


def hybrid_retrieve(
    tenant_id: str,
    query_text: str,
    top_k: int = 5,
    doc_type: Optional[str] = None,
    use_expansion: bool = True,
    include_statutes: bool = False
) -> Dict[str, Any]:
    """
    Advanced Hybrid RAG Pipeline:
    1. Query rewriting and Indic vernacular expansion.
    2. Dense Vector semantic retrieval (ChromaDB ONNX).
    3. Sparse Keyword retrieval (BM25 Okapi).
    4. Reciprocal Rank Fusion (RRF) with deduplication.
    5. Context assembly with complete provenance and exact citations.
    """
    effective_query = expand_query_terms(query_text) if use_expansion else query_text

    # 1. Vector Search
    vector_results = query_vector_store(
        tenant_id=tenant_id,
        query_text=effective_query,
        n_results=top_k * 2,
        doc_type=doc_type
    )

    # 2. BM25 Keyword Search
    bm25_results = query_bm25_keyword_store(
        tenant_id=tenant_id,
        query_text=effective_query,
        n_results=top_k * 2,
        doc_type=doc_type,
        include_statutes=include_statutes
    )

    # 3. Reciprocal Rank Fusion
    fused_chunks = reciprocal_rank_fusion(
        ranked_lists=[vector_results, bm25_results],
        k=60,
        top_n=top_k
    )

    # 4. Context Assembly with Provenance
    context_blocks = []
    citations = []

    for idx, c in enumerate(fused_chunks, start=1):
        source = c.get("source", "Unknown Document")
        section = c.get("page_or_section", "1")
        doc_type = c.get("document_type", "DOCUMENT")
        doc_id = c.get("doc_id", "unknown")
        snippet = c.get("snippet", "").strip()

        citation = {
            "index": idx,
            "source": source,
            "doc_id": doc_id,
            "section": section,
            "document_type": doc_type,
            "rrf_score": c.get("rrf_score"),
            "methods": c.get("retrieval_methods", ["HYBRID_RRF"])
        }
        citations.append(citation)

        block = f"[Source {idx}: {source} | {section} | Type: {doc_type}]\n{snippet}"
        context_blocks.append(block)

    assembled_context = "\n\n---\n\n".join(context_blocks) if context_blocks else "No relevant documents found."

    return {
        "original_query": query_text,
        "expanded_query": effective_query,
        "fused_results": fused_chunks,
        "assembled_context": assembled_context,
        "citations": citations,
        "vector_candidate_count": len(vector_results),
        "bm25_candidate_count": len(bm25_results),
        "total_fused_count": len(fused_chunks)
    }

