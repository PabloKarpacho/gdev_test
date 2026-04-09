from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
import unittest

from aiogram import Bot, Router
from aiogram.fsm.storage.memory import MemoryStorage

from bot import __main__ as bot_main
from bot.app import get_bot, get_dispatcher
from bot.common.logging import get_logger
from bot.handlers import setup_routers
from bot.handlers.chat import build_chat_router
from bot.handlers.start import build_start_router
from bot.run import run_in_pooling
from bot.services.chat import ChatService
from bot.setup_bot import set_commands, setup_bot, setup_dispatcher


class FakeBot:
    def __init__(self) -> None:
        self.deleted_webhook = False
        self.commands = None
        self.session = SimpleNamespace(close=AsyncMock())

    async def delete_webhook(self) -> None:
        self.deleted_webhook = True

    async def set_my_commands(self, commands) -> None:
        self.commands = commands


class FakeDispatcher:
    def __init__(self) -> None:
        self.included_routers = []
        self.polled_bot = None

    def include_router(self, router) -> None:
        self.included_routers.append(router)

    async def start_polling(self, bot) -> None:
        self.polled_bot = bot


class BootstrapTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_bot_returns_aiogram_bot(self):
        bot = get_bot("123456:ABCDEF")

        self.assertIsInstance(bot, Bot)
        self.assertEqual(bot.token, "123456:ABCDEF")
        await bot.session.close()

    async def test_get_dispatcher_uses_memory_storage(self):
        dispatcher = get_dispatcher()

        self.assertIsInstance(dispatcher.storage, MemoryStorage)

    async def test_setup_routers_registers_start_and_chat_routers(self):
        dispatcher = FakeDispatcher()
        chat_service = Mock(spec=ChatService)

        setup_routers(dispatcher=dispatcher, chat_service=chat_service)

        self.assertEqual(len(dispatcher.included_routers), 2)
        self.assertTrue(
            all(isinstance(router, Router) for router in dispatcher.included_routers)
        )

    async def test_build_router_helpers_return_router_instances(self):
        start_router = build_start_router()
        chat_router = build_chat_router(chat_service=Mock(spec=ChatService))

        self.assertIsInstance(start_router, Router)
        self.assertIsInstance(chat_router, Router)
        text_filter = chat_router.message.handlers[2].filters[0].magic
        self.assertFalse(
            text_filter.resolve(SimpleNamespace(text="/start", photo=None, voice=None))
        )
        self.assertTrue(
            text_filter.resolve(SimpleNamespace(text="hello", photo=None, voice=None))
        )

    async def test_set_commands_registers_start_command(self):
        bot = FakeBot()

        await set_commands(bot)

        self.assertEqual(len(bot.commands), 1)
        self.assertEqual(bot.commands[0].command, "start")

    async def test_setup_dispatcher_keeps_default_configuration(self):
        dispatcher = FakeDispatcher()

        self.assertIsNone(setup_dispatcher(dispatcher))

    async def test_setup_bot_calls_all_setup_steps(self):
        bot = FakeBot()
        dispatcher = FakeDispatcher()
        chat_service = Mock(spec=ChatService)

        with (
            patch("bot.setup_bot.set_commands", new=AsyncMock()) as set_commands_mock,
            patch("bot.setup_bot.setup_routers") as setup_routers_mock,
            patch("bot.setup_bot.setup_dispatcher") as setup_dispatcher_mock,
        ):
            await setup_bot(bot=bot, dispatcher=dispatcher, chat_service=chat_service)

        set_commands_mock.assert_awaited_once_with(bot)
        setup_routers_mock.assert_called_once_with(
            dispatcher=dispatcher,
            chat_service=chat_service,
        )
        setup_dispatcher_mock.assert_called_once_with(dispatcher)

    async def test_main_wires_runtime_dependencies(self):
        settings = SimpleNamespace(
            bot_token="telegram-token",
            openai_api_key="openai-key",
            openai_chat_model="gpt-4.1-mini",
            openai_transcription_model="gpt-4o-mini-transcribe",
            system_prompt="System",
            log_level="INFO",
        )

        with (
            patch.object(bot_main, "load_settings", return_value=settings),
            patch.object(bot_main, "setup_logging") as setup_logging_mock,
            patch.object(bot_main, "get_bot", return_value="bot") as get_bot_mock,
            patch.object(
                bot_main,
                "get_dispatcher",
                return_value="dispatcher",
            ) as get_dispatcher_mock,
            patch.object(
                bot_main,
                "build_openai_chat_client",
                return_value="ai-client",
            ) as build_client_mock,
            patch.object(bot_main, "ChatService", return_value="chat-service") as chat_service_cls,
            patch.object(bot_main, "run_in_pooling") as run_in_pooling_mock,
        ):
            bot_main.main()

        setup_logging_mock.assert_called_once_with(level="INFO")
        get_bot_mock.assert_called_once_with(token="telegram-token")
        get_dispatcher_mock.assert_called_once_with()
        build_client_mock.assert_called_once_with(
            api_key="openai-key",
            model_name="gpt-4.1-mini",
            transcription_model="gpt-4o-mini-transcribe",
            system_prompt="System",
        )
        chat_service_cls.assert_called_once_with(ai_client="ai-client")
        run_in_pooling_mock.assert_called_once_with(
            bot="bot",
            dp="dispatcher",
            chat_service="chat-service",
        )

    async def test_get_logger_returns_logger_instance(self):
        self.assertIsNotNone(get_logger())


class BootstrapSyncTests(unittest.TestCase):
    def test_run_in_pooling_deletes_webhook_sets_up_and_polls(self):
        bot = FakeBot()
        dispatcher = FakeDispatcher()
        chat_service = Mock(spec=ChatService)

        with patch("bot.run.setup_bot", new=AsyncMock()) as setup_bot_mock:
            run_in_pooling(bot=bot, dp=dispatcher, chat_service=chat_service)

        self.assertTrue(bot.deleted_webhook)
        self.assertIs(dispatcher.polled_bot, bot)
        setup_bot_mock.assert_awaited_once_with(
            bot=bot,
            dispatcher=dispatcher,
            chat_service=chat_service,
        )

    def test_run_in_pooling_closes_bot_session_when_setup_fails(self):
        bot = FakeBot()
        dispatcher = FakeDispatcher()
        chat_service = Mock(spec=ChatService)

        with (
            patch("bot.run.setup_bot", new=AsyncMock(side_effect=RuntimeError("boom"))),
            self.assertRaises(RuntimeError),
        ):
            run_in_pooling(bot=bot, dp=dispatcher, chat_service=chat_service)

        bot.session.close.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()
