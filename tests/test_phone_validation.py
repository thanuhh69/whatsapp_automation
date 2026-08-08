import pytest
from backend.services.recipient import normalize_phone

def test_indian_phone_normalization_valid():
    # Plain 10 digit
    phone, valid = normalize_phone("9876543210", country_code="91")
    assert valid is True
    assert phone == "919876543210"

    # With +91
    phone, valid = normalize_phone("+91 98765 43210", country_code="91")
    assert valid is True
    assert phone == "919876543210"

    # With 91 prefix
    phone, valid = normalize_phone("91-9876543210", country_code="91")
    assert valid is True
    assert phone == "919876543210"

    # With 0 prefix
    phone, valid = normalize_phone("09876543210", country_code="91")
    assert valid is True
    assert phone == "919876543210"

def test_indian_phone_normalization_invalid():
    # Starts with 5 (invalid for Indian mobile 6-9)
    phone, valid = normalize_phone("5876543210", country_code="91")
    assert valid is False
    assert phone is None

    # Too short
    phone, valid = normalize_phone("98765432", country_code="91")
    assert valid is False

    # Too long
    phone, valid = normalize_phone("9198765432100", country_code="91")
    assert valid is False

    # Non-digits only
    phone, valid = normalize_phone("abcdef", country_code="91")
    assert valid is False
