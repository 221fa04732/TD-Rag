"""Filter out textbook noise (index, key terms, review questions, etc.) during ingestion."""

NOISE_PATTERNS = [
    "key terms",
    "review questions",
    "problems",
    "see also",
    "index",
    "references",
    "bibliography",
]


def is_noise_chunk(text: str) -> bool:
    """Return True if the chunk looks like index/glossary/review noise to skip embedding."""
    if not text or not text.strip():
        return True
    lower = text.lower().strip()
    return any(p in lower for p in NOISE_PATTERNS)
