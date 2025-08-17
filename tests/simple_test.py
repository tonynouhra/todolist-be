import pytest

def test_simple_addition():
    """Simple test to verify pytest is working"""
    assert 1 + 1 == 2

@pytest.mark.asyncio
async def test_simple_async():
    """Simple async test to verify async support"""
    result = await simple_async_function()
    assert result == "hello"

async def simple_async_function():
    return "hello"