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
from src.services.amocrm.contacts import ContactsService
from src.services.amocrm.leads import LeadsService
from src.services.amocrm.notes import NotesService
from src.services.lead_processor import LeadProcessor, retry_failed_leads
from src.services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

RETRY_INTERVAL_SECONDS = 300  # 5 minutes


def _create_crm_client():
    """Create AmoCRM client (real or mock based on settings)."""
    if settings.AMOCRM_MOCK_MODE:
        from src.services.amocrm.mock import MockAmoCRMClient
        logger.info("Using MockAmoCRMClient (AMOCRM_MOCK_MODE=true)")
        return MockAmoCRMClient()
    else:
        from src.services.amocrm.auth import AmoCRMAuth
        from src.services.amocrm.client import AmoCRMClient
        auth = AmoCRMAuth(session_factory=async_session)
        logger.info("Using real AmoCRM client (subdomain=%s)", settings.AMOCRM_SUBDOMAIN)
        return AmoCRMClient(auth)


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


async def retry_task(
    contacts: ContactsService,
    leads_service: LeadsService,
    notes: NotesService,
    bot: Bot,
) -> None:
    """Background task: retry failed leads every 5 minutes."""
    while True:
        await asyncio.sleep(RETRY_INTERVAL_SECONDS)
        try:
            count = await retry_failed_leads(
                async_session, contacts, leads_service, notes, bot,
            )
            if count:
                logger.info("Retried %d failed leads successfully", count)
        except Exception:
            logger.exception("Error in retry_failed_leads task")


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

    # AmoCRM services
    crm_client = _create_crm_client()
    contacts = ContactsService(crm_client)
    leads_service = LeadsService(crm_client)
    notes = NotesService(crm_client)
    lead_processor = LeadProcessor(contacts, leads_service, notes, bot)

    # OpenAI client (injected into handlers as "openai_client" kwarg)
    openai_client = None
    if settings.OPENAI_API_KEY:
        openai_client = OpenAIClient()
        logger.info("OpenAI client initialized (model=%s)", settings.OPENAI_MODEL)
    else:
        logger.warning("OPENAI_API_KEY not set, freetext AI will be unavailable")

    dp = Dispatcher(
        storage=storage,
        openai_client=openai_client,
        lead_processor=lead_processor,
    )

    dp.update.middleware(LoggingMiddleware())
    dp.update.middleware(ThrottlingMiddleware())
    dp.update.middleware(DbSessionMiddleware(session_pool=async_session))

    main_router = get_main_router()
    dp.include_router(main_router)

    await run_health_server()

    # Start background retry task
    asyncio.create_task(retry_task(contacts, leads_service, notes, bot))
    logger.info("Background retry task started (interval=%ds)", RETRY_INTERVAL_SECONDS)

    logger.info("Bot starting in long polling mode")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
