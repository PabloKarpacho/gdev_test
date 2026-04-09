import sys
from typing import Protocol

from loguru import logger

DEFAULT_LOG_CONTEXT = {
    "chat_id": "-",
    "user_id": "-",
    "message_id": "-",
    "message_type": "-",
}


class LoggerProtocol(Protocol):
    """Minimal logger surface used across the application."""

    def debug(self, message: str, *args: object, **kwargs: object) -> object: ...

    def info(self, message: str, *args: object, **kwargs: object) -> object: ...

    def warning(self, message: str, *args: object, **kwargs: object) -> object: ...

    def error(self, message: str, *args: object, **kwargs: object) -> object: ...

    def exception(self, message: str, *args: object, **kwargs: object) -> object: ...

    def bind(self, **kwargs: object) -> "LoggerProtocol": ...


def setup_logging(level: str = "INFO") -> None:
    """
    ### Purpose
    Configure the shared Loguru logger for the application runtime.

    ### Parameters
    - **level** (str): Minimal log level that should be emitted to stdout, for example `INFO` or `DEBUG`.

    ### Returns
    - **None**: The function updates the process-wide Loguru configuration.
    """

    logger.remove()
    logger.configure(extra=DEFAULT_LOG_CONTEXT)
    logger.add(
        sys.stdout,
        level=level.upper(),
        backtrace=True,
        diagnose=False,
        enqueue=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level> | "
            "chat_id=<magenta>{extra[chat_id]}</magenta> "
            "user_id=<magenta>{extra[user_id]}</magenta> "
            "message_id=<magenta>{extra[message_id]}</magenta> "
            "message_type=<magenta>{extra[message_type]}</magenta>"
        ),
    )


def get_logger() -> LoggerProtocol:
    """
    ### Purpose
    Return the shared Loguru logger instance used by application modules.

    ### Parameters
    - **None**: The function returns the already configured shared logger.

    ### Returns
    - **LoggerProtocol**: Shared process-wide logger instance that supports structured logging.
    """

    return logger
