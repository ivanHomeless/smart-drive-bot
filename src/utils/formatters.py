SERVICE_TYPE_LABELS = {
    "sell": "Продажа авто",
    "buy": "Покупка авто",
    "find": "Подбор авто",
    "check": "Проверка авто",
    "legal": "Юридическая помощь",
    "freetext": "Свободный вопрос",
}

FIELD_LABELS = {
    "car_brand": "Марка/Модель",
    "year": "Год",
    "mileage": "Пробег",
    "price": "Цена",
    "photos": "Фото",
    "name": "Имя",
    "phone": "Телефон",
    "comment": "Комментарий",
    "budget": "Бюджет",
    "year_from": "Год от",
    "transmission": "Коробка передач",
    "drive": "Привод",
    "purpose": "Цель",
    "brand_preference": "Предпочтения по марке",
    "body_type": "Тип кузова",
    "check_type": "Тип проверки",
    "vin": "VIN / Госномер",
    "question_type": "Тип вопроса",
    "description": "Описание",
}


def format_confirmation(service_type: str, data: dict) -> str:
    """Format collected data for the confirmation screen."""
    lines = ["Ваша заявка:\n"]
    service_label = SERVICE_TYPE_LABELS.get(service_type, service_type)
    lines.append(f"Услуга: {service_label}")

    for key, value in data.items():
        if key.startswith("__") or value is None:
            continue
        label = FIELD_LABELS.get(key, key)
        if key == "photos" and isinstance(value, list):
            lines.append(f"{label}: {len(value)} шт.")
        else:
            lines.append(f"{label}: {value}")

    lines.append("\nВсё верно?")
    return "\n".join(lines)


def format_lead_title(service_type: str, data: dict) -> str:
    """Format lead title for AmoCRM: '{service} - {brand} - {name}'."""
    service_label = SERVICE_TYPE_LABELS.get(service_type, service_type)
    brand = data.get("car_brand", "")
    name = data.get("name", "")
    parts = [service_label]
    if brand:
        parts.append(brand)
    if name:
        parts.append(name)
    return " - ".join(parts)


def format_lead_note(service_type: str, data: dict, telegram_user: dict | None = None) -> str:
    """Format lead note with all collected data for AmoCRM."""
    lines = []
    service_label = SERVICE_TYPE_LABELS.get(service_type, service_type)
    lines.append(f"Услуга: {service_label}")
    lines.append("")

    for key, value in data.items():
        if key.startswith("__") or value is None:
            continue
        label = FIELD_LABELS.get(key, key)
        if key == "photos" and isinstance(value, list):
            lines.append(f"{label}: {len(value)} шт.")
            for i, file_id in enumerate(value, 1):
                lines.append(f"  Фото {i}: {file_id}")
        else:
            lines.append(f"{label}: {value}")

    if telegram_user:
        lines.append("")
        lines.append("--- Метаданные ---")
        if "id" in telegram_user:
            lines.append(f"Telegram ID: {telegram_user['id']}")
        if "username" in telegram_user:
            lines.append(f"Username: @{telegram_user['username']}")

    return "\n".join(lines)
