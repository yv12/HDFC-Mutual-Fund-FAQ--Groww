"""
Unit tests for the query classifier module.
"""

from app.pipeline.query_classifier import classify_query


def test_classify_factual_queries():
    """Verify that factual queries are correctly identified."""
    factual_queries = [
        "What is the NAV of HDFC Mid Cap Fund?",
        "what is the expense ratio of hdfc large cap?",
        "Who is the fund manager of HDFC Small Cap?",
        "Does HDFC Defence Fund have an exit load?",
        "what is the minimum SIP investment for HDFC Gold ETF?",
        "what is the benchmark index for HDFC Large Cap Fund?",
        "What is the AUM of HDFC Defence?",
        "Is there a lock-in period for this mutual fund?",
    ]
    for q in factual_queries:
        assert classify_query(q) == "factual", f"Query failed to classify as factual: {q}"


def test_classify_advisory_queries():
    """Verify that advisory or recommendation queries are correctly routed to advisory."""
    advisory_queries = [
        "Should I invest in HDFC Mid Cap Fund?",
        "Which is the best fund to buy right now?",
        "Can you recommend a mutual fund for me?",
        "Is HDFC Large Cap better than HDFC Small Cap?",
        "suggest a good mutual fund to invest in.",
        "Compare HDFC Defence Fund with Mid Cap.",
        "would you recommend HDFC Gold ETF?",
        "Calculate my returns for HDFC Small Cap",
        "What are the projected returns for HDFC Defence Fund?",
        "Is there a returns calculator for this scheme?",
        "If I invest 1000, how much will my money grow to in 5 years?",
        "SIP calculator for HDFC Mid Cap",
        "calculate future returns for 10 years",
    ]
    for q in advisory_queries:
        assert classify_query(q) == "advisory", f"Query failed to classify as advisory: {q}"


def test_classify_out_of_scope_queries():
    """Verify that unrelated or generic queries are routed to out_of_scope."""
    out_of_scope_queries = [
        "What is the weather today in Mumbai?",
        "Who won the cricket match yesterday?",
        "hello",
        "tell me a joke",
        "how does a car work?",
    ]
    for q in out_of_scope_queries:
        assert classify_query(q) == "out_of_scope", f"Query failed to classify as out_of_scope: {q}"


def test_classify_empty_query():
    """Verify that empty queries fallback to out_of_scope."""
    assert classify_query("") == "out_of_scope"
    assert classify_query("   ") == "out_of_scope"
