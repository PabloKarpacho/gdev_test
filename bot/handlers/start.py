from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.common.logging import get_logger

WELCOME_TEXT = (
    "I am a Telegram bot connected to ChatGPT.\n\n"
    "Send me a text message, a voice note, or a photo, and I will reply."
)

logger = get_logger()


def get_start_logger(message: Message):
    """
    ### Purpose
    Attach command context to `/start` handler logs.

    ### Parameters
    - **message** (Message): Incoming Telegram message.

    ### Returns
    - **LoggerProtocol**: Logger bound with command context when available.
    """

    chat = getattr(message, "chat", None)
    from_user = getattr(message, "from_user", None)
    return logger.bind(
        chat_id=getattr(chat, "id", None),
        user_id=getattr(from_user, "id", None),
        message_id=getattr(message, "message_id", None),
        message_type="command_start",
    )


async def handle_start(message: Message) -> None:
    """
    ### Purpose
    Send the greeting message for the `/start` command.

    ### Parameters
    - **message** (Message): Incoming Telegram message.

    ### Returns
    - **None**: The function replies to the user in Telegram.
    """

    message_logger = get_start_logger(message)
    message_logger.info("Received /start command")
    await message.answer(WELCOME_TEXT)
    message_logger.info("Start command response sent")


def build_start_router() -> Router:
    """
    ### Purpose
    Build the router responsible for the `/start` command.

    ### Parameters
    - **None**: The function uses static handler wiring only.

    ### Returns
    - **Router**: Configured aiogram router instance.
    """

    router = Router()

    @router.message(CommandStart())
    async def start_handler(message: Message) -> None:
        await handle_start(message)

    return router
