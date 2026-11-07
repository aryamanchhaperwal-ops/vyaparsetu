import pytest
from backend.app.services.voice_service import parse_vernacular_voice_narration

def test_parse_hindi_spoken_narration():
    text = "Sharma ji ko cement aur ret ke liye 25000 rupaye cash me diye"
    parsed = parse_vernacular_voice_narration(text)

    assert parsed["amount"] == 25000.0
    assert parsed["direction"] == "DEBIT"
    assert parsed["channel"] == "CASH"
    assert "Sharma ji" in parsed["counterparty_name"]
    assert parsed["category"] == "Raw Materials"
    assert parsed["confidence_score"] >= 0.85

def test_parse_customer_credit_narration():
    text = "Gupta Brothers se 85,000 ka payment RTGS se aaya mal ka"
    parsed = parse_vernacular_voice_narration(text)

    assert parsed["amount"] == 85000.0
    assert parsed["direction"] == "CREDIT"
    assert parsed["channel"] == "RTGS"
    assert "Gupta Brothers" in parsed["counterparty_name"]
    assert parsed["confidence_score"] >= 0.85

def test_parse_rent_narration():
    text = "Dukaan ka monthly kiraya 20 hazar transfer kiya"
    parsed = parse_vernacular_voice_narration(text)

    assert parsed["amount"] == 20000.0
    assert parsed["direction"] == "DEBIT"
    assert parsed["category"] == "Rent & Utilities"

