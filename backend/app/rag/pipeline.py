import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.rag.chunker import chunk_pages
from app.rag.pdf_loader import extract_pdf_text
from app.rag.vector_store import vector_store
from app.storage import database


async def ingest_pdf(file: UploadFile, user_id: str) -> dict:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise ValueError("Only PDF files are supported.")

    doc_id = str(uuid.uuid4())
    safe_name = Path(file.filename).name
    output_path = settings.upload_dir / f"{doc_id}_{safe_name}"

    size = 0
    with output_path.open("wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > settings.max_upload_mb * 1024 * 1024:
                output_path.unlink(missing_ok=True)
                raise ValueError(f"PDF exceeds {settings.max_upload_mb} MB limit.")
            buffer.write(chunk)

    pages = extract_pdf_text(output_path)
    chunks = chunk_pages(pages)
    if not chunks:
        raise ValueError("Could not create useful chunks from the PDF.")

    vector_store.add_chunks(user_id, doc_id, chunks)
    doc = {
        "id": doc_id,
        "user_id": user_id,
        "filename": safe_name,
        "title": Path(safe_name).stem,
        "chunk_count": len(chunks),
    }
    database.add_document(doc)
    return doc


def reset_document_artifacts(document_id: str) -> None:
    for path in settings.upload_dir.glob(f"{document_id}_*"):
        path.unlink(missing_ok=True)
    for collection_path in (
        vector_store._base_path("default", document_id),
        vector_store._legacy_base_path("default", document_id),
    ):
        if collection_path.exists():
            shutil.rmtree(collection_path)
