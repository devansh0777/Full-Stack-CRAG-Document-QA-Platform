import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from langchain_community.document_loaders import (
    Docx2txtLoader,
    PyPDFLoader,
    TextLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.services.embeddings_service import embed_texts

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


def _ensure_upload_dir() -> Path:
    upload_dir = settings.upload_path
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def _persist_upload(file: UploadFile) -> Path:
    extension = Path(file.filename or "").suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {extension}")

    target_dir = _ensure_upload_dir()
    filename = f"{uuid4().hex}{extension}"
    destination = target_dir / filename
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return destination


def _load_documents(file_path: Path):
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        loader = PyPDFLoader(str(file_path))
    elif suffix == ".docx":
        loader = Docx2txtLoader(str(file_path))
    else:
        loader = TextLoader(str(file_path), encoding="utf-8")
    return loader.load()


def upload_document(db: Session, user: User, file: UploadFile) -> Document:
    stored_path = _persist_upload(file)
    document = Document(
        user_id=user.id,
        filename=file.filename or stored_path.name,
        content_type=file.content_type,
        file_path=str(stored_path),
    )
    db.add(document)
    db.flush()

    raw_docs = _load_documents(stored_path)
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(raw_docs)
    texts = [chunk.page_content for chunk in chunks]
    if not texts:
        raise ValueError("No text content could be extracted from the document")
    embeddings = embed_texts(texts)

    chunk_rows = []
    for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=False)):
        chunk_rows.append(
            DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk.page_content,
                page_number=chunk.metadata.get("page"),
                embedding=embedding,
            )
        )

    db.add_all(chunk_rows)
    db.commit()
    db.refresh(document)
    return document


def list_documents(db: Session, user_id: int) -> list[Document]:
    return (
        db.query(Document)
        .filter(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
        .all()
    )


def delete_document(db: Session, user_id: int, document_id: int) -> bool:
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == user_id)
        .first()
    )
    if not document:
        return False
    path = Path(document.file_path)
    db.delete(document)
    db.commit()
    if path.exists():
        path.unlink()
    return True
