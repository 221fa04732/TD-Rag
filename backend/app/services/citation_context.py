"""
Locate the user-provided citation inside the textbook PDF text and take ~N lines above
and below so image retrieval embeddings match queries in surrounding context, not the
citation snippet alone.
"""

import re
from typing import Optional, Tuple

from app.config import (
    IMAGE_CITATION_CONTEXT_LINES,
    IMAGE_EMBEDDING_INPUT_MAX_CHARS,
    PDF_DIR,
)
from app.services.pdf import extract_full_text


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def load_book_full_text(pdf_filename: str, book_id: str) -> str:
    """Concatenate all page text for one PDF."""
    if not pdf_filename:
        return ""
    path = PDF_DIR / book_id / pdf_filename
    if not path.is_file():
        return ""
    pages = extract_full_text(path)
    return "\n\n".join(text for _, text in pages if text and text.strip())


def extract_surrounding_context(
    full_text: str,
    citation: str,
    n_lines: int,
) -> Optional[Tuple[str, str, str]]:
    """
    Locate citation in full_text (flexible whitespace), then take up to n_lines
    before and after in the original line breaks.
    """
    cite = (citation or "").strip()
    if not cite or not full_text.strip():
        return None

    words = cite.split()
    if len(words) < 2:
        return None

    start: Optional[int] = None
    end: Optional[int] = None
    for take in range(min(len(words), 30), 1, -1):
        pattern = r"[\s\n]+".join(re.escape(w) for w in words[:take])
        m = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
        if m:
            start, end = m.start(), m.end()
            break

    if start is None or end is None:
        return None

    before_text = full_text[:start]
    after_text = full_text[end:]
    before_lines = before_text.splitlines()[-n_lines:]
    after_lines = after_text.splitlines()[:n_lines]
    matched = full_text[start:end]
    return (
        "\n".join(before_lines),
        matched,
        "\n".join(after_lines),
    )


def _pack_for_embedding(
    title: str,
    anchor: str,
    before: str,
    after: str,
    n_lines: int,
    max_chars: int,
) -> str:
    """
    Pack title, matched anchor, and nearest context (end of 'before', start of 'after')
    into a single string that fits embedding model limits.
    """
    # Nearest to the figure: last N lines before anchor, first N lines after anchor
    bl = before.splitlines()
    al = after.splitlines()
    tail_before = "\n".join(bl[-n_lines:]) if bl else ""
    head_after = "\n".join(al[:n_lines]) if al else ""

    parts = [
        f"TITLE: {title}",
        f"CITATION_ANCHOR:\n{anchor}",
        f"TEXT_ABOVE_FIGURE (up to {n_lines} lines, nearest to figure):\n{tail_before}",
        f"TEXT_BELOW_FIGURE (up to {n_lines} lines):\n{head_after}",
    ]
    s = "\n\n".join(parts)
    if len(s) <= max_chars:
        return s
    # Trim context sections from the middle outward; keep title + anchor
    head_room = max_chars - len(title) - len(anchor) - 80
    if head_room < 200:
        return s[:max_chars]
    half = head_room // 2
    tb = tail_before[:half] if tail_before else ""
    ha = head_after[:half] if head_after else ""
    s2 = "\n\n".join(
        [
            f"TITLE: {title}",
            f"CITATION_ANCHOR:\n{anchor}",
            f"TEXT_ABOVE_FIGURE:\n{tb}",
            f"TEXT_BELOW_FIGURE:\n{ha}",
        ]
    )
    return s2[:max_chars]


def build_image_embedding_document(
    book_id: str,
    pdf_filename: str,
    title: str,
    citation: str,
    description: str,
) -> str:
    """
    Text used for the image embedding: title plus book-matched context above/below citation.
    Falls back to title + citation/description if the PDF cannot be read or citation is not found.
    """
    title = (title or "").strip()
    body = (description or "").strip() if (description or "").strip() else (citation or "").strip()
    anchor_for_search = (citation or "").strip() or body

    full_text = load_book_full_text(pdf_filename, book_id)
    n = IMAGE_CITATION_CONTEXT_LINES
    max_c = IMAGE_EMBEDDING_INPUT_MAX_CHARS

    if full_text.strip() and anchor_for_search:
        ctx = extract_surrounding_context(full_text, anchor_for_search, n)
        if ctx:
            before, anchor, after = ctx
            return _pack_for_embedding(title, anchor, before, after, n, max_c)

    return f"TITLE: {title}\n\nCITATION_FOR_RETRIEVAL:\n{body}"[:max_c]


def build_figure_embedding_document(title: str, figure_ref: str) -> str:
    """
    Index images by title + figure label only (no PDF citation paste).
    Wording helps match book text that cites figures (e.g. 'Figure 2.1', 'Fig. 2.1').
    """
    t = (title or "").strip()
    f = (figure_ref or "").strip()
    return (
        f"TITLE: {t}\n"
        f"FIGURE_REFERENCE: {f}\n"
        f"Labels: {t}; {f}; figure {f}"
    )
