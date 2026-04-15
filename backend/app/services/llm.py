"""
Synthesize a human-readable answer strictly from retrieved book chunks
using Gemini API.
"""

import json
import logging
import re
import urllib.request
from typing import List, Dict, Any, Optional, Tuple

from app.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    MAX_ANSWER_TOKENS,
    FIGURE_MATCH_MIN_SCORE,
)

logger = logging.getLogger(__name__)

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
_CACHED_GEMINI_MODEL: Optional[str] = None


def _get_available_gemini_model() -> Optional[str]:
    """Fetch available Gemini models that support generateContent."""
    global _CACHED_GEMINI_MODEL

    if _CACHED_GEMINI_MODEL:
        return _CACHED_GEMINI_MODEL

    if not GEMINI_API_KEY:
        return None

    try:
        url = f"{_GEMINI_BASE}/models?key={GEMINI_API_KEY}"
        req = urllib.request.Request(url, method="GET")

        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        for m in data.get("models") or []:
            name = m.get("name") or ""

            if not name.startswith("models/"):
                continue

            methods = m.get("supportedGenerationMethods") or []

            if "generateContent" in methods and "gemini" in name.lower():
                _CACHED_GEMINI_MODEL = name.replace("models/", "", 1)
                return _CACHED_GEMINI_MODEL

    except Exception as e:
        logger.warning("Could not list Gemini models: %s", e)

    return None


def _build_chunks_text(chunks: List[Dict[str, Any]]) -> str:
    """Format retrieved chunks with clear separators."""

    parts = []

    for i, r in enumerate(chunks, 1):
        text = r.get("text", "").strip()
        meta = r.get("metadata") or {}

        page = meta.get("page_number", "")
        section = meta.get("section", "")

        if not text:
            continue

        parts.append(
            f"""
---------------- EXCERPT {i} ----------------
Page: {page}
Section: {section}

{text}
---------------------------------------------
"""
        )

    return "\n".join(parts)


def _synthesize_via_gemini(prompt: str, max_output_tokens: Optional[int] = None) -> Optional[str]:
    """Call Gemini API and return generated text."""

    if not GEMINI_API_KEY:
        return None

    model = _get_available_gemini_model() or (GEMINI_MODEL or "gemini-1.5-flash")
    max_tok = max_output_tokens if max_output_tokens is not None else MAX_ANSWER_TOKENS

    try:
        url = f"{_GEMINI_BASE}/models/{model}:generateContent?key={GEMINI_API_KEY}"

        body = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.05,
                "topP": 0.9,
                "maxOutputTokens": max_tok
            }
        }

        data = json.dumps(body).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
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
        logger.warning("Gemini synthesis failed: %s", e)

    return None


def synthesize_answer(query: str, chunks: List[Dict[str, Any]]) -> Optional[str]:
    """
    Generate an answer strictly from book excerpts.
    """

    if not chunks:
        return None

    # Sort chunks by page number (maintains book order)
    chunks = sorted(
        chunks,
        key=lambda x: int((x.get("metadata") or {}).get("page_number", 0))
    )

    chunks_text = _build_chunks_text(chunks)

    if not chunks_text.strip():
        return None

    instruction = """
You are answering questions using excerpts from a textbook.

Your task is to construct a clear and complete explanation using ONLY the provided excerpts.

================ IMPORTANT RULES ================

1. The excerpts are the ONLY source of information.
2. Every statement must be supported by the excerpts.
3. Do NOT introduce outside knowledge.
4. Prefer wording from the excerpts when possible.
5. You may lightly paraphrase to improve clarity.
6. Do NOT mention the excerpts, retrieval, or sourcing in your answer.
7. Do NOT include citations of any kind: no page numbers, section names, footnotes, bracketed references (e.g. [1]), or phrases like "according to the book", "as stated on page", "see excerpt", or "source".

================ REASONING STEP (INTERNAL) ================

Before writing the answer, analyze the excerpts and internally determine:

• the main definition
• supporting explanations
• categories or types mentioned
• additional characteristics or notes

Use this internal structure to organize the explanation clearly.

================ ANSWER STYLE ================

Write like a teacher explaining a concept from a textbook.

Structure the answer clearly:

1. Definition or main concept
2. Explanation
3. Types or categories (if present)
4. Additional characteristics or notes

Formatting rules:

• Use short paragraphs
• Use bullet points when listing types
• Bold important terms when defining them

================ GROUNDING RULE ================

If the excerpts do not contain enough information to answer the question,
respond exactly with:

"The book does not contain enough information to answer this question."
"""

    prompt = f"""
{instruction}

================ BOOK EXCERPTS ================

{chunks_text}

================ USER QUESTION ================

{query}

================ FINAL ANSWER ================
Write the explanation using the structure defined above. Output only the explanation itself—no headings about sources, pages, or citations.
"""

    return _synthesize_via_gemini(prompt)


