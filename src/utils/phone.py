import phonenumbers


def validate_phone(text: str, default_region: str = "RU") -> str | None:
    """Validate and normalize phone number to E.164 format.

    Returns E.164 string (e.g. '+79991234567') or None if invalid.
    """
    try:
        parsed = phonenumbers.parse(text, default_region)
    except phonenumbers.NumberParseException:
        return None

    if not phonenumbers.is_valid_number(parsed):
        return None

    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
