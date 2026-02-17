from pydantic import BaseModel


class ValidateRequest(BaseModel):
    key: str


class ValidateResponse(BaseModel):
    valid: bool
    license_type: str | None = None
    expires_at: str | None = None


class CheckRequest(BaseModel):
    key: str


class CheckResponse(BaseModel):
    valid: bool
    license_type: str | None = None
    expires_at: str | None = None