def _parse_json_from_gemini(text: str) -> Optional[dict]:
    """Extract JSON object from Gemini output (handles optional markdown fences)."""
    if not text or not text.strip():
        return None
    t = text.strip()
    if "```" in t:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", t)
        if m:
            t = m.group(1).strip()
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    try:
        start = t.find("{")
        end = t.rfind("}")
        if start >= 0 and end > start:
            return json.loads(t[start : end + 1])
    except json.JSONDecodeError:
        pass
    return None


def synthesize_answer_and_figure_refs(
    query: str,
    chunks: List[Dict[str, Any]],
    image_catalog: List[Dict[str, Any]],
) -> Tuple[Optional[str], List[str]]:
    """
    One Gemini call: human-readable answer from excerpts + which uploaded figures are relevant.
    image_catalog items should include at least figure_ref, title, image_path (metadata from Chroma).
    """
    if not chunks:
        return None, []

    if not GEMINI_API_KEY:
        ans = synthesize_answer(query, chunks)
        return ans, []

    chunks = sorted(
        chunks,
        key=lambda x: int((x.get("metadata") or {}).get("page_number", 0)),
    )
    chunks_text = _build_chunks_text(chunks)
    if not chunks_text.strip():
        return None, []

    catalog_lines = []
    catalog_json: List[Dict[str, str]] = []
    for i, m in enumerate(image_catalog, 1):
        fr = (m.get("figure_ref") or "").strip()
        ti = (m.get("title") or "").strip()
        if not fr and not ti:
            continue
        catalog_lines.append(f'{i}. figure_ref: "{fr}" | title: "{ti}"')
        catalog_json.append({"figure_ref": fr, "title": ti})

    if not catalog_json:
        ans = synthesize_answer(query, chunks)
        return ans, []

    catalog_block = "\n".join(catalog_lines)
    catalog_json_str = json.dumps(catalog_json, ensure_ascii=False, indent=2)

    instruction = """
You are answering from a textbook AND selecting which uploaded figures are relevant to the user's question.

================ PART 1 — ANSWER ================
Use ONLY the BOOK EXCERPTS below. Same rules as a teaching explanation:
- No outside knowledge; no citations/pages in the answer text.
- If excerpts are insufficient, say exactly: "The book does not contain enough information to answer this question."
- Output the answer as plain teacher-style text (paragraphs, bullets, **bold** for key terms).

================ PART 2 — FIGURES ================
The instructor uploaded figures for this book. Each entry has figure_ref (as printed in the book, e.g. "Figure 1.1") and title.

Choose ONLY figures that are **directly supported** by the excerpts in relation to the question (e.g. if the question is about passive attacks, only figures that illustrate passive attacks — not other topics).

The app will **only show** a figure if the excerpts **actually cite** that figure (e.g. "Figure 1.2" / "Fig. 1.2"). So only list figures you believe are cited in the BOOK EXCERPTS below.

- If no figure is relevant, use an empty array.
- Every value in relevant_figures MUST be copied **exactly** from the figure_ref field in the catalog (same spelling and punctuation).
- The catalog may list the **same figure_ref more than once** (different image files). Listing that figure_ref **once** in relevant_figures is enough — the app will attach every matching upload.

================ OUTPUT FORMAT ================
Return **only** valid JSON (no markdown outside the JSON) with this exact structure:
{
  "answer": "<your answer string>",
  "relevant_figures": ["Figure 1.1", "..."]
}

The relevant_figures array must contain only figure_ref strings that appear in the catalog below.
"""

    prompt = f"""{instruction}

================ UPLOADED FIGURE CATALOG (machine-readable) ================
{catalog_json_str}

================ UPLOADED FIGURE CATALOG (human-readable) ================
{catalog_block}

================ BOOK EXCERPTS ================
{chunks_text}

================ USER QUESTION ================
{query}

================ JSON OUTPUT ================
"""

    # Extra tokens for JSON wrapper + figure list
    raw = _synthesize_via_gemini(prompt, max_output_tokens=max(MAX_ANSWER_TOKENS, 2200))
    if not raw:
        ans = synthesize_answer(query, chunks)
        return ans, []

    obj = _parse_json_from_gemini(raw)
    if not obj:
        logger.warning("Gemini figure JSON parse failed; using answer-only fallback")
        ans = synthesize_answer(query, chunks)
        return ans, []

    answer = obj.get("answer")
    if isinstance(answer, str):
        answer = answer.strip() or None
    else:
        answer = None

    refs_raw = obj.get("relevant_figures")
    refs: List[str] = []
    if isinstance(refs_raw, list):
        for x in refs_raw:
            if isinstance(x, str) and x.strip():
                refs.append(x.strip())

    if not answer:
        ans = synthesize_answer(query, chunks)
        answer = ans

    return answer, refs


