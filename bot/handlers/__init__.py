"""Telegram bot handlers registration."""

from aiogram import Dispatcher

from bot.common.logging import get_logger
from bot.handlers.chat import build_chat_router
from bot.handlers.start import build_start_router
from bot.services.chat import ChatService

logger = get_logger()


def setup_routers(dispatcher: Dispatcher, chat_service: ChatService) -> None:
    """
    ### Purpose
    Register all runtime routers for the Telegram bot.

    ### Parameters
    - **dispatcher** (Dispatcher): Main aiogram dispatcher instance.
    - **chat_service** (ChatService): Service used by message handlers.

    ### Returns
    - **None**: This function mutates the dispatcher by attaching routers.
    """

    logger.info("Registering bot routers")
    dispatcher.include_router(build_start_router())
    dispatcher.include_router(build_chat_router(chat_service=chat_service))
    logger.info("All bot routers registered")
