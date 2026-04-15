"""ChromaDB vector store: text chunks and image records (title + citation) per book."""

import chromadb
from chromadb.config import Settings
from typing import Any, Dict, Optional
from app.config import (
    CHROMA_DIR,
    RELEVANCE_MAX_DISTANCE_TEXT,
    RELEVANCE_MAX_DISTANCE_IMAGE,
)
from app.services.embeddings import embed


def _client():
    return chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )


def _text_collection_name(book_id: str) -> str:
    return f"text_{book_id}"


def _image_collection_name(book_id: str) -> str:
    return f"images_{book_id}"


def init_text_collection(book_id: str) -> None:
    """Ensure text collection exists."""
    client = _client()
    name = _text_collection_name(book_id)
    client.get_or_create_collection(name=name, metadata={"description": "Text chunks"})


def add_text_chunks(book_id: str, chunks: list[str], metadatas: list[dict[str, Any]]) -> None:
    """Add text chunks with metadata."""
    if not chunks:
        return

    client = _client()
    name = _text_collection_name(book_id)

    coll = client.get_or_create_collection(
        name=name,
        metadata={"description": "Text chunks"}
    )

    embeddings = embed(chunks, is_query=False)

    ids = [f"text_{book_id}_{i}" for i in range(len(chunks))]

    clean_meta = []
    for m in metadatas:
        row = {}
        for k, v in m.items():
            s = str(v) if v is not None else ""
            if k == "section" and len(s) > 300:
                s = s[:297] + "..."
            row[k] = s
        clean_meta.append(row)

    coll.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=clean_meta
    )


def add_image_record(
    book_id: str,
    image_path: str,
    title: str,
    citation: str = "",
    description: str = "",
    page_ref: Optional[str] = None,
    embedding_document: Optional[str] = None,
    figure_ref: str = "",
) -> None:
    """Store an image record. Embedding uses embedding_document if set, else title + citation/description."""
    client = _client()
    name = _image_collection_name(book_id)

    coll = client.get_or_create_collection(
        name=name,
        metadata={"description": "Image citations"}
    )

    body = (description or "").strip() if (description or "").strip() else (citation or "").strip()
    combined = (embedding_document or "").strip() or f"{title} {body}".strip()

    emb = embed([combined], is_query=False)

    import uuid
    id_ = f"img_{book_id}_{uuid.uuid4().hex[:12]}"

    meta = {
        "image_path": image_path,
        "title": title,
        "citation": (citation or "").strip(),
        "description": (description or "").strip(),
        "page_ref": (page_ref or "").strip(),
        "figure_ref": (figure_ref or "").strip(),
    }

    meta = {
        k: (v[:500] if isinstance(v, str) and len(v) > 500 else v)
        for k, v in meta.items()
    }

    doc = combined[:50000] if len(combined) > 50000 else combined
    coll.add(ids=[id_], embeddings=emb, documents=[doc], metadatas=[meta])


def _deduplicate_chunks(results):
    """Remove near-duplicate overlapping chunks."""
    seen = set()
    unique = []

    for r in results:
        text = r["text"][:120]  # first part as signature
        if text in seen:
            continue
        seen.add(text)
        unique.append(r)

    return unique


def query_text(
    book_id: str,
    query_embedding: list[float],
    top_k: int = 10,
    max_distance: Optional[float] = None
) -> list[dict[str, Any]]:
    """Return relevant text chunks."""

    if max_distance is None:
        max_distance = RELEVANCE_MAX_DISTANCE_TEXT

    client = _client()
    name = _text_collection_name(book_id)

    try:
        coll = client.get_collection(name=name)
    except Exception:
        return []

    res = coll.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    out = []

    if not res["documents"] or not res["documents"][0]:
        return []

    distances = (res.get("distances") or [[]])
    distance_list = distances[0] if distances else []

    for i, doc in enumerate(res["documents"][0]):
        dist = distance_list[i] if i < len(distance_list) else float("inf")

        if distance_list and dist > max_distance:
            continue

        meta = (res["metadatas"][0][i] or {}) if res["metadatas"] else {}

        out.append({
            "text": doc,
            "metadata": meta
        })

    # Remove overlapping duplicates
    out = _deduplicate_chunks(out)

    # Sort by page number so context follows book order
    out = sorted(
        out,
        key=lambda x: int((x.get("metadata") or {}).get("page_number", 0))
    )

    return out


def query_images(
    book_id: str,
    query_embedding: list[float],
    top_k: int = 5,
    max_distance: Optional[float] = None
) -> list[dict[str, Any]]:
    """Return relevant image records."""

    if max_distance is None:
        max_distance = RELEVANCE_MAX_DISTANCE_IMAGE

    client = _client()
    name = _image_collection_name(book_id)

    try:
        coll = client.get_collection(name=name)
    except Exception:
        return []

    res = coll.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["metadatas", "distances"],
    )

    out = []

    if not res["metadatas"] or not res["metadatas"][0]:
        return []

    distances = (res.get("distances") or [[]])
    distance_list = distances[0] if distances else []

    metas = res["metadatas"][0]
    for i, meta in enumerate(metas):
        dist = distance_list[i] if i < len(distance_list) else float("inf")

        if distance_list and dist > max_distance:
            continue

        out.append(meta)

    return out


def list_all_images_metadata(book_id: str) -> list[Dict[str, Any]]:
    """Return metadata for every image indexed for this book (for Gemini figure selection)."""
    client = _client()
    name = _image_collection_name(book_id)
    try:
        coll = client.get_collection(name=name)
    except Exception:
        return []
    try:
        data = coll.get(include=["metadatas"])
    except Exception:
        return []
    metas = data.get("metadatas") or []
    return [m for m in metas if m and (m.get("image_path") or "").strip()]