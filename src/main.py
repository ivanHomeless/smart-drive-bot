import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from src.bot.handlers import get_main_router
from src.bot.middlewares.db import DbSessionMiddleware
from src.bot.middlewares.logging_mw import LoggingMiddleware
from src.bot.middlewares.throttling import ThrottlingMiddleware
from src.config import settings
from src.db.engine import async_session
from src.services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


async def health_check(_request: web.Request) -> web.Response:
    return web.Response(text="ok")


async def run_health_server() -> None:
    app = web.Application()
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", settings.HEALTH_CHECK_PORT)
    await site.start()
    logger.info("Health check server started on port %d", settings.HEALTH_CHECK_PORT)


async def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    redis = Redis.from_url(settings.REDIS_URL)
    storage = RedisStorage(redis=redis, state_ttl=1800)

    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # OpenAI client (injected into handlers as "openai_client" kwarg)
    openai_client = None
    if settings.OPENAI_API_KEY:
        openai_client = OpenAIClient()
        logger.info("OpenAI client initialized (model=%s)", settings.OPENAI_MODEL)
    else:
        logger.warning("OPENAI_API_KEY not set, freetext AI will be unavailable")

    dp = Dispatcher(storage=storage, openai_client=openai_client)

    dp.update.middleware(LoggingMiddleware())
    dp.update.middleware(ThrottlingMiddleware())
    dp.update.middleware(DbSessionMiddleware(session_pool=async_session))

    main_router = get_main_router()
    dp.include_router(main_router)

    await run_health_server()

    logger.info("Bot starting in long polling mode")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
