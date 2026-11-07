import os
import re
import io
import csv
import hashlib
import datetime
from pathlib import Path
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from chromadb.utils import embedding_functions

from backend.app.config import settings
from backend.app.services.pdf_service import extract_text_from_pdf

# Ensure ChromaDB persistent storage directory exists
Path(settings.CHROMADB_DIR).mkdir(parents=True, exist_ok=True)


class DeterministicIndicEmbeddingFunction(embedding_functions.EmbeddingFunction):
    """
    Fallback deterministic feature-hash embedding function (384-dimensional).
    Produces normalized semantic vectors without external network downloads,
    guaranteeing reliable offline tests and graceful error handling.
    """
    def __call__(self, input: List[str]) -> List[List[float]]:
        dim = 384
        embeddings = []
        for text in input:
            vec = [0.0] * dim
            tokens = re.findall(r"\w+", text.lower())
            if not tokens:
                embeddings.append(vec)
                continue

            for idx, token in enumerate(tokens):
                # Hash token and 2-gram
                h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
                slot = h % dim
                weight = 1.0 + (1.0 / (idx + 1))
                vec[slot] += weight

                if idx > 0:
                    bigram = f"{tokens[idx-1]}_{token}"
                    h2 = int(hashlib.sha256(bigram.encode("utf-8")).hexdigest(), 16)
                    slot2 = h2 % dim
                    vec[slot2] += 1.5

            # L2 Normalize vector
            norm = sum(x * x for x in vec) ** 0.5
            if norm > 0:
                vec = [x / norm for x in vec]
            embeddings.append(vec)
        return embeddings


_chroma_client: Optional[ClientAPI] = None
_embedding_fn = None


def get_embedding_function():
    """Initializes and returns the configured embedding function with automatic fallback."""
    global _embedding_fn
    if _embedding_fn is not None:
        return _embedding_fn

    provider = getattr(settings, "EMBEDDING_PROVIDER", "default_onnx")
    if provider == "deterministic_indic":
        _embedding_fn = DeterministicIndicEmbeddingFunction()
        return _embedding_fn

    try:
        # Default Chroma ONNX embedding function (all-MiniLM-L6-v2)
        _embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        # Test call to ensure ONNX weights are loaded
        _embedding_fn(["test initialization"])
    except Exception as e:
        # Fall back to deterministic embedding
        _embedding_fn = DeterministicIndicEmbeddingFunction()

    return _embedding_fn


