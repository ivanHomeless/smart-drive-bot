from unittest.mock import AsyncMock, MagicMock

from aiogram.types import TelegramObject, User

from src.bot.middlewares.throttling import ThrottlingMiddleware


async def test_throttle_allows_normal_traffic():
    mw = ThrottlingMiddleware(rate_limit=3, period=1.0)
    handler = AsyncMock(return_value="ok")
    event = MagicMock(spec=TelegramObject)
    user = MagicMock(spec=User)
    user.id = 1

    for _ in range(3):
        result = await mw(handler, event, {"event_from_user": user})
        assert result == "ok"

    assert handler.call_count == 3


async def test_throttle_drops_excess_traffic():
    mw = ThrottlingMiddleware(rate_limit=2, period=60.0)
    handler = AsyncMock(return_value="ok")
    event = MagicMock(spec=TelegramObject)
    user = MagicMock(spec=User)
    user.id = 1

    results = []
    for _ in range(5):
        r = await mw(handler, event, {"event_from_user": user})
        results.append(r)

    assert results.count("ok") == 2
    assert results.count(None) == 3


async def test_throttle_allows_without_user():
    mw = ThrottlingMiddleware(rate_limit=1, period=1.0)
    handler = AsyncMock(return_value="ok")
    event = MagicMock(spec=TelegramObject)

    for _ in range(5):
        result = await mw(handler, event, {})
        assert result == "ok"
