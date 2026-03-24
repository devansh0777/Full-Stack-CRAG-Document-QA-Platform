from typing import Any

import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.embeddings_service import embed_text


def retrieve_document_chunks(
    db: Session,
    user_id: int,
    question: str,
    document_ids: list[int] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    question_embedding = embed_text(question)
    distance_expr = DocumentChunk.embedding.cosine_distance(question_embedding)
    query = (
        db.query(DocumentChunk, Document, distance_expr.label("distance"))
        .join(Document, Document.id == DocumentChunk.document_id)
        .filter(Document.user_id == user_id)
    )
    if document_ids:
        query = query.filter(Document.id.in_(document_ids))

    results = query.order_by("distance").limit(limit or settings.top_k).all()
    items = []
    for chunk, document, distance in results:
        items.append(
            {
                "chunk_id": chunk.id,
                "document_id": document.id,
                "document_name": document.filename,
                "content": chunk.content,
                "page_number": chunk.page_number,
                "score": float(1 - distance),
            }
        )
    return items


def search_web(question: str) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    with DDGS() as ddgs:
        for item in ddgs.text(question, max_results=settings.web_search_results):
            results.append(
                {
                    "title": item.get("title", "Web result"),
                    "url": item.get("href", ""),
                    "snippet": item.get("body", ""),
                }
            )
    return results


def fetch_web_context(results: list[dict[str, str]]) -> list[dict[str, str]]:
    contexts: list[dict[str, str]] = []
    headers = {"User-Agent": "Mozilla/5.0"}
    for item in results:
        url = item.get("url")
        if not url:
            continue
        try:
            response = requests.get(url, headers=headers, timeout=8)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            text = " ".join(soup.stripped_strings)
            contexts.append(
                {
                    "title": item["title"],
                    "url": url,
                    "snippet": item["snippet"],
                    "content": text[:4000],
                }
            )
        except requests.RequestException:
            continue
    return contexts
