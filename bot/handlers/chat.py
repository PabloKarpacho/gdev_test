from aiogram import Bot, F, Router
from aiogram.types import Message

from bot.common.logging import get_logger
from bot.services.chat import ChatService
from bot.telegram.files import (
    AttachmentValidationError,
    download_photo_attachment,
    download_voice_attachment,
)

ATTACHMENT_ERROR_REPLY = (
    "The attachment is too large or unsupported. "
    "Send a smaller photo or a supported voice message."
)
PROCESSING_ERROR_REPLY = (
    "Something went wrong while processing your message. Please try again."
)

logger = get_logger()


def get_message_logger(message: Message):
    """
    ### Purpose
    Attach chat and message identifiers to handler logs.

    ### Parameters
    - **message** (Message): Incoming Telegram message.

    ### Returns
    - **LoggerProtocol**: Logger bound with message context when available.
    """

    chat = getattr(message, "chat", None)
    from_user = getattr(message, "from_user", None)
    message_type = "text"
    if getattr(message, "photo", None):
        message_type = "photo"
    elif getattr(message, "voice", None):
        message_type = "voice"

    return logger.bind(
        chat_id=getattr(chat, "id", None),
        user_id=getattr(from_user, "id", None),
        message_id=getattr(message, "message_id", None),
        message_type=message_type,
    )


async def handle_text_message(message: Message, chat_service: ChatService) -> None:
    """
    ### Purpose
    Handle plain text messages by forwarding them to the AI service.

    ### Parameters
    - **message** (Message): Incoming Telegram message.
    - **chat_service** (ChatService): Application service that talks to the AI layer.

    ### Returns
    - **None**: The function sends a text reply back to Telegram.
    """

    message_logger = get_message_logger(message)
    normalized_text = (message.text or "").strip()

    message_logger.info(
        "Received text message for processing, text_length={}",
        len(normalized_text),
    )

    try:
        message_logger.info("Calling chat service for text message")
        answer = await chat_service.reply_to_text(message.text)
        message_logger.info("Chat service returned text response, reply_length={}", len(answer))
    except Exception:
        message_logger.exception("Text message processing failed")
        await message.answer(PROCESSING_ERROR_REPLY)
        return

    message_logger.info("Sending text reply to Telegram")
    await message.answer(answer)
    message_logger.info("Text reply sent successfully")


async def handle_photo_message(
    message: Message,
    bot: Bot,
    chat_service: ChatService,
) -> None:
    """
    ### Purpose
    Handle photo messages by downloading the image and sending it to the AI service.

    ### Parameters
    - **message** (Message): Incoming Telegram photo message.
    - **bot** (Bot): Active aiogram bot instance used for file downloads.
    - **chat_service** (ChatService): Application service that talks to the AI layer.

    ### Returns
    - **None**: The function sends a text reply back to Telegram.
    """

    message_logger = get_message_logger(message)
    photo_count = len(message.photo or [])
    caption_length = len((message.caption or "").strip())

    message_logger.info(
        "Received photo message for processing, photo_count={}, caption_length={}",
        photo_count,
        caption_length,
    )

    try:
        message_logger.info("Downloading photo attachment from Telegram")
        attachment = await download_photo_attachment(bot=bot, photo_sizes=message.photo)
        message_logger.info(
            "Photo attachment downloaded, filename={}, mime_type={}, size_bytes={}",
            attachment.filename,
            attachment.mime_type,
            len(attachment.content),
        )
        message_logger.info("Calling chat service for photo message")
        answer = await chat_service.reply_to_photo(
            attachment=attachment,
            caption=message.caption,
        )
        message_logger.info("Chat service returned photo response, reply_length={}", len(answer))
    except AttachmentValidationError as error:
        message_logger.warning("Photo attachment validation failed: {}", error)
        await message.answer(ATTACHMENT_ERROR_REPLY)
        return
    except Exception:
        message_logger.exception("Photo message processing failed")
        await message.answer(PROCESSING_ERROR_REPLY)
        return

    message_logger.info("Sending photo reply to Telegram")
    await message.answer(answer)
    message_logger.info("Photo reply sent successfully")


async def handle_voice_message(
    message: Message,
    bot: Bot,
    chat_service: ChatService,
) -> None:
    """
    ### Purpose
    Handle voice messages by downloading audio, transcribing it, and generating a reply.

    ### Parameters
    - **message** (Message): Incoming Telegram voice message.
    - **bot** (Bot): Active aiogram bot instance used for file downloads.
    - **chat_service** (ChatService): Application service that talks to the AI layer.

    ### Returns
    - **None**: The function sends a text reply back to Telegram.
    """

    message_logger = get_message_logger(message)
    voice = getattr(message, "voice", None)

    message_logger.info(
        "Received voice message for processing, duration_seconds={}, mime_type={}",
        getattr(voice, "duration", None),
        getattr(voice, "mime_type", None),
    )

    try:
        message_logger.info("Downloading voice attachment from Telegram")
        attachment = await download_voice_attachment(bot=bot, voice=message.voice)
        message_logger.info(
            "Voice attachment downloaded, filename={}, mime_type={}, size_bytes={}",
            attachment.filename,
            attachment.mime_type,
            len(attachment.content),
        )
        message_logger.info("Calling chat service for voice message")
        answer = await chat_service.reply_to_voice(attachment)
        message_logger.info("Chat service returned voice response, reply_length={}", len(answer))
    except AttachmentValidationError as error:
        message_logger.warning("Voice attachment validation failed: {}", error)
        await message.answer(ATTACHMENT_ERROR_REPLY)
        return
    except Exception:
        message_logger.exception("Voice message processing failed")
        await message.answer(PROCESSING_ERROR_REPLY)
        return

    message_logger.info("Sending voice reply to Telegram")
    await message.answer(answer)
    message_logger.info("Voice reply sent successfully")


def build_chat_router(chat_service: ChatService) -> Router:
    """
    ### Purpose
    Build the router responsible for text, photo, and voice AI interactions.

    ### Parameters
    - **chat_service** (ChatService): Application service used by message handlers.

    ### Returns
    - **Router**: Configured aiogram router instance.
    """

    router = Router()

    @router.message(F.photo)
    async def photo_handler(message: Message, bot: Bot) -> None:
        await handle_photo_message(message=message, bot=bot, chat_service=chat_service)

    @router.message(F.voice)
    async def voice_handler(message: Message, bot: Bot) -> None:
        await handle_voice_message(message=message, bot=bot, chat_service=chat_service)

    @router.message(F.text & ~F.text.startswith("/"))
    async def text_handler(message: Message) -> None:
        await handle_text_message(message=message, chat_service=chat_service)

    return router
