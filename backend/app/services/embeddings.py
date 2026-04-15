"""
Embedding model wrapper (sentence-transformers).
Handles query and passage embeddings for retrieval.
"""

from sentence_transformers import SentenceTransformer
from app.config import (
    EMBEDDING_MODEL,
    EMBEDDING_QUERY_PREFIX,
    EMBEDDING_PASSAGE_PREFIX,
)

_model = None


def get_model() -> SentenceTransformer:
    """Load embedding model lazily."""
    global _model

    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)

    return _model


def embed(texts: list[str], is_query: bool = False) -> list[list[float]]:
    """Generate embeddings for texts."""

    if not texts:
        return []

    prefix = EMBEDDING_QUERY_PREFIX if is_query else EMBEDDING_PASSAGE_PREFIX

    if prefix:
        texts = [prefix + t for t in texts]

    model = get_model()

    embeddings = model.encode(
        texts,
        batch_size=32,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    if embeddings.ndim == 1:
        return [embeddings.tolist()]

    return embeddings.tolist()