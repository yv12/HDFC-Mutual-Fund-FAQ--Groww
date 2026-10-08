from app.pipeline.query_rewriter import (
    detect_ambiguous_scheme_query,
    extract_fund_from_text,
    _extract_last_fund_from_history,
)

def test_cold_ambiguous_query():
    ambig, attr, options = detect_ambiguous_scheme_query("What's the exit load of this scheme?", [])
    assert ambig is True
    assert attr == "Exit load"
    assert len(options) == 5
    assert "Exit load of HDFC Mid Cap Fund" in options

def test_cold_attribute_only():
    ambig, attr, options = detect_ambiguous_scheme_query("What is the expense ratio?", [])
    assert ambig is True
    assert attr == "Expense ratio"
    assert len(options) == 5
    assert "Expense ratio of HDFC Small Cap Fund" in options

def test_explicit_fund():
    ambig, attr, options = detect_ambiguous_scheme_query("What is the exit load of HDFC Mid Cap Fund?", [])
    assert ambig is False
    assert options == []

def test_alias_fund():
    ambig, attr, options = detect_ambiguous_scheme_query("What is the exit load of top 100?", [])
    assert ambig is False
    assert options == []

def test_history_resolution():
    history = [
        {"role": "user", "content": "Tell me about top 100"},
        {"role": "assistant", "content": "HDFC Top 100 is a large cap fund with NAV 120."}
    ]
    ambig, attr, options = detect_ambiguous_scheme_query("What's the exit load of this scheme?", history)
    assert ambig is False
    fund = _extract_last_fund_from_history(history)
    assert fund == "HDFC Large Cap Fund Direct Growth"

def test_endpoint_disambiguation():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)

    r = client.post("/api/chat", json={"query": "What's the exit load of this scheme?"})
    assert r.status_code == 200
    data = r.json()
    assert data["query_type"] == "clarification"
    assert "Which HDFC scheme are you asking about?" in data["answer"]
    assert len(data["options"]) == 5
    assert any("Exit load of HDFC Mid Cap" in opt for opt in data["options"])

if __name__ == "__main__":
    test_cold_ambiguous_query()
    test_cold_attribute_only()
    test_explicit_fund()
    test_alias_fund()
    test_history_resolution()
    test_endpoint_disambiguation()
    print("ALL TESTS PASSED SUCCESSFULLY!")
