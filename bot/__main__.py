from bot.ai.client import build_openai_chat_client
from bot.app import get_bot, get_dispatcher
from bot.common.logging import get_logger, setup_logging
from bot.config import load_settings
from bot.run import run_in_pooling
from bot.services.chat import ChatService

logger = get_logger()


def main() -> None:
    """
    ### Purpose
    Start the Telegram AI bot from the command line.

    ### Parameters
    - **None**: Runtime settings are loaded from the environment.

    ### Returns
    - **None**: The process starts Telegram polling and blocks until shutdown.
    """

    settings = load_settings()
    setup_logging(level=settings.log_level)
    logger.info("Starting bot application")

    bot = get_bot(token=settings.bot_token)
    dispatcher = get_dispatcher()
    ai_client = build_openai_chat_client(
        api_key=settings.openai_api_key,
        model_name=settings.openai_chat_model,
        transcription_model=settings.openai_transcription_model,
        system_prompt=settings.system_prompt,
    )
    chat_service = ChatService(ai_client=ai_client)

    logger.info("Bot and dispatcher are initialized, starting polling")
    run_in_pooling(bot=bot, dp=dispatcher, chat_service=chat_service)


if __name__ == "__main__":
    main()