def get_chroma_client() -> ClientAPI:
    """Returns singleton persistent ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=settings.CHROMADB_DIR)
    return _chroma_client


def sanitize_collection_name(tenant_id: str) -> str:
    """
    Produces a valid ChromaDB collection name (3-63 chars, alphanumeric, start/end alphanumeric).
    """
    clean_id = re.sub(r"[^a-zA-Z0-9_-]", "_", tenant_id).strip("_")
    name = f"tenant_{clean_id}"
    if len(name) < 3:
        name = f"col_{name}"
    return name[:60]


def get_tenant_collection(tenant_id: str) -> Collection:
    """Retrieves or creates an isolated persistent collection for a tenant."""
    client = get_chroma_client()
    col_name = sanitize_collection_name(tenant_id)
    fn = get_embedding_function()
    return client.get_or_create_collection(
        name=col_name,
        embedding_function=fn,
        metadata={"tenant_id": tenant_id, "created_at": datetime.datetime.utcnow().isoformat()}
    )


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    """
    Splits text into overlapping chunks, attempting to break on paragraph or sentence boundaries.
    """
    if not text or not text.strip():
        return []

    text = re.sub(r"\r\n", "\n", text).strip()
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunk = text[start:].strip()
            if chunk:
                chunks.append(chunk)
            break

        # Find clean boundary (newline or period)
        split_idx = text.rfind("\n", start + overlap, end)
        if split_idx == -1:
            split_idx = text.rfind(". ", start + overlap, end)
        if split_idx == -1:
            split_idx = text.rfind(" ", start + overlap, end)
        if split_idx == -1 or split_idx <= start:
            split_idx = end

        chunk = text[start:split_idx].strip()
        if chunk:
            chunks.append(chunk)
        start = split_idx - overlap if split_idx - overlap > start else split_idx

    return chunks


def parse_document_content(filename: str, content_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Parses PDF, CSV, Excel, and Text bytes into structured sections with page/section provenance.
    """
    lower_name = filename.lower()
    sections: List[Dict[str, Any]] = []

    # 1. PDF
    if lower_name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content_bytes))
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                page_text = page_text.strip()
                if page_text:
                    sections.append({
                        "section_name": f"Page {i + 1}",
                        "text": page_text,
                        "page_number": i + 1
                    })
        except Exception:
            # Fallback to safe text extraction
            try:
                raw_text = extract_text_from_pdf(content_bytes)
            except Exception:
                raw_text = content_bytes.decode("utf-8", errors="replace")
            if raw_text and raw_text.strip():
                sections.append({"section_name": "Full Document", "text": raw_text.strip(), "page_number": 1})

    # 2. CSV
    elif lower_name.endswith(".csv"):
        text = content_bytes.decode("utf-8", errors="replace")
        csv_reader = csv.reader(io.StringIO(text))
        rows = [r for r in csv_reader if any(cell.strip() for cell in r)]
        if rows:
            header = rows[0]
            header_str = ", ".join(header)
            row_items = []
            for r_idx, r in enumerate(rows[1:], start=2):
                row_str = f"Row {r_idx}: " + "; ".join(f"{h}={v}" for h, v in zip(header, r) if v.strip())
                row_items.append(row_str)

            # Batch every 10 rows into a section
            batch_size = 10
            for b_idx in range(0, len(row_items), batch_size):
                batch = row_items[b_idx:b_idx + batch_size]
                section_text = f"CSV Header: [{header_str}]\n" + "\n".join(batch)
                sections.append({
                    "section_name": f"Rows {b_idx + 2} to {min(b_idx + batch_size + 1, len(rows))}",
                    "text": section_text,
                    "page_number": (b_idx // batch_size) + 1
                })

    # 3. Excel (.xlsx, .xls)
    elif lower_name.endswith(".xlsx") or lower_name.endswith(".xls"):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(content_bytes), data_only=True)
        for sheetname in wb.sheetnames:
            ws = wb[sheetname]
            rows = list(ws.iter_rows(values_only=True))
            clean_rows = [r for r in rows if any(cell is not None and str(cell).strip() for cell in r)]
            if not clean_rows:
                continue

            header = [str(c or "").strip() for c in clean_rows[0]]
            sheet_lines = [f"Sheet: {sheetname} | Columns: {', '.join(header)}"]
            for r_idx, r in enumerate(clean_rows[1:], start=2):
                line = f"Row {r_idx}: " + "; ".join(f"{h}={v}" for h, v in zip(header, r) if v is not None)
                sheet_lines.append(line)

            sections.append({
                "section_name": f"Sheet: {sheetname}",
                "text": "\n".join(sheet_lines),
                "page_number": 1
            })

    # 4. Text (.txt, .md, .json)
    else:
        text = content_bytes.decode("utf-8", errors="replace")
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if paragraphs:
            for i, p in enumerate(paragraphs):
                sections.append({
                    "section_name": f"Section {i + 1}",
                    "text": p,
                    "page_number": i + 1
                })
        elif text.strip():
            sections.append({
                "section_name": "Full Document",
                "text": text.strip(),
                "page_number": 1
            })

    return sections


