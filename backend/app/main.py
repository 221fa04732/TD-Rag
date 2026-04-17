"""FastAPI app: CORS, static uploads, routes."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.config import UPLOAD_DIR, GEMINI_API_KEY, GEMINI_IMAGE_EXPLAIN_API_KEY, CORS_ORIGINS
from app.routes import books, images, image_explanation, query

app = FastAPI(title="Textbook Image RAG", description="Upload PDF + images with citations, query for text and images.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    from app.config import _env_loaded
    print(f"Env loaded from: {_env_loaded}")
    if GEMINI_API_KEY:
        print("Gemini API key loaded — answer synthesis enabled.")
    else:
        print("No GEMINI_API_KEY — set it in .env for synthesized answers and figure selection.")
    if GEMINI_IMAGE_EXPLAIN_API_KEY:
        print("GEMINI_IMAGE_EXPLAIN_API_KEY loaded — multimodal image explanations enabled.")

# Mount uploads so /uploads/images/... can be loaded in frontend
uploads_path = Path(UPLOAD_DIR)
if uploads_path.exists():
    app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

app.include_router(books.router)
app.include_router(images.router)
app.include_router(image_explanation.router)
app.include_router(query.router)


@app.get("/")
def root():
    return {"message": "Textbook Image RAG API", "docs": "/docs"}


@app.get("/api/llm-status")
def llm_status():
    """Check which LLM is configured for answer synthesis."""
    return {
        "gemini_configured": bool(GEMINI_API_KEY),
        "gemini_image_explain_configured": bool(GEMINI_IMAGE_EXPLAIN_API_KEY),
    }
