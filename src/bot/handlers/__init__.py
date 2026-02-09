from aiogram import Router

from src.bot.handlers.start import router as start_router


def get_main_router() -> Router:
    main_router = Router()
    main_router.include_router(start_router)
    return main_router
