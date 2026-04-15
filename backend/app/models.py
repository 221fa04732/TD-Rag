"""Pydantic request/response models."""
from pydantic import BaseModel, Field
from typing import Optional


class QueryRequest(BaseModel):
    book_id: str
    question: str = Field(..., min_length=1)


class TextSection(BaseModel):
    text: str
    page_number: Optional[int] = None
    section: Optional[str] = None


class RetrievedImage(BaseModel):
    image_path: str
    title: str
    citation: str = ""  # legacy / optional extra text
    figure_ref: Optional[str] = None  # e.g. Fig. 2.1, 3.1a
    page_ref: Optional[str] = None  # optional free-text page label


class QueryResponse(BaseModel):
    answer: Optional[str] = None  # LLM-synthesized answer from book chunks (human-readable)
    text_sections: list[TextSection] = []  # Source chunks used for the answer
    images: list[RetrievedImage] = []


class ImageExplanationRequest(BaseModel):
    book_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    image_path: str = Field(..., min_length=1)
    title: Optional[str] = None


class ImageExplanationResponse(BaseModel):
    explanation: Optional[str] = None


class BookInfo(BaseModel):
    id: str
    title: str
    created_at: str
