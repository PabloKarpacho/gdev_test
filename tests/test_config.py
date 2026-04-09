import unittest

from pydantic import ValidationError

from bot.config import Settings


class SettingsTests(unittest.TestCase):
    def test_requires_bot_token_and_openai_api_key(self):
        with self.assertRaises(ValidationError):
            Settings(_env_file=None)

    def test_uses_safe_defaults_for_optional_values(self):
        settings = Settings(
            _env_file=None,
            bot_token="telegram-token",
            openai_api_key="openai-token",
        )

        self.assertEqual(settings.openai_chat_model, "gpt-4.1-mini")
        self.assertIn("Telegram", settings.system_prompt)
