"""Casting director endpoints — AI character detection + voice assignment."""

from fastapi import APIRouter, HTTPException, Request

from backend.routers.books import get_book_path
from backend.schemas.casting import (
    AnalyzeRequest, AnalyzeResponse, AssignVoicesRequest, CharacterInfo,
)
from backend.services.casting_service import analyze_characters

router = APIRouter(prefix="/api/casting", tags=["casting"])

# In-memory voice assignments
_assignments: dict[str, list[dict]] = {}


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest, request: Request):
    book_path = get_book_path(req.book_id)
    api_key: str | None = request.headers.get("X-OpenAI-Key")
    try:
        raw = await analyze_characters(book_path, api_key=api_key)
        characters = [
            CharacterInfo(
                name=ch.get("name", "Unknown"),
                description=ch.get("description", ""),
                line_count=len(ch.get("sample_lines", [])),
                sample_lines=ch.get("sample_lines", []),
            )
            for ch in raw
        ]
        return AnalyzeResponse(characters=characters)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@router.post("/assign-voices")
async def assign_voices(req: AssignVoicesRequest):
    _assignments[req.book_id] = [a.model_dump() for a in req.assignments]
    return {"status": "ok", "assignments": len(req.assignments)}


def get_assignments(book_id: str) -> list[dict]:
    """Return saved voice assignments for a book, or empty list."""
    return _assignments.get(book_id, [])
