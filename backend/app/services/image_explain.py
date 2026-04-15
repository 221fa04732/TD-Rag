"""Multimodal Gemini: explain a retrieved textbook image in context of the user question."""

import base64
import json
import logging
import mimetypes
import urllib.request
from pathlib import Path
from typing import Optional

from app.config import (
    GEMINI_IMAGE_EXPLAIN_API_KEY,
    GEMINI_IMAGE_EXPLAIN_MODEL,
    MAX_IMAGE_EXPLAIN_TOKENS,
)

logger = logging.getLogger(__name__)

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
_CACHED_IMAGE_EXPLAIN_MODEL: Optional[str] = None


def _get_image_explain_model() -> str:
    """Pick a vision-capable Gemini model for the image-explain key."""
    global _CACHED_IMAGE_EXPLAIN_MODEL

    if GEMINI_IMAGE_EXPLAIN_MODEL:
        return GEMINI_IMAGE_EXPLAIN_MODEL.replace("models/", "", 1)

    if _CACHED_IMAGE_EXPLAIN_MODEL:
        return _CACHED_IMAGE_EXPLAIN_MODEL

    if not GEMINI_IMAGE_EXPLAIN_API_KEY:
        return "gemini-1.5-flash"

    try:
        url = f"{_GEMINI_BASE}/models?key={GEMINI_IMAGE_EXPLAIN_API_KEY}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        for m in data.get("models") or []:
            name = m.get("name") or ""
            if not name.startswith("models/"):
                continue
            methods = m.get("supportedGenerationMethods") or []
            if "generateContent" in methods and "gemini" in name.lower():
                _CACHED_IMAGE_EXPLAIN_MODEL = name.replace("models/", "", 1)
                return _CACHED_IMAGE_EXPLAIN_MODEL
    except Exception as e:
        logger.warning("Could not list Gemini models for image explain: %s", e)

    return "gemini-1.5-flash"


def explain_image_multimodal(
    question: str,
    image_bytes: bytes,
    mime_type: str,
    title: Optional[str] = None,
) -> Optional[str]:
    """
    Ask Gemini (vision) for a short, structured explanation tied to the question and image.
    Uses GEMINI_IMAGE_EXPLAIN_API_KEY only.
    """
    if not GEMINI_IMAGE_EXPLAIN_API_KEY:
        return None

    model = _get_image_explain_model()
    title_line = f"\nImage title (from upload): {title}\n" if (title or "").strip() else ""

    instruction = f"""You describe a textbook figure for a student. Be **brief and direct**.

Student question:
\"\"\"{question}\"\"\"{title_line}

**Length:** about **10–20 lines total** (not more). No long essays.

**Content:** Stay tied to the question. Say **only what the picture shows**—components, labels you can read, arrows, axes, structure, and how parts relate. Straight to the point.

**Format (use several of these, not all if not needed):**
- Start with **one short line** summarizing what the figure is (if obvious).
- Use **bullet points** (`- item`) for lists of parts, steps, or features.
- Use **numbered lists** only for clear sequences.
- Use **bold** for key terms sparingly.
- Optional: a tiny `##` section heading only if it helps scanability (at most one).

**Rules:**
- Do not invent labels or details not visible in the image.
- If something is unclear or cropped, one short honest note is enough.
- No preamble (\"Here is…\"). No external citations.

Output **markdown only** (bullets, bold, optional one `##`).
"""

    b64 = base64.standard_b64encode(image_bytes).decode("ascii")

    body = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": instruction},
                    {
                        "inline_data": {
                            "mime_type": mime_type or "image/jpeg",
                            "data": b64,
                        }
                    },
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.25,
            "topP": 0.9,
            "maxOutputTokens": MAX_IMAGE_EXPLAIN_TOKENS,
        },
    }

    try:
        url = f"{_GEMINI_BASE}/models/{model}:generateContent?key={GEMINI_IMAGE_EXPLAIN_API_KEY}"
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            out = json.loads(resp.read().decode())

        text = (
            (out.get("candidates") or [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        if isinstance(text, str) and text.strip():
            return text.strip()
    except Exception as e:
        logger.warning("Gemini image explanation failed: %s", e)

    return None


def guess_mime(path: Path) -> str:
    mt, _ = mimetypes.guess_type(str(path))
    if mt and mt.startswith("image/"):
        return mt
    ext = path.suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(ext, "image/jpeg")
