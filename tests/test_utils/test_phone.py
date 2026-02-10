from src.utils.phone import validate_phone


def test_valid_ru_phone_with_country_code():
    assert validate_phone("+79991234567") == "+79991234567"


def test_valid_ru_phone_without_plus():
    assert validate_phone("89991234567") == "+79991234567"


def test_valid_ru_phone_with_spaces():
    assert validate_phone("+7 999 123 45 67") == "+79991234567"


def test_valid_international_phone():
    result = validate_phone("+14155552671", default_region="US")
    assert result == "+14155552671"


def test_invalid_phone_too_short():
    assert validate_phone("123") is None


def test_invalid_phone_letters():
    assert validate_phone("abc") is None


def test_invalid_phone_empty():
    assert validate_phone("") is None


def test_valid_ru_phone_formatted():
    assert validate_phone("+7 (999) 123-45-67") == "+79991234567"


def test_invalid_phone_partial():
    assert validate_phone("+7999") is None
