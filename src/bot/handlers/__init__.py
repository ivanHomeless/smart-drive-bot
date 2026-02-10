from aiogram import Router

from src.bot.handlers.buy import buy_handler
from src.bot.handlers.check import check_handler
from src.bot.handlers.common import router as common_router
from src.bot.handlers.errors import router as errors_router
from src.bot.handlers.find import find_handler
from src.bot.handlers.legal import legal_handler
from src.bot.handlers.sell import sell_handler
from src.bot.handlers.start import router as start_router


def get_main_router() -> Router:
    main_router = Router()
    # Order matters:
    # 1. start (commands + reset confirmation)
    # 2. branch routers (each handles its own states)
    # 3. common nav (nav:home without state filter)
    # 4. errors (catch-all for stale callbacks) — always last
    main_router.include_router(start_router)
    main_router.include_router(sell_handler.router)
    main_router.include_router(buy_handler.router)
    main_router.include_router(find_handler.router)
    main_router.include_router(check_handler.router)
    main_router.include_router(legal_handler.router)
    main_router.include_router(common_router)
    main_router.include_router(errors_router)
    return main_router
