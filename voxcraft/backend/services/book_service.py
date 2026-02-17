"""Book processing service — wraps engine text extraction utilities."""

from pathlib import Path

from backend.engine import (
    extract_text_from_file,
    extract_book_metadata,
    split_into_chunks,
    apply_text_cleaning,
    BookMetadata,
)


def get_book_text(
    file_path: str,
    fix_capitals: bool = True,
    remove_footnotes: bool = True,
    normalize_chars: bool = True,
) -> str:
    """Extract and clean text from a book file."""
    text = extract_text_from_file(Path(file_path))
    return apply_text_cleaning(text, fix_capitals, remove_footnotes, normalize_chars)


def get_book_metadata(file_path: str) -> BookMetadata:
    """Get metadata for a book file."""
    return extract_book_metadata(Path(file_path))


def chunk_text(text: str, chunk_size: int = 1500, max_chars: int | None = None) -> list[str]:
    """Split text into TTS-friendly chunks."""
    return split_into_chunks(text, chunk_size, max_chars)
