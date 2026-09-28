"""Pytest configuration and shared fixtures for Weather API tests."""

import pytest


@pytest.fixture
def anyio_backend():
    """Use asyncio as the async backend."""
    return "asyncio"
