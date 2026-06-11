"""
Unit tests for the PII scanner module.
"""

from app.security.pii_scanner import scan_pii


def test_pii_pan_card():
    """Verify that PAN card numbers are detected (case-insensitive)."""
    assert scan_pii("My PAN is ABCDE1234F") is True
    assert scan_pii("pan abcde1234f") is True
    assert scan_pii("Here is a number: XYZWP1234Z") is True


def test_pii_aadhaar_card():
    """Verify that Aadhaar numbers with or without spaces are detected."""
    assert scan_pii("Aadhaar 1234 5678 9012") is True
    assert scan_pii("number 123456789012") is True


def test_pii_email():
    """Verify that email addresses are detected."""
    assert scan_pii("Contact me at test@example.com") is True
    assert scan_pii("my email is dummy.user+info@groww.co.in") is True


def test_pii_phone():
    """Verify that phone numbers are detected."""
    assert scan_pii("Call me at 9876543210") is True
    assert scan_pii("My phone number is +91-98765-43210") is True
    assert scan_pii("+91 8888888888") is True


def test_pii_otp():
    """Verify that OTP codes are detected when 'otp' is in the context."""
    # Matches when 'otp' keyword is present
    assert scan_pii("My OTP is 123456") is True
    assert scan_pii("Use otp 9876") is True
    # Should NOT trigger if no 'otp' keyword is present (to avoid false positives on standard numbers)
    assert scan_pii("The scheme launch year is 2023") is False
    assert scan_pii("NAV is 12.3456") is False


def test_pii_bank_account():
    """Verify that bank account numbers are detected when bank keywords are present."""
    # Matches when bank keyword is present
    assert scan_pii("My account number is 12345678901") is True
    assert scan_pii("My bank acc is 9876543212345") is True
    # Should NOT trigger if no bank keyword is present
    assert scan_pii("We have 12345678901 chunks") is False


def test_non_pii_queries():
    """Verify that clean factual queries are not flagged as PII."""
    assert scan_pii("What is the expense ratio of HDFC Mid Cap Fund?") is False
    assert scan_pii("Who is the fund manager?") is False
    assert scan_pii("What is the exit load?") is False
