"""Weather Station API — Authentication middleware."""

import secrets
from fastapi import Security, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.config import get_settings

security = HTTPBearer()


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    """Verify the Bearer token matches the configured API secret key.

    Used to protect the ingest endpoint so only Home Assistant can push data.
    """
    settings = get_settings()

    is_valid = secrets.compare_digest(
        credentials.credentials.encode("utf-8"),
        settings.api_secret_key.encode("utf-8"),
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return credentials.credentials
