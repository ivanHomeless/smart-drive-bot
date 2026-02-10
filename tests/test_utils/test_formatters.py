from src.utils.formatters import format_confirmation, format_lead_note, format_lead_title


def test_format_confirmation_sell():
    data = {
        "car_brand": "Toyota Camry",
        "year": "2019",
        "mileage": "85 000 km",
        "name": "Alexey",
        "phone": "+79991234567",
    }
    result = format_confirmation("sell", data)
    assert "Продажа авто" in result
    assert "Toyota Camry" in result
    assert "2019" in result
    assert "Alexey" in result
    assert "+79991234567" in result


def test_format_confirmation_skips_internal_keys():
    data = {
        "__editing_field__": "name",
        "name": "Test",
    }
    result = format_confirmation("buy", data)
    assert "__editing_field__" not in result
    assert "Test" in result


def test_format_confirmation_photos_count():
    data = {"photos": ["id1", "id2", "id3"], "name": "Test"}
    result = format_confirmation("sell", data)
    assert "3 шт." in result


def test_format_lead_title():
    data = {"car_brand": "BMW X5", "name": "Ivan"}
    title = format_lead_title("sell", data)
    assert title == "Продажа авто - BMW X5 - Ivan"


def test_format_lead_title_no_brand():
    data = {"name": "Ivan"}
    title = format_lead_title("legal", data)
    assert title == "Юридическая помощь - Ivan"


def test_format_lead_note():
    data = {"car_brand": "Kia Rio", "name": "Test"}
    telegram_user = {"id": 123, "username": "testuser"}
    note = format_lead_note("buy", data, telegram_user)
    assert "Покупка авто" in note
    assert "Kia Rio" in note
    assert "Telegram ID: 123" in note
    assert "@testuser" in note
