import pytest
import asyncio
from backend.app.llm.client import BharatCodeClient

@pytest.mark.asyncio
async def test_bharatcode_hinglish_raw_materials_classification():
    client = BharatCodeClient()
    res = await client.classify_transaction(
        narration="Paid 15000 to Sharma ji for 50 bags cement and sariya",
        amount=15000.0,
        direction="DEBIT",
        counterparty_hint="Sharma Ji"
    )
    assert res["category"] == "Raw Materials"
    assert res["is_business_expense"] is True
    assert res["gst_rate"] == 18.0
    assert res["confidence_score"] >= 0.85
    assert "cement" in res["rationale"].lower() or "supplies" in res["rationale"].lower()

@pytest.mark.asyncio
async def test_bharatcode_rent_kiraya_classification():
    client = BharatCodeClient()
    res = await client.classify_transaction(
        narration="Dukaan ka kiraya diya landlord sharma",
        amount=25000.0,
        direction="DEBIT"
    )
    assert res["category"] == "Rent & Utilities"
    assert res["is_business_expense"] is True
    assert res["suggested_hsn_sac"] == "9972"
    assert res["confidence_score"] >= 0.85

@pytest.mark.asyncio
async def test_bharatcode_salary_classification():
    client = BharatCodeClient()
    res = await client.classify_transaction(
        narration="Helper Ramu staff monthly tankhwah salary",
        amount=12000.0,
        direction="DEBIT"
    )
    assert res["category"] == "Salaries & Wages"
    assert res["gst_rate"] == 0.0
    assert res["confidence_score"] >= 0.85

@pytest.mark.asyncio
async def test_bharatcode_ambiguous_low_confidence_classification():
    client = BharatCodeClient()
    res = await client.classify_transaction(
        narration="payment to anil",
        amount=3000.0,
        direction="DEBIT"
    )
    # Low confidence triggers human-in-the-loop approval
    assert res["confidence_score"] < 0.85
    assert res["category"] == "Uncategorized"

@pytest.mark.asyncio
async def test_bharatcode_gst_statutory_assistant():
    client = BharatCodeClient()
    messages = [
        {"role": "system", "content": "You are GST AI assistant"},
        {"role": "user", "content": "What are the essential conditions to claim input tax credit (ITC)?"}
    ]
    resp = await client.chat_completion(messages)
    text = resp["content"]
    assert "Section 16" in text
    assert "Section 17(5)" in text
    assert "GSTR-2B" in text or "invoice" in text

