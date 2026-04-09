import unittest
from types import SimpleNamespace
from unittest.mock import patch

from bot.ai.client import OpenAIChatClient, get_langchain_message_types


class FakeLLM:
    def __init__(self, response_text: str = "assistant reply") -> None:
        self.messages = []
        self.response_text = response_text

    async def ainvoke(self, messages):
        self.messages.append(messages)
        return SimpleNamespace(content=self.response_text)


class FakeTranscriptionsAPI:
    def __init__(self, transcript: str = "voice transcript") -> None:
        self.calls = []
        self.transcript = transcript

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(text=self.transcript)


class FakeOpenAIClient:
    def __init__(self, transcript: str = "voice transcript") -> None:
        self.audio = SimpleNamespace(
            transcriptions=FakeTranscriptionsAPI(transcript=transcript)
        )


class OpenAIChatClientTests(unittest.IsolatedAsyncioTestCase):
    def test_get_langchain_message_types_raises_import_error_when_dependency_is_missing(
        self,
    ) -> None:
        with patch(
            "bot.ai.client.import_module",
            side_effect=ImportError("langchain_core is missing"),
        ):
            with self.assertRaises(ImportError):
                get_langchain_message_types()

    async def test_respond_to_text_uses_system_prompt_and_user_text(self):
        llm = FakeLLM(response_text="text answer")
        transcription_client = FakeOpenAIClient()
        client = OpenAIChatClient(
            llm=llm,
            transcription_client=transcription_client,
            system_prompt="You are helpful.",
            transcription_model="whisper-1",
        )

        result = await client.respond_to_text("Hello, bot")

        self.assertEqual(result, "text answer")
        sent_messages = llm.messages[0]
        self.assertEqual(sent_messages[0].content, "You are helpful.")
        self.assertEqual(sent_messages[1].content, "Hello, bot")

    async def test_respond_to_photo_builds_multimodal_message(self):
        llm = FakeLLM(response_text="photo answer")
        transcription_client = FakeOpenAIClient()
        client = OpenAIChatClient(
            llm=llm,
            transcription_client=transcription_client,
            system_prompt="You are helpful.",
            transcription_model="whisper-1",
        )

        result = await client.respond_to_photo(
            prompt="What is on this image?",
            photo_bytes=b"\xff\xd8\xff",
            mime_type="image/jpeg",
        )

        self.assertEqual(result, "photo answer")
        sent_messages = llm.messages[0]
        content = sent_messages[1].content
        self.assertEqual(content[0]["type"], "text")
        self.assertEqual(content[0]["text"], "What is on this image?")
        self.assertEqual(content[1]["type"], "image")
        self.assertEqual(content[1]["mime_type"], "image/jpeg")
        self.assertTrue(content[1]["base64"])

    async def test_transcribe_voice_sends_bytes_to_openai_audio_api(self):
        llm = FakeLLM()
        transcription_client = FakeOpenAIClient(transcript="transcribed text")
        client = OpenAIChatClient(
            llm=llm,
            transcription_client=transcription_client,
            system_prompt="You are helpful.",
            transcription_model="whisper-1",
        )

        result = await client.transcribe_voice(
            audio_bytes=b"voice-bytes",
            filename="voice.ogg",
        )

        self.assertEqual(result, "transcribed text")
        call = transcription_client.audio.transcriptions.calls[0]
        self.assertEqual(call["model"], "whisper-1")
        self.assertEqual(call["response_format"], "text")
        self.assertEqual(call["file"].name, "voice.ogg")

    async def test_extract_text_handles_content_blocks(self):
        llm = FakeLLM()
        transcription_client = FakeOpenAIClient()
        client = OpenAIChatClient(
            llm=llm,
            transcription_client=transcription_client,
            system_prompt="You are helpful.",
            transcription_model="whisper-1",
        )

        result = client._extract_text(
            SimpleNamespace(
                content=[
                    {"type": "reasoning", "text": "hidden"},
                    {"type": "text", "text": "First"},
                    {"type": "text", "text": "Second"},
                ]
            )
        )

        self.assertEqual(result, "First\nSecond")


if __name__ == "__main__":
    unittest.main()
