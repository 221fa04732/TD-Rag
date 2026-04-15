"""Cross-encoder reranker: score (query, passage) pairs and return top-k chunks to reduce noise."""
import logging
from typing import Any, List

from app.config import RERANKER_MODEL, TOP_K_AFTER_RERANK

logger = logging.getLogger(__name__)

_reranker = None


def _get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder(RERANKER_MODEL)
    return _reranker


def rerank(query: str, chunks: List[dict[str, Any]], top_k: int = None) -> List[dict[str, Any]]:
    """
    Rerank chunks by relevance to the query using a cross-encoder.
    chunks: list of dicts with "text" and "metadata".
    Returns top_k chunks (default from config) in order of relevance.
    """
    if not chunks or not query.strip():
        return chunks
    top_k = top_k if top_k is not None else TOP_K_AFTER_RERANK
    top_k = min(top_k, len(chunks))

    try:
        model = _get_reranker()
        pairs = [(query.strip(), c.get("text", "")) for c in chunks]
        scores = model.predict(pairs)
        if hasattr(scores, "tolist"):
            scores = scores.tolist()
        indexed = list(zip(scores, range(len(chunks))))
        indexed.sort(key=lambda x: x[0], reverse=True)
        return [chunks[i] for _, i in indexed[:top_k]]
    except Exception as e:
        logger.warning("Reranker failed, returning original order: %s", e)
        return chunks[:top_k]
