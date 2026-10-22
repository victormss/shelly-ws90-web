"""Tests for API authentication and timing attack mitigation."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from app.auth import verify_api_key


@pytest.fixture
def mock_settings():
    """Mock settings with a known API key."""
    with patch("app.auth.get_settings") as mock:
        settings = MagicMock()
        settings.api_secret_key = "super-secret-token-12345"
        mock.return_value = settings
        yield settings


@pytest.mark.asyncio
async def test_verify_api_key_valid(mock_settings):
    """Correct API key successfully authenticates."""
    creds = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="super-secret-token-12345",
    )
    result = await verify_api_key(credentials=creds)
    assert result == "super-secret-token-12345"


@pytest.mark.asyncio
async def test_verify_api_key_invalid(mock_settings):
    """Incorrect API key raises 403 Forbidden."""
    creds = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="wrong-token-abcde",
    )
    with pytest.raises(HTTPException) as exc_info:
        await verify_api_key(credentials=creds)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Invalid API key"


@pytest.mark.asyncio
async def test_verify_api_key_empty(mock_settings):
    """Empty credentials raise 403 Forbidden."""
    creds = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="",
    )
    with pytest.raises(HTTPException) as exc_info:
        await verify_api_key(credentials=creds)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_verify_api_key_unicode(mock_settings):
    """Unicode / special characters in token are compared safely without crash."""
    creds = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="token-con-acentos-áéíóú-ñ",
    )
    with pytest.raises(HTTPException) as exc_info:
        await verify_api_key(credentials=creds)

    assert exc_info.value.status_code == 403
