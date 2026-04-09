import asyncio

from aiogram import Bot, Dispatcher

from bot.common.logging import get_logger
from bot.services.chat import ChatService
from bot.setup_bot import setup_bot

logger = get_logger()


async def close_bot_session(bot: Bot) -> None:
    """
    ### Purpose
    Close the Telegram bot HTTP session when polling stops or startup fails.

    ### Parameters
    - **bot** (Bot): Active aiogram bot instance.

    ### Returns
    - **None**: The function closes the underlying session when available.
    """

    session = getattr(bot, "session", None)
    close = getattr(session, "close", None)
    if close is not None:
        await close()


def run_in_pooling(bot: Bot, dp: Dispatcher, chat_service: ChatService) -> None:
    """
    ### Purpose
    Start the Telegram bot in polling mode.

    ### Parameters
    - **bot** (Bot): Active aiogram bot instance.
    - **dp** (Dispatcher): Dispatcher that routes incoming updates.
    - **chat_service** (ChatService): Service used by message handlers.

    ### Returns
    - **None**: The function owns the event loop until polling stops.
    """

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        logger.info("Deleting webhook before polling")
        loop.run_until_complete(bot.delete_webhook())

        logger.info("Setting up bot and dispatcher")
        loop.run_until_complete(
            setup_bot(
                bot=bot,
                dispatcher=dp,
                chat_service=chat_service,
            )
        )

        logger.info("Start polling")
        loop.run_until_complete(dp.start_polling(bot))
    except Exception:
        logger.exception("Unhandled exception in polling loop")
        raise
    finally:
        logger.info("Closing bot session")
        loop.run_until_complete(close_bot_session(bot))
        logger.info("Closing polling event loop")
        loop.close()
