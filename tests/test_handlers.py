from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import unittest

from bot.handlers.chat import (
    ATTACHMENT_ERROR_REPLY,
    PROCESSING_ERROR_REPLY,
    get_message_logger,
    handle_photo_message,
    handle_text_message,
    handle_voice_message,
)
from bot.handlers.start import handle_start, get_start_logger
from bot.telegram.files import AttachmentValidationError
from bot.services.chat import BinaryAttachment


class FakeMessage:
    def __init__(self, *, text=None, caption=None, photo=None, voice=None) -> None:
        self.text = text
        self.caption = caption
        self.photo = photo or []
        self.voice = voice
        self.chat = SimpleNamespace(id=101)
        self.from_user = SimpleNamespace(id=202)
        self.message_id = 303
        self.answers = []

    async def answer(self, text: str, **kwargs) -> None:
        self.answers.append((text, kwargs))


class HandlerTests(unittest.IsolatedAsyncioTestCase):
    def test_get_message_logger_binds_message_context(self):
        message = FakeMessage(text="Hello")

        with patch("bot.handlers.chat.logger") as logger_mock:
            logger_instance = object()
            logger_mock.bind.return_value = logger_instance

            result = get_message_logger(message)

        logger_mock.bind.assert_called_once_with(
            chat_id=101,
            user_id=202,
            message_id=303,
            message_type="text",
        )
        self.assertIs(result, logger_instance)

    def test_get_start_logger_binds_command_context(self):
        message = FakeMessage(text="/start")

        with patch("bot.handlers.start.logger") as logger_mock:
            logger_instance = object()
            logger_mock.bind.return_value = logger_instance

            result = get_start_logger(message)

        logger_mock.bind.assert_called_once_with(
            chat_id=101,
            user_id=202,
            message_id=303,
            message_type="command_start",
        )
        self.assertIs(result, logger_instance)

    async def test_handle_start_sends_welcome_message(self):
        message = FakeMessage()

        with patch("bot.handlers.start.logger") as logger_mock:
            bound_logger = logger_mock.bind.return_value

            await handle_start(message)

        self.assertEqual(len(message.answers), 1)
        self.assertIn("Telegram bot", message.answers[0][0])
        self.assertGreaterEqual(bound_logger.info.call_count, 2)

    async def test_handle_text_message_uses_chat_service(self):
        message = FakeMessage(text="Hello")
        chat_service = AsyncMock()
        chat_service.reply_to_text.return_value = "AI answer"

        with patch("bot.handlers.chat.logger") as logger_mock:
            bound_logger = logger_mock.bind.return_value

            await handle_text_message(message=message, chat_service=chat_service)

        chat_service.reply_to_text.assert_awaited_once_with("Hello")
        self.assertEqual(message.answers[0][0], "AI answer")
        self.assertGreaterEqual(bound_logger.info.call_count, 3)

    async def test_handle_text_message_returns_processing_error_on_service_failure(self):
        message = FakeMessage(text="Hello")
        chat_service = AsyncMock()
        chat_service.reply_to_text.side_effect = RuntimeError("provider failure")

        await handle_text_message(message=message, chat_service=chat_service)

        chat_service.reply_to_text.assert_awaited_once_with("Hello")
        self.assertEqual(message.answers[0][0], PROCESSING_ERROR_REPLY)

    async def test_handle_photo_message_downloads_photo_before_reply(self):
        message = FakeMessage(
            caption="What is this?",
            photo=[SimpleNamespace(file_id="1", file_size=10)],
        )
        bot = object()
        chat_service = AsyncMock()
        chat_service.reply_to_photo.return_value = "photo answer"
        attachment = BinaryAttachment(
            content=b"photo",
            filename="photo.jpg",
            mime_type="image/jpeg",
        )

        with (
            patch(
                "bot.handlers.chat.download_photo_attachment",
                new=AsyncMock(return_value=attachment),
            ) as download_mock,
            patch("bot.handlers.chat.logger") as logger_mock,
        ):
            bound_logger = logger_mock.bind.return_value
            await handle_photo_message(
                message=message,
                bot=bot,
                chat_service=chat_service,
            )

        download_mock.assert_awaited_once_with(bot=bot, photo_sizes=message.photo)
        chat_service.reply_to_photo.assert_awaited_once_with(
            attachment=attachment,
            caption="What is this?",
        )
        self.assertEqual(message.answers[0][0], "photo answer")
        self.assertGreaterEqual(bound_logger.info.call_count, 4)

    async def test_handle_voice_message_downloads_voice_before_reply(self):
        message = FakeMessage(voice=SimpleNamespace(file_id="voice-id"))
        bot = object()
        chat_service = AsyncMock()
        chat_service.reply_to_voice.return_value = "voice answer"
        attachment = BinaryAttachment(
            content=b"voice",
            filename="voice.ogg",
            mime_type="audio/ogg",
        )

        with (
            patch(
                "bot.handlers.chat.download_voice_attachment",
                new=AsyncMock(return_value=attachment),
            ) as download_mock,
            patch("bot.handlers.chat.logger") as logger_mock,
        ):
            bound_logger = logger_mock.bind.return_value
            await handle_voice_message(
                message=message,
                bot=bot,
                chat_service=chat_service,
            )

        download_mock.assert_awaited_once_with(bot=bot, voice=message.voice)
        chat_service.reply_to_voice.assert_awaited_once_with(attachment)
        self.assertEqual(message.answers[0][0], "voice answer")
        self.assertGreaterEqual(bound_logger.info.call_count, 4)

    async def test_handle_photo_message_returns_validation_error_to_user(self):
        message = FakeMessage(
            caption="What is this?",
            photo=[SimpleNamespace(file_id="1", file_size=10)],
        )
        bot = object()
        chat_service = AsyncMock()

        with patch(
            "bot.handlers.chat.download_photo_attachment",
            new=AsyncMock(side_effect=AttachmentValidationError("bad photo")),
        ):
            await handle_photo_message(
                message=message,
                bot=bot,
                chat_service=chat_service,
            )

        chat_service.reply_to_photo.assert_not_called()
        self.assertEqual(message.answers[0][0], ATTACHMENT_ERROR_REPLY)

    async def test_handle_voice_message_returns_processing_error_on_service_failure(self):
        message = FakeMessage(voice=SimpleNamespace(file_id="voice-id"))
        bot = object()
        chat_service = AsyncMock()
        attachment = BinaryAttachment(
            content=b"voice",
            filename="voice.ogg",
            mime_type="audio/ogg",
        )
        chat_service.reply_to_voice.side_effect = RuntimeError("provider failure")

        with patch(
            "bot.handlers.chat.download_voice_attachment",
            new=AsyncMock(return_value=attachment),
        ):
            await handle_voice_message(
                message=message,
                bot=bot,
                chat_service=chat_service,
            )

        self.assertEqual(message.answers[0][0], PROCESSING_ERROR_REPLY)


if __name__ == "__main__":
    unittest.main()
