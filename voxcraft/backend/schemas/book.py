from pydantic import BaseModel


class ChapterInfo(BaseModel):
    id: str
    title: str
    word_count: int


class BookUploadResponse(BaseModel):
    book_id: str
    title: str
    author: str
    format: str
    total_words: int
    has_cover: bool
    chapters: list[ChapterInfo]
    cover_image: str | None = None


class BookMetadataResponse(BaseModel):
    book_id: str
    title: str
    author: str
    format: str
    total_words: int
    has_cover: bool
    chapters: list[ChapterInfo]
