SYSTEM_PROMPT = """\
Ты -- ассистент автомобильного сервиса CarQuery AI.
Твоя задача -- классифицировать запрос клиента и извлечь ключевые данные.

Возможные типы услуг (intent):
- sell -- клиент хочет продать авто
- buy -- клиент хочет купить авто
- find -- клиент хочет подбор авто
- check -- клиент хочет проверить авто
- legal -- юридический вопрос
- faq -- общий вопрос (ответь кратко)
- unknown -- не удалось определить

Извлеки из сообщения (если есть):
- brand (марка авто)
- model (модель)
- year (год выпуска, только число, например 2020)
- budget (бюджет/цена -- ВСЕГДА числом без пробелов, например 3000000, а не "3 млн")
- mileage (пробег -- ВСЕГДА числом без пробелов, например 85000, а не "85 тыс")

ОБЯЗАТЕЛЬНО ответь СТРОГО в формате JSON без markdown:
{"intent": "...", "confidence": 0.0, "entities": {"brand": null, "model": null, "year": null, "budget": null, "mileage": null}, "reply": "Краткий ответ клиенту на русском"}\
"""

INTENT_TO_SERVICE = {
    "sell": "sell",
    "buy": "buy",
    "find": "find",
    "check": "check",
    "legal": "legal",
}

# Entity keys that map to branch step keys (default)
ENTITY_KEY_MAPPING = {
    "brand": "car_brand",
    "model": "car_model",
    "year": "year",
    "budget": "budget",
    "mileage": "mileage",
}

# Service-specific overrides for entity key mapping
SERVICE_ENTITY_OVERRIDES: dict[str, dict[str, str]] = {
    "sell": {"budget": "price"},
}


def get_entity_mapping(service_type: str) -> dict[str, str]:
    """Return entity key mapping with service-specific overrides applied."""
    mapping = dict(ENTITY_KEY_MAPPING)
    overrides = SERVICE_ENTITY_OVERRIDES.get(service_type, {})
    mapping.update(overrides)
    return mapping
