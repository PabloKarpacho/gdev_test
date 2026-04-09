from types import ModuleType
from unittest.mock import patch
import sys
import unittest

from bot.ai.client import OpenAIChatClient, build_openai_chat_client


class FakeChatOpenAI:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


class FakeAsyncOpenAI:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key


class ClientFactoryTests(unittest.TestCase):
    def test_build_openai_chat_client_uses_langchain_and_openai_clients(self):
        fake_langchain_module = ModuleType("langchain_openai")
        fake_langchain_module.ChatOpenAI = FakeChatOpenAI
        fake_openai_module = ModuleType("openai")
        fake_openai_module.AsyncOpenAI = FakeAsyncOpenAI

        with patch.dict(
            sys.modules,
            {
                "langchain_openai": fake_langchain_module,
                "openai": fake_openai_module,
            },
        ):
            client = build_openai_chat_client(
                api_key="openai-key",
                model_name="gpt-4.1-mini",
                transcription_model="gpt-4o-mini-transcribe",
                system_prompt="System prompt",
            )

        self.assertIsInstance(client, OpenAIChatClient)
        self.assertEqual(client._llm.kwargs["api_key"], "openai-key")
        self.assertEqual(client._llm.kwargs["model"], "gpt-4.1-mini")
        self.assertEqual(client._transcription_client.api_key, "openai-key")


if __name__ == "__main__":
    unittest.main()
