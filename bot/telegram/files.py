from collections.abc import Sequence

from aiogram import Bot

from bot.services.chat import BinaryAttachment

MAX_PHOTO_BYTES = 10 * 1024 * 1024
MAX_VOICE_BYTES = 20 * 1024 * 1024
DEFAULT_VOICE_MIME_TYPE = "audio/ogg"
ALLOWED_VOICE_MIME_TYPES = frozenset(
    {
        "audio/ogg",
        "audio/mpeg",
        "audio/mp3",
        "audio/wav",
        "audio/x-wav",
        "audio/mp4",
    }
)


class AttachmentValidationError(ValueError):
    """
    ### Purpose
    Represent a user-facing validation failure for Telegram attachments.

    ### Parameters
    - **ValueError**: Parent exception used for invalid attachment input.

    ### Returns
    - **AttachmentValidationError**: Specialized validation error.
    """


def validate_attachment_size(
    *,
    file_size: int | None,
    max_bytes: int,
    attachment_label: str,
) -> None:
    """
    ### Purpose
    Reject oversized attachments before or after downloading them.

    ### Parameters
    - **file_size** (int | None): Attachment size in bytes when available.
    - **max_bytes** (int): Maximum allowed size in bytes.
    - **attachment_label** (str): Human-readable attachment label for error messages.

    ### Returns
    - **None**: The function raises when validation fails.
    """

    if file_size is not None and file_size > max_bytes:
        raise AttachmentValidationError(
            f"{attachment_label} is too large. Maximum supported size is {max_bytes} bytes."
        )


def normalize_voice_mime_type(mime_type: str | None) -> str:
    """
    ### Purpose
    Normalize Telegram voice MIME type values to a supported default.

    ### Parameters
    - **mime_type** (str | None): MIME type reported by Telegram.

    ### Returns
    - **str**: Normalized MIME type suitable for transcription.
    """

    return mime_type or DEFAULT_VOICE_MIME_TYPE


def validate_voice_mime_type(mime_type: str) -> None:
    """
    ### Purpose
    Ensure the voice attachment MIME type is supported by the bot.

    ### Parameters
    - **mime_type** (str): Normalized voice MIME type.

    ### Returns
    - **None**: The function raises when validation fails.
    """

    if mime_type not in ALLOWED_VOICE_MIME_TYPES:
        raise AttachmentValidationError(
            "Voice message format is unsupported. Send OGG, MP3, WAV, or M4A audio."
        )


async def download_telegram_file(bot: Bot, file_id: str) -> bytes:
    """
    ### Purpose
    Download a Telegram file into memory as raw bytes.

    ### Parameters
    - **bot** (Bot): Active aiogram bot instance.
    - **file_id** (str): Telegram file identifier.

    ### Returns
    - **bytes**: Downloaded file content.
    """

    file = await bot.get_file(file_id)
    if not getattr(file, "file_path", None):
        raise AttachmentValidationError("Telegram file path is missing.")

    content = await bot.download_file(file.file_path)
    if hasattr(content, "read"):
        return content.read()
    return bytes(content)


def resolve_voice_filename(file_id: str, mime_type: str | None) -> str:
    """
    ### Purpose
    Build a deterministic voice filename that matches the Telegram MIME type.

    ### Parameters
    - **file_id** (str): Telegram file identifier.
    - **mime_type** (str | None): MIME type reported by Telegram.

    ### Returns
    - **str**: Generated filename with an extension suitable for transcription.
    """

    extension_map = {
        "audio/ogg": ".ogg",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/mp4": ".mp4",
    }
    extension = extension_map.get(mime_type or "", ".ogg")
    return f"{file_id}{extension}"


async def download_photo_attachment(bot: Bot, photo_sizes) -> BinaryAttachment:
    """
    ### Purpose
    Download the largest available Telegram photo variant.

    ### Parameters
    - **bot** (Bot): Active aiogram bot instance.
    - **photo_sizes** (Sequence): Collection of Telegram photo sizes.

    ### Returns
    - **BinaryAttachment**: Downloaded photo attachment.
    """

    if not isinstance(photo_sizes, Sequence) or not photo_sizes:
        raise AttachmentValidationError("Photo attachment is missing.")

    largest_photo = max(photo_sizes, key=lambda item: getattr(item, "file_size", 0))
    validate_attachment_size(
        file_size=getattr(largest_photo, "file_size", None),
        max_bytes=MAX_PHOTO_BYTES,
        attachment_label="Photo",
    )
    photo_bytes = await download_telegram_file(bot=bot, file_id=largest_photo.file_id)
    validate_attachment_size(
        file_size=len(photo_bytes),
        max_bytes=MAX_PHOTO_BYTES,
        attachment_label="Photo",
    )
    return BinaryAttachment(
        content=photo_bytes,
        filename="photo.jpg",
        mime_type="image/jpeg",
    )


async def download_voice_attachment(bot: Bot, voice) -> BinaryAttachment:
    """
    ### Purpose
    Download a Telegram voice note into memory.

    ### Parameters
    - **bot** (Bot): Active aiogram bot instance.
    - **voice** (object): Telegram voice object.

    ### Returns
    - **BinaryAttachment**: Downloaded voice attachment.
    """

    validate_attachment_size(
        file_size=getattr(voice, "file_size", None),
        max_bytes=MAX_VOICE_BYTES,
        attachment_label="Voice message",
    )
    mime_type = normalize_voice_mime_type(getattr(voice, "mime_type", None))
    validate_voice_mime_type(mime_type)
    voice_bytes = await download_telegram_file(bot=bot, file_id=voice.file_id)
    validate_attachment_size(
        file_size=len(voice_bytes),
        max_bytes=MAX_VOICE_BYTES,
        attachment_label="Voice message",
    )
    return BinaryAttachment(
        content=voice_bytes,
        filename=resolve_voice_filename(file_id=voice.file_id, mime_type=mime_type),
        mime_type=mime_type,
    )
