"""Query: RAG text + Gemini picks relevant figures, then we load those images from the catalog."""
from fastapi import APIRouter, HTTPException
from app.models import QueryRequest, QueryResponse, TextSection, RetrievedImage
from app.db import get_book
from app.services.embeddings import embed
from app.services.vector_store import query_text, list_all_images_metadata
from app.services.reranker import rerank
from app.services.llm import (
    synthesize_answer,
    synthesize_answer_and_figure_refs,
    match_figure_labels_to_catalog,
    filter_images_by_citations_in_chunks,
)
from app.config import TOP_K_TEXT

router = APIRouter(prefix="/api", tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    book = get_book(req.book_id)
    if not book:
        raise HTTPException(404, "Book not found")

    query_embedding = embed([req.question], is_query=True)[0]

    # Broad pool for citation matching: figure refs often sit in chunks the reranker drops
    # when optimizing for Q&A overlap.
    text_chunks_broad = query_text(req.book_id, query_embedding, top_k=TOP_K_TEXT)
    text_results = rerank(req.question, text_chunks_broad)

    text_sections = [
        TextSection(
            text=r["text"],
            page_number=int(r["metadata"].get("page_number")) if r["metadata"].get("page_number") else None,
            section=(r["metadata"].get("section") or "").strip() or None,
        )
        for r in text_results
    ]

    image_catalog = list_all_images_metadata(req.book_id)

    answer = None
    image_results: list = []

    if text_results and image_catalog:
        answer, fig_labels = synthesize_answer_and_figure_refs(
            req.question,
            text_results,
            image_catalog,
        )
        image_results = match_figure_labels_to_catalog(fig_labels, image_catalog)
        image_results = filter_images_by_citations_in_chunks(
            image_results,
            text_chunks_broad,
        )
    elif text_results:
        answer = synthesize_answer(req.question, text_results)
        image_results = []
    else:
        answer = None
        image_results = []

    images = []
    for m in image_results:
        path = m.get("image_path") or ""
        if path and not path.startswith("/"):
            path = "/" + path
        cite = (m.get("citation") or "").strip() or (m.get("description") or "").strip()
        fig = (m.get("figure_ref") or "").strip() or None
        pref = (m.get("page_ref") or "").strip() or None
        images.append(
            RetrievedImage(
                image_path=path,
                title=m.get("title") or "",
                citation=cite,
                figure_ref=fig,
                page_ref=pref,
            )
        )

    return QueryResponse(answer=answer, text_sections=text_sections, images=images)
