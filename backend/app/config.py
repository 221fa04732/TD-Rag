"""App configuration: paths, embedding model, Chroma."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env so GEMINI_API_KEY is available
BASE_DIR = Path(__file__).resolve().parent.parent  # backend/

_env_files = [
    BASE_DIR / ".env",
    BASE_DIR.parent / ".env",
    Path.cwd() / ".env",
]

_env_loaded = None
for _f in _env_files:
    if _f.exists():
        load_dotenv(_f, override=True)
        _env_loaded = str(_f)
        break

if _env_loaded is None:
    load_dotenv()
    _env_loaded = "(current working directory)"

# Base paths
UPLOAD_DIR = BASE_DIR / "uploads"
PDF_DIR = UPLOAD_DIR / "pdfs"
IMAGE_DIR = UPLOAD_DIR / "images"
# ChromaDB must be writable. Override with CHROMA_DIR env if you get "readonly database".
CHROMA_DIR = Path(os.environ.get("CHROMA_DIR", "")).resolve() if os.environ.get("CHROMA_DIR") else BASE_DIR / "chroma_db"

# Ensure directories exist
for d in (UPLOAD_DIR, PDF_DIR, IMAGE_DIR, CHROMA_DIR):
    d.mkdir(parents=True, exist_ok=True)


# =============================
# Embedding Configuration
# =============================

# Embedding model (local)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

EMBEDDING_QUERY_PREFIX = ""
EMBEDDING_PASSAGE_PREFIX = ""


# =============================
# Chunking Configuration
# =============================

# Large chunks work best for textbooks
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


# =============================
# Retrieval Configuration
# =============================

# Retrieve → rerank → select: fetch 12, rerank, send top 5 to LLM
TOP_K_TEXT = 12          # retrieve this many chunks from Chroma
TOP_K_AFTER_RERANK = 5   # keep this many after cross-encoder rerank

# When indexing an image, match citation in the PDF text and embed this many lines above/below.
IMAGE_CITATION_CONTEXT_LINES = int(os.environ.get("IMAGE_CITATION_CONTEXT_LINES", "20"))
# Embedding models have short sequence limits; pack title + anchor + context into this budget.
IMAGE_EMBEDDING_INPUT_MAX_CHARS = int(os.environ.get("IMAGE_EMBEDDING_INPUT_MAX_CHARS", "3500"))

# Cross-encoder reranker: refines retrieval by scoring (query, chunk) pairs
RERANKER_MODEL = "BAAI/bge-reranker-base"

# Gemini figure string → uploaded image match (0–100 score); lower = accept more fuzzy matches
FIGURE_MATCH_MIN_SCORE = float(os.environ.get("FIGURE_MATCH_MIN_SCORE", "68"))

# Relevance threshold (Chroma L2 on normalized embeddings; ~1.0 was too strict for image vs long query text)
RELEVANCE_MAX_DISTANCE_TEXT = 1.4
RELEVANCE_MAX_DISTANCE_IMAGE = float(os.environ.get("RELEVANCE_MAX_DISTANCE_IMAGE", "1.45"))


# =============================
# Gemini API Configuration
# =============================

GEMINI_API_KEY = (
    os.environ.get("GEMINI_API_KEY")
    or os.environ.get("GEMINI_API_KEY ")
    or ""
).strip()

# Recommended Gemini model
GEMINI_MODEL = "gemini-pro"

# Multimodal image explanations (separate key; vision-capable model recommended)
GEMINI_IMAGE_EXPLAIN_API_KEY = (os.environ.get("GEMINI_IMAGE_EXPLAIN_API_KEY") or "").strip()
GEMINI_IMAGE_EXPLAIN_MODEL = (os.environ.get("GEMINI_IMAGE_EXPLAIN_MODEL") or "").strip()
# Short image explanations (~10–20 lines); raise if you change the prompt to long form
MAX_IMAGE_EXPLAIN_TOKENS = int(os.environ.get("MAX_IMAGE_EXPLAIN_TOKENS", "1024"))


# =============================
# Generation Settings
# =============================

# Lower temperature → stable RAG answers
TEMPERATURE = 0.2

# nucleus sampling
TOP_P = 0.9

# Maximum tokens for generated answer
# Supports detailed explanations (~2 pages)
MAX_ANSWER_TOKENS = 1600