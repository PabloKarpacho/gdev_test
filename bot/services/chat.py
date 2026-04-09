from dataclasses import dataclass

from bot.ai.client import AIClient


EMPTY_TEXT_REPLY = "Send me a non-empty text message."
EMPTY_VOICE_REPLY = "I could not recognize the voice message."
DEFAULT_PHOTO_PROMPT = "Describe the image and help the user."


@dataclass(frozen=True)
class BinaryAttachment:
    """
    ### Purpose
    Represent a downloaded Telegram file in a transport-agnostic format.

    ### Parameters
    - **content** (bytes): Raw file bytes.
    - **filename** (str): Original or generated filename.
    - **mime_type** (str): MIME type associated with the file.

    ### Returns
    - **BinaryAttachment**: Immutable attachment value object.
    """

    content: bytes
    filename: str
    mime_type: str


class ChatService:
    """
    ### Purpose
    Coordinate AI requests for text, photo, and voice Telegram messages.

    ### Parameters
    - **ai_client** (AIClient): AI client implementation used for generation and transcription.

    ### Returns
    - **ChatService**: Application service for Telegram handlers.
    """

    def __init__(self, ai_client: AIClient) -> None:
        self._ai_client = ai_client

    async def reply_to_text(self, text: str | None) -> str:
        """
        ### Purpose
        Generate a reply for a text message.

        ### Parameters
        - **text** (str | None): User text message.

        ### Returns
        - **str**: Assistant reply or validation feedback.
        """

        normalized_text = (text or "").strip()
        if not normalized_text:
            return EMPTY_TEXT_REPLY
        return await self._ai_client.respond_to_text(normalized_text)

    async def reply_to_photo(
        self,
        attachment: BinaryAttachment,
        caption: str | None,
    ) -> str:
        """
        ### Purpose
        Generate a reply for a photo message.

        ### Parameters
        - **attachment** (BinaryAttachment): Downloaded photo attachment.
        - **caption** (str | None): Optional user caption for the image.

        ### Returns
        - **str**: Assistant reply describing or analyzing the image.
        """

        prompt = (caption or "").strip() or DEFAULT_PHOTO_PROMPT
        return await self._ai_client.respond_to_photo(
            prompt=prompt,
            photo_bytes=attachment.content,
            mime_type=attachment.mime_type,
        )

    async def reply_to_voice(self, attachment: BinaryAttachment) -> str:
        """
        ### Purpose
        Generate a reply for a voice message.

        ### Parameters
        - **attachment** (BinaryAttachment): Downloaded voice attachment.

        ### Returns
        - **str**: Assistant reply or a transcription failure message.
        """

        transcript = await self._ai_client.transcribe_voice(
            audio_bytes=attachment.content,
            filename=attachment.filename,
        )
        if not transcript:
            return EMPTY_VOICE_REPLY
        return await self._ai_client.respond_to_voice(transcript)