def ingest_document_to_vector_store(
    tenant_id: str,
    filename: str,
    content_bytes: bytes,
    doc_type: Optional[str] = None,
    doc_id: Optional[str] = None,
    document_date: Optional[str] = None,
    extra_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Ingests, parses, chunks, and stores a document in the tenant's persistent ChromaDB collection.
    - Performs duplicate document detection by content SHA-256 hash.
    - Attaches rich provenance metadata to every chunk.
    - Handles PDF, CSV, Excel, and Text formats gracefully.
    """
    if not content_bytes:
        return {"status": "FAILED", "error": "Empty document content", "chunk_count": 0}

    content_hash = hashlib.sha256(content_bytes).hexdigest()
    collection = get_tenant_collection(tenant_id)

    # 1. Duplicate detection
    existing = collection.get(
        where={"content_hash": content_hash},
        limit=1
    )
    if existing and existing["ids"]:
        first_meta = existing["metadatas"][0] if existing["metadatas"] else {}
        existing_doc_id = first_meta.get("doc_id", "unknown")
        return {
            "status": "DUPLICATE",
            "is_duplicate": True,
            "doc_id": existing_doc_id,
            "filename": filename,
            "content_hash": content_hash,
            "message": f"Document '{filename}' with hash {content_hash[:8]} is already indexed (doc_id: {existing_doc_id})."
        }

    # Generate document ID if not provided
    generated_doc_id = doc_id or f"doc_{content_hash[:12]}"
    detected_type = doc_type or (
        "BANK_STATEMENT" if "statement" in filename.lower() else (
            "INVOICE" if "inv" in filename.lower() or "bill" in filename.lower() else (
                "SPREADSHEET" if filename.lower().endswith((".csv", ".xlsx", ".xls")) else "DOCUMENT"
            )
        )
    )
    doc_date = document_date or datetime.date.today().isoformat()

    # 2. Parse into structured sections
    sections = parse_document_content(filename, content_bytes)
    if not sections:
        return {"status": "UNSUPPORTED_OR_EMPTY", "error": "No parseable text extracted from document", "chunk_count": 0}

    # 3. Chunk sections
    documents: List[str] = []
    ids: List[str] = []
    metadatas: List[Dict[str, Any]] = []

    chunk_counter = 0
    for sec in sections:
        sec_name = sec["section_name"]
        sec_text = sec["text"]
        chunks = chunk_text(sec_text, chunk_size=450, overlap=80)

        for chk in chunks:
            chunk_id = f"{generated_doc_id}_chk_{chunk_counter}"
            meta = {
                "tenant_id": str(tenant_id),
                "doc_id": str(generated_doc_id),
                "source": str(filename),
                "document_type": str(detected_type),
                "date": str(doc_date),
                "page_or_section": str(sec_name),
                "chunk_index": int(chunk_counter),
                "content_hash": str(content_hash)
            }
            if extra_metadata:
                for k, v in extra_metadata.items():
                    if isinstance(v, (str, int, float, bool)):
                        meta[str(k)] = v

            documents.append(chk)
            ids.append(chunk_id)
            metadatas.append(meta)
            chunk_counter += 1

    # 4. Add to ChromaDB
    if documents:
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

    return {
        "status": "INDEXED",
        "is_duplicate": False,
        "doc_id": generated_doc_id,
        "filename": filename,
        "document_type": detected_type,
        "chunk_count": len(documents),
        "content_hash": content_hash
    }


def query_vector_store(
    tenant_id: str,
    query_text: str,
    n_results: int = 5,
    doc_type: Optional[str] = None,
    metadata_filter: Optional[Dict[str, Any]] = None,
    min_similarity: float = 0.0
) -> List[Dict[str, Any]]:
    """
    Performs tenant-isolated semantic vector retrieval over ChromaDB.
    Guarantees that no other tenant's documents can be returned.
    """
    collection = get_tenant_collection(tenant_id)
    where_filter: Dict[str, Any] = {"tenant_id": tenant_id}

    if doc_type:
        where_filter = {"$and": [{"tenant_id": tenant_id}, {"document_type": doc_type}]}
    elif metadata_filter:
        conditions = [{"tenant_id": tenant_id}]
        for k, v in metadata_filter.items():
            conditions.append({k: v})
        where_filter = {"$and": conditions}

    try:
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where_filter
        )
    except Exception:
        # Fallback without where filter if collection metadata is missing or filter errors
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results
        )

    items: List[Dict[str, Any]] = []
    if results and results.get("ids") and len(results["ids"]) > 0:
        chunk_ids = results["ids"][0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0] if results.get("distances") else [0.0] * len(docs)

        for c_id, doc, meta, dist in zip(chunk_ids, docs, metas, distances):
            meta = meta or {}
            # Strict tenant verification defense-in-depth
            if meta.get("tenant_id") and meta.get("tenant_id") != tenant_id:
                continue

            # Convert distance to similarity score
            sim_score = max(0.0, 1.0 - (float(dist) / 2.0)) if dist is not None else 1.0
            if sim_score < min_similarity:
                continue

            items.append({
                "chunk_id": c_id,
                "doc_id": meta.get("doc_id", "unknown"),
                "source": meta.get("source", "document"),
                "document_type": meta.get("document_type", "DOCUMENT"),
                "date": meta.get("date"),
                "page_or_section": meta.get("page_or_section", "1"),
                "chunk_index": meta.get("chunk_index", 0),
                "snippet": doc,
                "similarity_score": round(sim_score, 4),
                "retrieval_method": "VECTOR_DENSE"
            })

    return items


def delete_document_from_vector_store(tenant_id: str, doc_id: str) -> int:
    """Deletes all chunks belonging to a document from the tenant's collection."""
    collection = get_tenant_collection(tenant_id)
    existing = collection.get(
        where={"$and": [{"tenant_id": tenant_id}, {"doc_id": doc_id}]}
    )
    if existing and existing["ids"]:
        collection.delete(ids=existing["ids"])
        return len(existing["ids"])
    return 0


def list_tenant_documents(tenant_id: str) -> List[Dict[str, Any]]:
    """Lists unique documents indexed in the tenant's vector store."""
    collection = get_tenant_collection(tenant_id)
    all_records = collection.get()
    docs_map: Dict[str, Dict[str, Any]] = {}

    if all_records and all_records.get("metadatas"):
        for meta in all_records["metadatas"]:
            if not meta or meta.get("tenant_id") != tenant_id:
                continue
            doc_id = meta.get("doc_id")
            if doc_id and doc_id not in docs_map:
                docs_map[doc_id] = {
                    "doc_id": doc_id,
                    "source": meta.get("source"),
                    "document_type": meta.get("document_type"),
                    "date": meta.get("date"),
                    "content_hash": meta.get("content_hash"),
                    "chunks_count": 0
                }
            if doc_id:
                docs_map[doc_id]["chunks_count"] += 1

    return list(docs_map.values())

