from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from bot.config import Settings, resolve_env_file
from bot.telegram.files import (
    AttachmentValidationError,
    download_telegram_file,
    download_photo_attachment,
    download_voice_attachment,
)


class FakeBot:
    def __init__(self) -> None:
        self.requested_file_ids = []
        self.downloaded_paths = []

    async def get_file(self, file_id: str):
        self.requested_file_ids.append(file_id)
        return SimpleNamespace(file_path=f"telegram/{file_id}")

    async def download_file(self, file_path: str):
        self.downloaded_paths.append(file_path)
        return BytesIO(b"downloaded-bytes")


class MissingFilePathBot(FakeBot):
    async def get_file(self, file_id: str):
        self.requested_file_ids.append(file_id)
        return SimpleNamespace(file_path=None)


class SettingsAndFilesTests(unittest.IsolatedAsyncioTestCase):
    async def test_settings_loads_new_bot_and_openai_fields(self):
        with TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "BOT_TOKEN=test-telegram-token",
                        "OPENAI_API_KEY=test-openai-key",
                        "OPENAI_MODEL=gpt-4.1-mini",
                        "OPENAI_TRANSCRIPTION_MODEL=whisper-1",
                    ]
                )
            )

            settings = Settings(_env_file=env_path)

        self.assertEqual(settings.bot_token, "test-telegram-token")
        self.assertEqual(settings.openai_api_key, "test-openai-key")
        self.assertEqual(settings.openai_model, "gpt-4.1-mini")
        self.assertEqual(settings.openai_transcription_model, "whisper-1")

    async def test_download_photo_attachment_uses_largest_photo_size(self):
        bot = FakeBot()
        photo_sizes = [
            SimpleNamespace(file_id="small-photo", file_size=10),
            SimpleNamespace(file_id="large-photo", file_size=20),
        ]

        attachment = await download_photo_attachment(bot=bot, photo_sizes=photo_sizes)

        self.assertEqual(bot.requested_file_ids, ["large-photo"])
        self.assertEqual(bot.downloaded_paths, ["telegram/large-photo"])
        self.assertEqual(attachment.content, b"downloaded-bytes")
        self.assertEqual(attachment.mime_type, "image/jpeg")

    async def test_download_voice_attachment_preserves_voice_metadata(self):
        bot = FakeBot()
        voice = SimpleNamespace(file_id="voice-id", mime_type="audio/ogg")

        attachment = await download_voice_attachment(bot=bot, voice=voice)

        self.assertEqual(bot.requested_file_ids, ["voice-id"])
        self.assertEqual(bot.downloaded_paths, ["telegram/voice-id"])
        self.assertEqual(attachment.filename, "voice-id.ogg")
        self.assertEqual(attachment.mime_type, "audio/ogg")

    async def test_download_voice_attachment_uses_extension_matching_mime_type(self):
        bot = FakeBot()
        voice = SimpleNamespace(file_id="voice-id", mime_type="audio/mpeg")

        attachment = await download_voice_attachment(bot=bot, voice=voice)

        self.assertEqual(attachment.filename, "voice-id.mp3")
        self.assertEqual(attachment.mime_type, "audio/mpeg")

    async def test_download_photo_attachment_rejects_large_files(self):
        bot = FakeBot()
        photo_sizes = [
            SimpleNamespace(file_id="large-photo", file_size=10 * 1024 * 1024 + 1),
        ]

        with self.assertRaises(AttachmentValidationError):
            await download_photo_attachment(bot=bot, photo_sizes=photo_sizes)

    async def test_download_telegram_file_rejects_missing_file_path(self):
        bot = MissingFilePathBot()

        with self.assertRaises(AttachmentValidationError):
            await download_telegram_file(bot=bot, file_id="missing-path")

    async def test_download_voice_attachment_rejects_unsupported_mime_type(self):
        bot = FakeBot()
        voice = SimpleNamespace(
            file_id="voice-id",
            mime_type="audio/flac",
            file_size=1024,
        )

        with self.assertRaises(AttachmentValidationError):
            await download_voice_attachment(bot=bot, voice=voice)

    async def test_download_voice_attachment_defaults_missing_mime_type(self):
        bot = FakeBot()
        voice = SimpleNamespace(file_id="voice-id", mime_type=None)

        attachment = await download_voice_attachment(bot=bot, voice=voice)

        self.assertEqual(attachment.filename, "voice-id.ogg")
        self.assertEqual(attachment.mime_type, "audio/ogg")


class ResolveEnvFileTests(unittest.TestCase):
    def test_resolve_env_file_uses_project_base_dir_without_parent_lookup(self):
        with TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            (workspace / "local.env").write_text("SHOULD_NOT_BE_USED=1")
            project_dir = workspace / "project"
            project_dir.mkdir()
            env_path = project_dir / ".env"
            env_path.write_text("BOT_TOKEN=test")

            resolved = resolve_env_file(base_dir=project_dir)

        self.assertEqual(resolved, str(env_path))


if __name__ == "__main__":
    unittest.main()
