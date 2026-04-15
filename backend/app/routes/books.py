"""Book upload and list."""
from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
from app.config import PDF_DIR
from app.db import create_book, list_books, get_book
from app.services.pdf import extract_full_text
from app.services.chunking import chunk_text
from app.services.content_filter import is_noise_chunk
from app.services.vector_store import init_text_collection, add_text_chunks

router = APIRouter(prefix="/api/books", tags=["books"])


@router.post("/upload")
async def upload_book(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are allowed")
    book_id = create_book(title=file.filename.replace(".pdf", ""), pdf_filename=file.filename)
    pdf_path = PDF_DIR / book_id
    pdf_path.mkdir(parents=True, exist_ok=True)
    out_path = pdf_path / file.filename
    content = await file.read()
    out_path.write_bytes(content)

    pages = extract_full_text(out_path)
    all_chunks = []
    all_metas = []
    for page_num, text in pages:
        for chunk, meta in chunk_text(text, page_num):
            if is_noise_chunk(chunk):
                continue
            all_chunks.append(chunk)
            all_metas.append(meta)

    init_text_collection(book_id)
    add_text_chunks(book_id, all_chunks, all_metas)

    return {"book_id": book_id, "title": file.filename.replace(".pdf", ""), "message": "PDF processed. Add images (file + title + figure label, e.g. Fig. 2.1) for this book."}


@router.get("")
def get_books():
    return {"books": list_books()}


@router.get("/{book_id}")
def get_book_info(book_id: str):
    book = get_book(book_id)
    if not book:
        raise HTTPException(404, "Book not found")
    return book
