"""Simple JSON-based storage for book and image metadata (no SQLite for minimal deps)."""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
import uuid
from app.config import BASE_DIR

DATA_FILE = BASE_DIR / "data" / "books.json"


def _ensure_data_dir():
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("{}", encoding="utf-8")


def _load() -> dict:
    _ensure_data_dir()
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def _save(data: dict) -> None:
    _ensure_data_dir()
    DATA_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def create_book(title: str, pdf_filename: str) -> str:
    """Create a book record. Returns book_id."""
    data = _load()
    book_id = str(uuid.uuid4())
    data[book_id] = {
        "id": book_id,
        "title": title,
        "pdf_filename": pdf_filename,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    _save(data)
    return book_id


def get_book(book_id: str) -> Optional[dict]:
    data = _load()
    return data.get(book_id)


def list_books() -> list[dict]:
    data = _load()
    return list(data.values())
