"""Image upload: single or bulk. Bulk: filename `Figure 1.1 (Title).png` → figure_ref + title."""
from typing import Any, List, Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pathlib import Path
import uuid
from app.config import IMAGE_DIR
from app.db import get_book
from app.services.citation_context import (
    build_figure_embedding_document,
    build_image_embedding_document,
)
from app.services.upload_filename import parse_figure_upload_filename
from app.services.vector_store import add_image_record

router = APIRouter(prefix="/api/books", tags=["images"])

ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


async def _persist_image_bytes(
    book_id: str,
    book: dict,
    content: bytes,
    ext: str,
    title: str,
    figure_ref: str,
    citation: str = "",
    description: str = "",
    page_ref: Optional[str] = None,
) -> dict[str, Any]:
    pdf_filename = (book.get("pdf_filename") or "").strip()
    if citation or description:
        embedding_document = build_image_embedding_document(
            book_id,
            pdf_filename,
            title,
            citation,
            description,
        )
    else:
        embedding_document = build_figure_embedding_document(title, figure_ref)

    img_dir = IMAGE_DIR / book_id
    img_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}{ext}"
    img_path = img_dir / safe_name
    img_path.write_bytes(content)

    rel_path = f"/uploads/images/{book_id}/{safe_name}"
    add_image_record(
        book_id,
        rel_path,
        title,
        citation=citation,
        description=description,
        page_ref=page_ref.strip() if page_ref else None,
        embedding_document=embedding_document,
        figure_ref=figure_ref,
    )

    return {
        "message": "Image added.",
        "image_path": rel_path,
        "title": title,
        "figure_ref": figure_ref,
    }


@router.post("/{book_id}/images")
async def add_image(
    book_id: str,
    file: UploadFile = File(...),
    title: str = Form(""),
    figure_ref: str = Form(""),
    citation: str = Form(""),
    description: str = Form(""),
    page_ref: str = Form(""),
):
    book = get_book(book_id)
    if not book:
        raise HTTPException(404, "Book not found")

    if not file.filename:
        raise HTTPException(400, "No file provided")
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXT:
        raise HTTPException(400, f"Allowed image types: {', '.join(ALLOWED_IMAGE_EXT)}")

    title = (title or "").strip()
    figure_ref = (figure_ref or "").strip()
    citation = (citation or "").strip()
    description = (description or "").strip()

    if not title:
        raise HTTPException(400, "Title is required for each image.")
    if not figure_ref:
        raise HTTPException(
            400,
            "Figure reference is required (e.g. Fig. 2.1, Figure 3.2a).",
        )

    content = await file.read()
    return await _persist_image_bytes(
        book_id,
        book,
        content,
        ext,
        title,
        figure_ref,
        citation=citation,
        description=description,
        page_ref=page_ref.strip() or None,
    )


@router.post("/{book_id}/images/bulk")
async def add_images_bulk(
    book_id: str,
    files: List[UploadFile] = File(...),
):
    """
    Upload many images at once. Each file name (without extension) must be::

        Figure 1.1 (Short title of the image)

    Text before ``(`` → figure_ref; text inside ``()`` → title.
    """
    book = get_book(book_id)
    if not book:
        raise HTTPException(404, "Book not found")

    if not files:
        raise HTTPException(400, "No files provided.")

    results: List[dict[str, Any]] = []
    errors: List[dict[str, str]] = []

    for f in files:
        name = f.filename or ""
        stem = Path(name).stem
        ext = Path(name).suffix.lower()

        if not ext or ext not in ALLOWED_IMAGE_EXT:
            errors.append(
                {
                    "filename": name,
                    "reason": f"Unsupported or missing extension (use {', '.join(sorted(ALLOWED_IMAGE_EXT))}).",
                }
            )
            continue

        try:
            figure_ref, title = parse_figure_upload_filename(stem)
        except ValueError as e:
            errors.append({"filename": name, "reason": str(e)})
            continue

        try:
            content = await f.read()
        except Exception as e:
            errors.append({"filename": name, "reason": f"Read failed: {e}"})
            continue

        if not content:
            errors.append({"filename": name, "reason": "Empty file."})
            continue

        try:
            saved = await _persist_image_bytes(
                book_id,
                book,
                content,
                ext,
                title,
                figure_ref,
            )
            results.append(
                {
                    "filename": name,
                    "figure_ref": saved["figure_ref"],
                    "title": saved["title"],
                    "image_path": saved["image_path"],
                }
            )
        except Exception as e:
            errors.append({"filename": name, "reason": str(e)})

    return {
        "added": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }


@router.post("/{book_id}/images/done")
def done_adding_images(book_id: str):
    """Optional: mark that user is done adding images. No-op for now; can be used by UI."""
    book = get_book(book_id)
    if not book:
        raise HTTPException(404, "Book not found")
    return {"message": "Done. You can now query this book."}
