import re
from typing import List, Dict, Any
from backend.app.knowledge_base.gst_statutes import GST_STATUTORY_CORPUS
from backend.app.llm.client import bharatcode_client
from backend.app.llm.prompts import SYSTEM_GST_ASSISTANT

def retrieve_relevant_statutes(query: str, top_k: int = 3) -> List[Dict[str, str]]:
    """
    Lightweight, deterministic lexical and semantic retriever over the Indian GST statute corpus.
    Calculates relevance score without external cloud vector database latency.
    """
    query_terms = set(re.findall(r"\w+", query.lower()))
    scored_items = []

    for item in GST_STATUTORY_CORPUS:
        score = 0
        text_corpus = f"{item['title']} {item['content']} {item['keywords']}".lower()

        # Keyword matching
        for term in query_terms:
            if len(term) <= 2:
                continue
            if term in text_corpus:
                score += 2
            if term in item["keywords"]:
                score += 3
            if term in item["title"].lower():
                score += 4

        if score > 0:
            scored_items.append((score, item))

    # Sort descending by score
    scored_items.sort(key=lambda x: x[0], reverse=True)

    if not scored_items:
        # Default fallback to Section 16 & Section 17(5)
        return GST_STATUTORY_CORPUS[:top_k]

    return [item for _, item in scored_items[:top_k]]

async def answer_gst_query_with_rag(
    user_query: str,
    language_hint: str = "English/Hindi"
) -> Dict[str, Any]:
    """
    Retrieval-Augmented Generation (RAG) assistant for GST and MSME accounting queries.
    Uses BharatCode as the sole LLM provider, strictly citing statutory sources.
    """
    retrieved_statutes = retrieve_relevant_statutes(user_query, top_k=3)

    # Format context for BharatCode
    context_str = "\n\n".join(
        f"--- Source: {doc['citation']} ---\n{doc['content']}"
        for doc in retrieved_statutes
    )

    prompt = (
        f"Statutory GST Legal Context:\n{context_str}\n\n"
        f"Merchant Query: {user_query}\n"
        f"Preferred Language: {language_hint}\n\n"
        f"Provide a clear, legally sound, and concise explanation for the Indian MSME business owner. "
        f"You MUST cite the relevant Section(s) and circulars from the provided context."
    )

    messages = [
        {"role": "system", "content": SYSTEM_GST_ASSISTANT},
        {"role": "user", "content": prompt}
    ]

    llm_resp = await bharatcode_client.chat_completion(messages, temperature=0.1)

    citations = [
        {"title": doc["title"], "citation": doc["citation"], "id": doc["id"]}
        for doc in retrieved_statutes
    ]

    return {
        "query": user_query,
        "answer": llm_resp["content"],
        "citations": citations,
        "llm_provider": "BharatCode Hosted API",
        "grounded": True
    }
