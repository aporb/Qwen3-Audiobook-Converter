"""Book upload and metadata endpoints."""

import json
import shutil
import uuid

from fastapi import APIRouter, HTTPException, Request, UploadFile, File

from backend.engine import extract_book_metadata
from backend.schemas.book import BookUploadResponse, BookMetadataResponse, ChapterInfo

router = APIRouter(prefix="/api/books", tags=["books"])

# In-memory book registry (book_id → metadata dict)
_books: dict[str, dict] = {}


@router.post("/upload", response_model=BookUploadResponse)
async def upload_book(request: Request, file: UploadFile = File(...)):
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    if ext not in ("epub", "pdf", "txt"):
        raise HTTPException(status_code=400, detail=f"Unsupported format: .{ext}")

    book_id = uuid.uuid4().hex[:12]
    uploads_dir = request.state.uploads_dir
    dest = uploads_dir / f"{book_id}.{ext}"

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    meta = extract_book_metadata(dest)

    chapters = [
        ChapterInfo(id=ch["id"], title=ch["title"], word_count=ch["word_count"])
        for ch in meta.chapters
    ]

    _books[book_id] = {
        "path": str(dest),
        "title": meta.title,
        "author": meta.author,
        "format": meta.format,
        "total_words": meta.total_words,
        "has_cover": meta.cover_image is not None,
        "cover_image": meta.cover_image,
        "chapters": [ch.model_dump() for ch in chapters],
    }

    return BookUploadResponse(
        book_id=book_id,
        title=meta.title,
        author=meta.author,
        format=meta.format,
        total_words=meta.total_words,
        has_cover=meta.cover_image is not None,
        chapters=chapters,
        cover_image=meta.cover_image,
    )


@router.get("/{book_id}/metadata", response_model=BookMetadataResponse)
async def get_metadata(book_id: str):
    if book_id not in _books:
        raise HTTPException(status_code=404, detail="Book not found")
    b = _books[book_id]
    return BookMetadataResponse(
        book_id=book_id,
        title=b["title"],
        author=b["author"],
        format=b["format"],
        total_words=b["total_words"],
        has_cover=b["has_cover"],
        chapters=[ChapterInfo(**ch) for ch in b["chapters"]],
    )


def get_book_path(book_id: str) -> str:
    if book_id not in _books:
        raise HTTPException(status_code=404, detail="Book not found")
    return _books[book_id]["path"]
