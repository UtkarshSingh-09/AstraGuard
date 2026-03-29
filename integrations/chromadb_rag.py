"""
ChromaDB vector store for SEBI/RBI/Tax regulatory documents.
Used by RegulatorGuardAgent for RAG-enhanced compliance checking.
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("astraguard.integrations.chromadb")

# ─── Lazy Initialization ─────────────────────────────────────────────────────

_chroma_client = None
_collection = None

COLLECTION_NAME = "sebi_regulations"
PERSIST_DIR = os.getenv("CHROMADB_PERSIST_DIR", "./chroma_data")


def _get_collection():
    """Lazy-initialize ChromaDB client and collection."""
    global _chroma_client, _collection

    if _collection is not None:
        return _collection

    try:
        import chromadb
        from chromadb.config import Settings

        _chroma_client = chromadb.PersistentClient(
            path=PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False),
        )

        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "SEBI, RBI, and Income Tax regulations for compliance checking"},
        )

        doc_count = _collection.count()
        logger.info(f"ChromaDB collection '{COLLECTION_NAME}' loaded with {doc_count} documents")

        return _collection

    except ImportError:
        logger.error("chromadb not installed. Run: pip install chromadb")
        return None
    except Exception as e:
        logger.error(f"ChromaDB initialization failed: {e}")
        return None


# ─── Query Function ──────────────────────────────────────────────────────────

async def query_regulations(
    text: str,
    n_results: int = 3,
) -> list[dict]:
    """
    Query the regulatory knowledge base for relevant rules.

    Args:
        text: The text to check against regulations
        n_results: Number of results to return

    Returns:
        List of {document, metadata, distance} dicts
    """
    collection = _get_collection()
    if collection is None:
        logger.warning("ChromaDB not available — returning empty results")
        return []

    if collection.count() == 0:
        logger.warning("ChromaDB collection is empty — run scripts/seed_chromadb.py first")
        return []

    try:
        results = collection.query(
            query_texts=[text],
            n_results=min(n_results, collection.count()),
        )

        output = []
        for i in range(len(results["documents"][0])):
            output.append({
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                "distance": results["distances"][0][i] if results.get("distances") else 0,
            })

        return output

    except Exception as e:
        logger.error(f"ChromaDB query failed: {e}")
        return []


# ─── Seeding Function (used by scripts/seed_chromadb.py) ─────────────────────

def seed_collection(documents_dir: str | Path) -> int:
    """
    Seed the ChromaDB collection from text files in a directory.

    Args:
        documents_dir: Path to directory containing .txt files

    Returns:
        Number of document chunks added
    """
    collection = _get_collection()
    if collection is None:
        raise RuntimeError("Cannot initialize ChromaDB")

    documents_dir = Path(documents_dir)
    if not documents_dir.exists():
        raise FileNotFoundError(f"Documents directory not found: {documents_dir}")

    txt_files = list(documents_dir.glob("*.txt"))
    if not txt_files:
        raise FileNotFoundError(f"No .txt files found in {documents_dir}")

    all_docs = []
    all_ids = []
    all_metas = []

    for filepath in txt_files:
        content = filepath.read_text(encoding="utf-8").strip()
        if not content:
            continue

        # Chunk the document (500 chars, 100 overlap)
        chunks = _chunk_text(content, chunk_size=500, overlap=100)

        for j, chunk in enumerate(chunks):
            doc_id = f"{filepath.stem}_chunk_{j}"
            all_docs.append(chunk)
            all_ids.append(doc_id)
            all_metas.append({
                "source": filepath.name,
                "chunk_index": j,
                "total_chunks": len(chunks),
            })

    if all_docs:
        # Upsert in batches of 100
        batch_size = 100
        for i in range(0, len(all_docs), batch_size):
            batch_end = min(i + batch_size, len(all_docs))
            collection.upsert(
                documents=all_docs[i:batch_end],
                ids=all_ids[i:batch_end],
                metadatas=all_metas[i:batch_end],
            )

    logger.info(f"Seeded {len(all_docs)} chunks from {len(txt_files)} files")
    return len(all_docs)


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += chunk_size - overlap
    return chunks
