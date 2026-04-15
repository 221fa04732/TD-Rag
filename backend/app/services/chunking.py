"""Section-aware text chunking for RAG. Attaches section headers to chunks."""
import re
from typing import List, Optional, Tuple

from app.config import CHUNK_SIZE, CHUNK_OVERLAP


def _looks_like_section_header(line: str) -> bool:
    """Heuristic: line is a section title (e.g. '1.3 SECURITY ATTACKS', 'Passive Attacks')."""
    s = line.strip()
    if not s or len(s) > 120:
        return False
    # Numbered section: "1.3 TITLE" or "1.3.1 Subsection"
    if re.match(r"^\d+(\.\d+)*\s+\S", s):
        return True
    # Short line, no sentence end (no period at end), often title case or all caps
    if s.endswith(".") or s.endswith("?") or s.endswith("!"):
        return False
    if len(s) < 80 and (s.isupper() or (len(s) > 2 and s[0].isupper() and not s.endswith("."))):
        return True
    return False


def _page_to_section_blocks(text: str) -> List[Tuple[str, str]]:
    """Split page text into (section_title, content) blocks. Section title may be empty."""
    blocks: List[Tuple[str, str]] = []
    paragraphs = re.split(r"\n\s*\n", text)
    current_section = ""
    current_content: List[str] = []

    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if _looks_like_section_header(p):
            if current_content:
                blocks.append((current_section, "\n\n".join(current_content)))
                current_content = []
            current_section = p
        else:
            current_content.append(p)

    if current_content:
        blocks.append((current_section, "\n\n".join(current_content)))

    return blocks


def chunk_text(
    text: str,
    page_number: Optional[int] = None,
    section_aware: bool = True,
) -> List[Tuple[str, dict]]:
    """
    Split text into overlapping chunks. If section_aware, first split into section blocks
    then chunk each block and attach section + page to metadata. Optionally prefix chunk
    with "SECTION: {section_title}" for better embedding relevance.
    """
    if not text.strip():
        return []

    if not section_aware:
        return _chunk_plain(text, page_number, "")

    blocks = _page_to_section_blocks(text)
    all_chunks: List[Tuple[str, dict]] = []
    for section_title, block_text in blocks:
        if not block_text.strip():
            continue
        for chunk_str, meta in _chunk_plain(block_text, page_number, section_title):
            # Prefix chunk with section so embeddings are section-aware
            if section_title:
                chunk_for_store = f"SECTION: {section_title}\n\n{chunk_str}"
            else:
                chunk_for_store = chunk_str
            meta["section"] = section_title
            all_chunks.append((chunk_for_store, meta))
    return all_chunks


def _chunk_plain(
    text: str,
    page_number: Optional[int],
    section_title: str,
) -> List[Tuple[str, dict]]:
    """Core chunking: split by paragraphs with overlap. Metadata has page_number and section."""
    paragraphs = re.split(r"\n\s*\n", text)
    chunks = []
    current = []
    current_len = 0
    meta = {"page_number": page_number, "section": section_title}

    def flush():
        nonlocal current, current_len
        if current:
            chunk_text_str = "\n\n".join(current)
            chunks.append((chunk_text_str, {**meta}))
            overlap_len = 0
            overlap_items = []
            for p in reversed(current):
                if overlap_len + len(p) + 2 <= CHUNK_OVERLAP:
                    overlap_items.append(p)
                    overlap_len += len(p) + 2
                else:
                    break
            current = list(reversed(overlap_items))
            current_len = sum(len(p) for p in current) + 2 * (len(current) - 1) if current else 0

    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if current_len + len(p) + 2 <= CHUNK_SIZE:
            current.append(p)
            current_len += len(p) + (2 if current else 0)
        else:
            if current and current_len + len(p) + 2 > CHUNK_SIZE:
                flush()
            if len(p) > CHUNK_SIZE:
                flush()
                sentences = re.split(r"(?<=[.!?])\s+", p)
                for s in sentences:
                    if current_len + len(s) + 1 <= CHUNK_SIZE:
                        current.append(s)
                        current_len += len(s) + 1
                    else:
                        flush()
                        current = [s]
                        current_len = len(s)
            else:
                current.append(p)
                current_len += len(p) + 2
    flush()
    return chunks
