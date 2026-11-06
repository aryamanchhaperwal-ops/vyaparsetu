import pytest
from backend.app.config import settings
from backend.app.llm.client import BharatCodeClient, BharatCodeAPIError

@pytest.mark.asyncio
async def test_bharatcode_official_configuration():
    """Validates that Lekha adheres to official BharatCode model identifiers and endpoints."""
    assert settings.BHARATCODE_BASE_URL == "https://bharatcode.ai/api/model/v1"
    assert settings.BHARATCODE_MODEL_NAME == "qwen-3.8-27b"
    assert settings.BHARATCODE_API_KEY is not None

@pytest.mark.asyncio
async def test_dev_simulation_mode_explicit_labeling():
    """Validates that DEV_SIMULATION mode never claims to be live BharatCode."""
    client = BharatCodeClient(ai_mode="DEV_SIMULATION")
    res = await client.classify_transaction(
        narration="Birla A1 Cement 50 bags cash payment",
        amount=18500.0,
        direction="DEBIT"
    )
    assert res["ai_mode"] == "DEV_SIMULATION"
    assert res["source"] == "DEV_SIMULATION"
    assert res["live_api"] is False
    assert "DEVELOPMENT SIMULATION" in res["notice"]
    assert res["category"] == "Raw Materials"

@pytest.mark.asyncio
async def test_production_bharatcode_mode_explicit_failure_when_unsubscribed():
    """
    Validates that PRODUCTION_BHARATCODE mode fails explicitly with BharatCodeAPIError
    when the API returns HTTP 402 (or unbilled/unsubscribed quota), and does NOT silently fake responses.
    """
    client = BharatCodeClient(ai_mode="PRODUCTION_BHARATCODE")
    
    # Must raise BharatCodeAPIError rather than silently returning mock data
    with pytest.raises(BharatCodeAPIError) as exc_info:
        await client.chat_completion([{"role": "user", "content": "Hello BharatCode"}])
    
    assert exc_info.value.status_code in (402, 401, 503)
    assert "BharatCode" in str(exc_info.value)

@pytest.mark.asyncio
async def test_zero_alternative_llm_providers():
    """Assures strict compliance: zero OpenAI, Anthropic, or Gemini calls in codebase."""
    import inspect
    from backend.app.llm import client
    source_code = inspect.getsource(client)
    for forbidden in ["openai", "anthropic", "google.generativeai", "gemini", "groq", "ollama"]:
        assert forbidden not in source_code.lower(), f"Forbidden provider {forbidden} found in client"

