"""
Long-term memory for E.V.A. using ChromaDB.

Stores facts / conversation snippets as embeddings so Eva can recall
relevant context from past sessions.

Requires:
  pip install chromadb
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from backend import config

logger = logging.getLogger(__name__)

_client = None
_collection = None
COLLECTION_NAME = "eva_memory"


def _get_collection():
    global _client, _collection
    if _collection is None:
        import chromadb  # type: ignore

        _client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("ChromaDB collection '%s' ready", COLLECTION_NAME)
    return _collection


def memory_store(text: str, metadata: Optional[dict] = None) -> str:
    """Persist *text* to long-term vector memory.

    Returns the generated document ID.
    """
    col = _get_collection()
    doc_id = str(uuid.uuid4())
    col.add(
        documents=[text],
        ids=[doc_id],
        metadatas=[metadata or {}],
    )
    logger.info("Stored memory (id=%s): %r", doc_id, text[:60])
    return doc_id


def memory_search(query: str, n_results: int = 5) -> list[dict]:
    """Search long-term memory for entries relevant to *query*.

    Returns a list of dicts: [{"text": ..., "id": ..., "metadata": ...}, ...]
    """
    col = _get_collection()
    results = col.query(query_texts=[query], n_results=n_results)
    output = []
    for doc, doc_id, meta in zip(
        results["documents"][0],
        results["ids"][0],
        results["metadatas"][0],
    ):
        output.append({"text": doc, "id": doc_id, "metadata": meta})
    logger.info("Memory search '%s' → %d results", query, len(output))
    return output


def memory_delete(doc_id: str) -> str:
    """Delete a memory entry by its document ID."""
    col = _get_collection()
    col.delete(ids=[doc_id])
    logger.info("Deleted memory id=%s", doc_id)
    return f"Memory {doc_id} deleted."
