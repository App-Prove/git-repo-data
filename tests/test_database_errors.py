import pytest
from fastapi import HTTPException
from prisma import Prisma
from app.utils.databases import parse_json_field


@pytest.mark.asyncio
async def test_parse_json_field_none():
    """Test parsing None JSON field"""
    with pytest.raises(HTTPException) as exc_info:
        parse_json_field(None, "test_field")
    assert exc_info.value.status_code == 500
    assert "test_field field is None" in exc_info.value.detail


@pytest.mark.asyncio
async def test_parse_json_field_invalid():
    """Test parsing invalid JSON field"""
    with pytest.raises(HTTPException) as exc_info:
        parse_json_field("{invalid_json", "test_field")
    assert exc_info.value.status_code == 500
    assert "Invalid JSON in test_field" in exc_info.value.detail 