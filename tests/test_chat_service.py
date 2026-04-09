import unittest

from bot.ai.client import AIClient
from bot.services.chat import BinaryAttachment, ChatService


class FakeAIClient(AIClient):
    def __init__(self) -> None:
        self.calls = []

    async def respond_to_text(self, prompt: str) -> str:
        self.calls.append(("text", prompt))
        return "text reply"

    async def respond_to_photo(
        self,
        prompt: str,
        photo_bytes: bytes,
        mime_type: str,
    ) -> str:
        self.calls.append(("photo", prompt, photo_bytes, mime_type))
        return "photo reply"

    async def transcribe_voice(self, audio_bytes: bytes, filename: str) -> str:
        self.calls.append(("transcribe", audio_bytes, filename))
        return "voice transcript"

    async def respond_to_voice(self, transcript: str) -> str:
        self.calls.append(("voice", transcript))
        return "voice reply"


class EmptyTranscriptAIClient(FakeAIClient):
    async def transcribe_voice(self, audio_bytes: bytes, filename: str) -> str:
        self.calls.append(("transcribe", audio_bytes, filename))
        return ""


class ChatServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_reply_to_text_rejects_empty_messages(self):
        service = ChatService(ai_client=FakeAIClient())

        result = await service.reply_to_text("   ")

        self.assertEqual(result, "Send me a non-empty text message.")

    async def test_reply_to_text_passes_prompt_to_ai_client(self):
        ai_client = FakeAIClient()
        service = ChatService(ai_client=ai_client)

        result = await service.reply_to_text("Tell me a joke")

        self.assertEqual(result, "text reply")
        self.assertEqual(ai_client.calls[0], ("text", "Tell me a joke"))

    async def test_reply_to_photo_uses_default_prompt_without_caption(self):
        ai_client = FakeAIClient()
        service = ChatService(ai_client=ai_client)
        attachment = BinaryAttachment(
            content=b"photo-bytes",
            filename="photo.jpg",
            mime_type="image/jpeg",
        )

        result = await service.reply_to_photo(attachment=attachment, caption=None)

        self.assertEqual(result, "photo reply")
        self.assertEqual(
            ai_client.calls[0],
            ("photo", "Describe the image and help the user.", b"photo-bytes", "image/jpeg"),
        )

    async def test_reply_to_voice_transcribes_audio_before_answer(self):
        ai_client = FakeAIClient()
        service = ChatService(ai_client=ai_client)
        attachment = BinaryAttachment(
            content=b"voice-bytes",
            filename="voice.ogg",
            mime_type="audio/ogg",
        )

        result = await service.reply_to_voice(attachment)

        self.assertEqual(result, "voice reply")
        self.assertEqual(ai_client.calls[0], ("transcribe", b"voice-bytes", "voice.ogg"))
        self.assertEqual(ai_client.calls[1], ("voice", "voice transcript"))

    async def test_reply_to_voice_handles_empty_transcript(self):
        service = ChatService(ai_client=EmptyTranscriptAIClient())
        attachment = BinaryAttachment(
            content=b"voice-bytes",
            filename="voice.ogg",
            mime_type="audio/ogg",
        )

        result = await service.reply_to_voice(attachment)

        self.assertEqual(result, "I could not recognize the voice message.")


if __name__ == "__main__":
    unittest.main()
