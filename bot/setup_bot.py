from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from bot.common.logging import get_logger
from bot.handlers import setup_routers
from bot.services.chat import ChatService

logger = get_logger()


async def set_commands(bot: Bot) -> None:
    """
    ### Purpose
    Configure Telegram bot commands shown in the client UI.

    ### Parameters
    - **bot** (Bot): Active aiogram bot instance.

    ### Returns
    - **None**: The function updates bot commands remotely.
    """

    logger.info("Setting bot commands")
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Show bot instructions"),
        ]
    )


def setup_dispatcher(dispatcher: Dispatcher) -> None:
    """
    ### Purpose
    Configure dispatcher-level middleware and options.

    ### Parameters
    - **dispatcher** (Dispatcher): Dispatcher instance being prepared for polling.

    ### Returns
    - **None**: The dispatcher is configured in place.
    """

    logger.debug("Dispatcher uses default configuration")


async def setup_bot(bot: Bot, dispatcher: Dispatcher, chat_service: ChatService) -> None:
    """
    ### Purpose
    Prepare the bot and dispatcher before polling starts.

    ### Parameters
    - **bot** (Bot): Active aiogram bot instance.
    - **dispatcher** (Dispatcher): Active aiogram dispatcher.
    - **chat_service** (ChatService): Service used by message handlers.

    ### Returns
    - **None**: The bot and dispatcher are configured for runtime.
    """

    logger.info("Setup bot started")
    await set_commands(bot)
    setup_routers(dispatcher=dispatcher, chat_service=chat_service)
    setup_dispatcher(dispatcher)
    logger.info("Setup bot finished")
