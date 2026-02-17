"""License key validation via LemonSqueezy API."""

import logging

import httpx
from fastapi import APIRouter, HTTPException

from backend.config import settings
from backend.schemas.license import (
    ValidateRequest, ValidateResponse, CheckRequest, CheckResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/license", tags=["license"])

LEMONSQUEEZY_VALIDATE_URL = "https://api.lemonsqueezy.com/v1/licenses/validate"
LEMONSQUEEZY_ACTIVATE_URL = "https://api.lemonsqueezy.com/v1/licenses/activate"


async def _call_lemonsqueezy(key: str) -> dict:
    """Call LemonSqueezy license validation API."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            LEMONSQUEEZY_VALIDATE_URL,
            json={"license_key": key},
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
    data = resp.json()
    return data


def _parse_license(data: dict) -> tuple[bool, str | None, str | None]:
    """Parse LemonSqueezy response into (valid, license_type, expires_at)."""
    valid = data.get("valid", False)
    if not valid:
        return False, None, None

    meta = data.get("meta", {})
    license_key = data.get("license_key", {})

    # Determine type from variant name or product
    variant_name = meta.get("variant_name", "").lower()
    if "lifetime" in variant_name:
        license_type = "lifetime"
    else:
        license_type = "annual"

    expires_at = license_key.get("expires_at")
    return True, license_type, expires_at


@router.post("/validate", response_model=ValidateResponse)
async def validate(req: ValidateRequest):
    try:
        data = await _call_lemonsqueezy(req.key)
        valid, license_type, expires_at = _parse_license(data)
        return ValidateResponse(
            valid=valid,
            license_type=license_type,
            expires_at=expires_at,
        )
    except httpx.HTTPError as e:
        logger.error(f"LemonSqueezy API error: {e}")
        raise HTTPException(status_code=502, detail="License validation service unavailable")
    except Exception as e:
        logger.error(f"License validation failed: {e}")
        raise HTTPException(status_code=500, detail="License validation failed")


@router.post("/check", response_model=CheckResponse)
async def check(req: CheckRequest):
    """Re-validate a stored key (called on session startup)."""
    try:
        data = await _call_lemonsqueezy(req.key)
        valid, license_type, expires_at = _parse_license(data)
        return CheckResponse(
            valid=valid,
            license_type=license_type,
            expires_at=expires_at,
        )
    except Exception:
        # On error, don't block the user — return valid=false silently
        return CheckResponse(valid=False)
