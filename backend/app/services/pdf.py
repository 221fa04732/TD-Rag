"""Extract text from PDF with page numbers. No image extraction."""
import fitz  # PyMuPDF
from pathlib import Path
from typing import Iterator


def extract_text_by_page(pdf_path: Path) -> Iterator[tuple[int, str]]:
    """Yield (page_number, text) for each page. 1-based page numbers."""
    doc = fitz.open(pdf_path)
    try:
        for i in range(len(doc)):
            page = doc[i]
            text = page.get_text().strip()
            yield (i + 1, text)
    finally:
        doc.close()


def extract_full_text(pdf_path: Path) -> list[tuple[int, str]]:
    """Return list of (page_number, text) for entire PDF."""
    return list(extract_text_by_page(pdf_path))
