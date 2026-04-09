from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.common.logging import get_logger

logger = get_logger()


def get_bot(token: str) -> Bot:
    """
    ### Purpose
    Create the Telegram bot client.

    ### Parameters
    - **token** (str): Telegram bot token.

    ### Returns
    - **Bot**: Configured aiogram bot instance.
    """

    logger.debug("Initializing Telegram Bot instance")
    return Bot(token=token)


def get_dispatcher() -> Dispatcher:
    """
    ### Purpose
    Create the dispatcher with in-memory FSM storage.

    ### Parameters
    - **None**: The dispatcher does not require external services.

    ### Returns
    - **Dispatcher**: Configured aiogram dispatcher.
    """

    logger.debug("Initializing Dispatcher with memory storage")
    return Dispatcher(storage=MemoryStorage())