def _norm_figure_label(s: str) -> str:
    """Lowercase, spaces, strip leading Figure/Fig."""
    s = (s or "").lower().strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"^(figure|fig\.?)\s+", "", s)
    return s.strip()


def _split_figure_numbers(s: str) -> tuple[str, str]:
    """
    Extract main number block and optional trailing letter (e.g. '1.1', 'b' from '1.1b').
    """
    s = _norm_figure_label(s)
    m = re.search(r"(\d+(?:\.\d+)+)([a-z])?\b", s, re.I)
    if not m:
        return "", ""
    return m.group(1), (m.group(2) or "").lower()


def _tokens(s: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(t) > 1}


def _score_label_against_row(label: str, meta: Dict[str, Any]) -> float:
    """
    Score how well a Gemini label matches a catalog row (figure_ref + title).
    Higher = better. 0 = no match.
    """
    fr = (meta.get("figure_ref") or "").strip()
    ti = (meta.get("title") or "").strip()
    if not fr and not ti:
        return 0.0

    nl = _norm_figure_label(label)
    nr = _norm_figure_label(fr)
    nt = _norm_figure_label(ti)

    # Exact match on normalized figure ref (after stripping "Figure")
    if nr and nl == nr:
        return 100.0
    # Gemini sometimes echoes the title instead of figure_ref
    if nt and nl == nt:
        return 98.0
    # One string contains the other (handles "1.1" inside "figure 1.1b")
    if nr and nl and (nl in nr or nr in nl):
        return 92.0
    if nt and nl and (nl in nt or nt in nl):
        return 90.0

    # Same numeric core: 1.1 vs 1.1b, or 2.3 vs 2.3a
    num_l, suf_l = _split_figure_numbers(label)
    num_r, suf_r = _split_figure_numbers(fr)
    if num_l and num_r:
        if num_l == num_r:
            # Same base number; letter may differ (1.1 vs 1.1b)
            if not suf_l or not suf_r or suf_l == suf_r:
                return 88.0
            return 82.0
        # One number is a prefix of the other section (e.g. 2 vs 2.1) — weaker
        if num_r.startswith(num_l + ".") or num_l.startswith(num_r + "."):
            return 72.0

    # Title / label word overlap (Gemini paraphrases)
    wl, wr, wt = _tokens(label), _tokens(fr), _tokens(ti)
    for a, b in ((wl, wr), (wl, wt), (wr, wl)):
        if not a or not b:
            continue
        inter = a & b
        union = a | b
        if not union:
            continue
        j = len(inter) / len(union)
        if j >= 0.5:
            return 75.0 + 15.0 * j
        if j >= 0.25 and len(inter) >= 2:
            return 65.0 + 20.0 * j

    return 0.0


