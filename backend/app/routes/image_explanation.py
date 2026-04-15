"""POST /api/image-explanation — multimodal explanation for one retrieved image."""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.config import GEMINI_IMAGE_EXPLAIN_API_KEY, IMAGE_DIR
from app.db import get_book
from app.models import ImageExplanationRequest, ImageExplanationResponse
from app.services.image_explain import explain_image_multimodal, guess_mime

router = APIRouter(prefix="/api", tags=["image-explanation"])


def _resolve_book_image_file(book_id: str, image_path: str) -> Path:
    p = (image_path or "").strip()
    if not p:
        raise HTTPException(400, "image_path is required")
    if not p.startswith("/"):
        p = "/" + p
    prefix = f"/uploads/images/{book_id}/"
    if not p.startswith(prefix):
        raise HTTPException(400, "image_path does not belong to this book")
    name = p[len(prefix) :]
    if not name or ".." in name or "/" in name:
        raise HTTPException(400, "invalid image_path")

    full = (IMAGE_DIR / book_id / name).resolve()
    allowed = (IMAGE_DIR / book_id).resolve()
    if not str(full).startswith(str(allowed)) or not full.is_file():
        raise HTTPException(404, "image file not found")
    return full


@router.post("/image-explanation", response_model=ImageExplanationResponse)
def image_explanation(req: ImageExplanationRequest):
    if not GEMINI_IMAGE_EXPLAIN_API_KEY:
        raise HTTPException(
            503,
            "Image explanation is not configured. Set GEMINI_IMAGE_EXPLAIN_API_KEY in the backend environment.",
        )

    book = get_book(req.book_id)
    if not book:
        raise HTTPException(404, "Book not found")

    path = _resolve_book_image_file(req.book_id, req.image_path)
    data = path.read_bytes()
    if not data:
        raise HTTPException(400, "empty image file")

    mime = guess_mime(path)
    title = (req.title or "").strip() or None

    explanation = explain_image_multimodal(req.question, data, mime, title=title)
    if not explanation:
        raise HTTPException(502, "Could not generate an explanation for this image.")

    return ImageExplanationResponse(explanation=explanation)
