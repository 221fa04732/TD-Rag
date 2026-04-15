# Textbook Image RAG (Manual Image Upload)

RAG app for **image-grounded answers from textbooks**: upload a PDF (text only), then **manually upload images** with title and description. Queries return relevant **book text** plus **matching images** (by description similarity). No image extraction from PDF; only images you upload are ever returned.

## Flow

1. **Upload PDF** → Text is extracted, chunked, embedded, and stored. No images are taken from the PDF.
2. **Add images** → For each figure/diagram you care about: upload the image file + **title** + **description** (and optional page ref). Repeat until you click **Done adding images**.
3. **Ask a question** → The system searches both book text and image descriptions, then returns relevant passages and any relevant uploaded images.

## Tech

- **Backend**: Python, FastAPI, PyMuPDF, sentence-transformers (embeddings, local), ChromaDB, **Gemini API** (answer synthesis and figure selection).
- **Frontend**: React (Vite), minimal UI.

## Setup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # for restart backend
pip install -r requirements.txt
uvicorn app.main:app --reload    # for restart backend
```
(Use `python` instead of `python3` if that’s what you have.)

Run from the `backend` directory so `app` and `uploads` resolve correctly. API: http://localhost:8000 (docs at /docs).

**Answer synthesis:** Set **`GEMINI_API_KEY`** in `backend/.env` (see [Google AI Studio](https://ai.google.dev/)). Optional: **`GEMINI_IMAGE_EXPLAIN_API_KEY`** for multimodal image explanations (see `.env.example`).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server proxies `/api` and `/uploads` to the backend.

## Usage

1. Upload a PDF textbook.
2. Select the book, then add images one by one: choose file, add title (optional) and **description** (required). Click **Add image**. Repeat as needed.
3. Click **Done adding images** when finished.
4. Type a question and click **Search**. You get a **synthesized answer** (Gemini), plus source excerpts and any matching images.


## Rules

- **Only images you uploaded** are returned; the system never generates or invents images.
- Image retrieval is based on **description (and title) embeddings**; good descriptions improve matches.

## Project layout

```
backend/
  app/
    main.py
    config.py
    models.py
    db.py
    routes/       (books, images, query)
    services/     (pdf, embeddings, chunking, vector_store, llm)
  uploads/        (pdfs/, images/) — created at runtime
  data/           books.json — created at runtime
  chroma_db/      Chroma persistence — created at runtime
frontend/
  src/
    App.jsx
    main.jsx
    index.css
```

## Optional

- **Multiple books**: Supported; each book has its own text and image collections.
- **Page references**: Use the “Page reference” field when adding an image (e.g. “Page 42”) so it appears in results.