def match_figure_labels_to_catalog(
    labels: List[str],
    catalog: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Map Gemini-returned figure strings to catalog rows.
    Flexible: Figure 1.1 vs 1.1b, small typo in spacing, or title-like strings.

    If several uploads share the same figure_ref (e.g. multiple "Figure 1.1"), all that
    tie for the best score for that label are returned (not only one).
    Order: label order, then catalog order among ties. Dedupes by image_path across labels.
    """
    if not labels or not catalog:
        return []

    out: List[Dict[str, Any]] = []
    seen_paths: set[str] = set()

    for lab in labels:
        if not (lab or "").strip():
            continue
        scored: List[tuple[float, Dict[str, Any]]] = []
        for m in catalog:
            sc = _score_label_against_row(lab, m)
            if sc >= FIGURE_MATCH_MIN_SCORE:
                scored.append((sc, m))
        if not scored:
            continue
        best_score = max(s for s, _ in scored)
        for sc, m in scored:
            if sc != best_score:
                continue
            p = (m.get("image_path") or "").strip()
            if p and p not in seen_paths:
                seen_paths.add(p)
                out.append(m)

    return out


def _normalize_text_for_figure_citation(text: str) -> str:
    """Collapse odd PDF whitespace so 'Figure\\n1.2' and nbsp do not break matching."""
    t = (text or "").replace("\u00a0", " ").replace("\u200b", "").replace("\ufeff", "")
    t = re.sub(r"[\u2000-\u200a]", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def _flexible_figure_number_pattern(num: str) -> str:
    """
    Catalog stores '1.2'; extracted PDF text may use '.', '-', '–', or '·' between parts.
    """
    if not num or "." not in num:
        return re.escape(num)
    parts = num.split(".")
    sep = r"(?:[.\-–·])"
    return re.escape(parts[0]) + sep + sep.join(re.escape(p) for p in parts[1:])


def _figure_ref_cited_in_text(figure_ref: str, text: str) -> bool:
    """
    True if a textbook-style figure citation appears in text (Figure X.Y, Fig. X.Y, Figures X.Y).
    Uses numeric core from figure_ref so minor formatting differences still match.
    """
    if not (figure_ref or "").strip() or not (text or "").strip():
        return False
    text = _normalize_text_for_figure_citation(text)
    if not text:
        return False
    num, suf = _split_figure_numbers(figure_ref)
    if not num:
        return False
    num_pat = _flexible_figure_number_pattern(num)
    # Allow "Figure 1.2", "Fig. 1.2", "Fig.1.2", "FIGURES 1-2"
    prefix = r"(?i)(?:figures?|fig\.?)\s*"
    if suf:
        strict = rf"{prefix}{num_pat}(?:\s*\({re.escape(suf)}\)|\s*{re.escape(suf)})\b"
        if re.search(strict, text):
            return True
    loose = rf"{prefix}{num_pat}\b"
    return bool(re.search(loose, text))


def filter_images_by_citations_in_chunks(
    images: List[Dict[str, Any]],
    chunks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Keep only images whose figure_ref is cited in the retrieved book excerpts.
    """
    if not images or not chunks:
        return []
    full_text = "\n".join((c.get("text") or "") for c in chunks)
    out: List[Dict[str, Any]] = []
    for m in images:
        fr = (m.get("figure_ref") or "").strip()
        if fr and _figure_ref_cited_in_text(fr, full_text):
            out.append(m)
    return out