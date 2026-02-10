from aiogram import Router

from src.bot.handlers.common import router as common_router
from src.bot.handlers.errors import router as errors_router
from src.bot.handlers.start import router as start_router


def get_main_router() -> Router:
    main_router = Router()
    # Order matters: start first, then common nav, then errors (catch-all) last
    main_router.include_router(start_router)
    main_router.include_router(common_router)
    main_router.include_router(errors_router)
    return main_router
