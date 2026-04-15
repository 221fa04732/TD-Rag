# Textbook Image RAG – Architecture (Manual Image Upload)

## Design choice

- **PDF**: Only **text** is extracted and used for RAG (no image extraction from PDF).
- **Images**: User **manually uploads** images with **title** and **description**. Descriptions are embedded and used to retrieve relevant images for a query.

## Flow

1. **Upload PDF** → Extract text → Chunk → Embed → Store in vector DB (per book).
2. **Add images** → For each image: upload file + title + description → Embed (title + description) → Store path + metadata in vector DB. User continues until they say "Done adding images".
3. **Query** → Embed query → Search **text** collection → Search **image** collection (by description) → Return relevant text + relevant images (only from stored images).

## Components

| Component        | Role |
|-----------------|------|
| FastAPI backend | Upload PDF, upload images, query; serves frontend. |
| ChromaDB        | Two collections: `text_chunks_{book_id}`, `images_{book_id}`. |
| Embeddings      | sentence-transformers (e.g. `all-MiniLM-L6-v2`) for text and image descriptions. |
| Storage         | PDFs and images on disk under `uploads/`. |
| SQLite (optional) | Book metadata (id, title, created_at) and image metadata (path, title, description). Can start with JSON/file and move to SQLite if needed. |

## Folder structure

```
backend/
  app/
    main.py           # FastAPI app, CORS, routes
    config.py         # Paths, embedding model name, Chroma path
    models.py         # Pydantic request/response models
    routes/
      books.py        # POST upload PDF, GET list books
      images.py       # POST add image (title, description), POST done
      query.py        # POST query → text + images
    services/
      pdf.py          # Extract text from PDF (PyMuPDF)
      embeddings.py   # Load model, embed text
      vector_store.py # Chroma: create/get collection, add query, add image
    db.py             # Book/image metadata (SQLite or JSON)
  requirements.txt
  uploads/            # created at runtime: pdfs/, images/{book_id}/

frontend/
  src/
    App.jsx
    components/
      BookUpload.jsx
      ImageUpload.jsx   # Add image + title + description, "Done adding images"
      QueryPanel.jsx    # Input question, show text + images
  package.json (Vite + React)
```

## API (summary)

- `POST /api/books/upload` — PDF file → create book, extract text, chunk, embed, store. Returns `book_id`.
- `GET /api/books` — List books.
- `POST /api/books/{book_id}/images` — Form: image file, title, description. Store file, embed, add to `images_{book_id}`.
- `POST /api/books/{book_id}/images/done` — Optional: mark "done adding images" (no body).
- `POST /api/query` — Body: `{ "book_id": "...", "question": "..." }`. Returns `{ "text_sections": [...], "images": [{ "path", "title", "description", "page_ref" }] }`.

## Rules

- Only return **images that were uploaded** for that book (no generated/fake images).
- Images are matched to the query via **description (and title) embeddings** only.
