from pydantic import BaseModel


class CharacterInfo(BaseModel):
    name: str
    description: str
    line_count: int
    sample_lines: list[str]


class AnalyzeRequest(BaseModel):
    book_id: str


class AnalyzeResponse(BaseModel):
    characters: list[CharacterInfo]


class VoiceAssignment(BaseModel):
    character_name: str
    voice: str
    engine: str = "mlx"


class AssignVoicesRequest(BaseModel):
    book_id: str
    assignments: list[VoiceAssignment]
