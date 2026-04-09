# Telegram ChatGPT Bot

Минимальный Telegram-бот на `aiogram 3` с OpenAI-интеграцией для:
- текстовых сообщений
- фотографий
- голосовых сообщений

Бот работает в `polling` режиме, использует `langchain_openai.ChatOpenAI` для text/photo ответов и OpenAI transcription API для voice flow.

## Project Layout

- `bot/__main__.py` — основной entrypoint приложения
- `main.py` — тонкий совместимый wrapper для запуска через `python main.py`
- `bot/config.py` — загрузка и валидация env-конфигурации
- `bot/ai/client.py` — OpenAI/LangChain клиент
- `bot/services/chat.py` — orchestration для text/photo/voice
- `bot/telegram/files.py` — скачивание и валидация Telegram-вложений
- `bot/handlers/` — Telegram handlers и router wiring
- `bot/run.py` — lifecycle polling и shutdown

## Requirements

- Python `3.12+`
- `uv`
- Telegram bot token
- OpenAI API key

## Configuration

Скопируйте значения из `.env.example` в локальный `.env` или `local.env`.

Поддерживаемые переменные:

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `BOT_TOKEN` | yes | none | Legacy alias: `BOT_CLIENT_TOKEN` |
| `OPENAI_API_KEY` | yes | none | Legacy alias: `OPENAI_API_TOKEN` |
| `OPENAI_CHAT_MODEL` | no | `gpt-4.1-mini` | Legacy alias: `OPENAI_MODEL` |
| `OPENAI_TRANSCRIPTION_MODEL` | no | `gpt-4o-mini-transcribe` | Legacy alias: `OPENAI_AUDIO_MODEL` |
| `SYSTEM_PROMPT` | no | built-in prompt | Uses the settings field name directly |
| `LOG_LEVEL` | no | `INFO` | Standard Loguru level |

Пример:

```env
BOT_TOKEN=your-telegram-bot-token
OPENAI_API_KEY=your-openai-api-key
OPENAI_CHAT_MODEL=gpt-4.1-mini
OPENAI_TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe
SYSTEM_PROMPT=You are a Telegram assistant powered by OpenAI. Answer clearly, helpfully, and in the same language as the user.
LOG_LEVEL=INFO
```

`bot/config.py` ищет env-файл только в корне проекта: сначала `local.env`, затем `.env`.

## Install And Run

Установка зависимостей:

```bash
uv sync
```

Запуск:

```bash
uv run python -m bot
```

Альтернативы:

```bash
uv run telegram-chatgpt-bot
uv run python main.py
```

## Runtime Behavior

- `text` -> сообщение уходит в `ChatOpenAI`
- `photo` -> скачивается крупнейшая Telegram-версия фото, проходит size validation, затем отправляется как multimodal prompt
- `voice` -> скачивается аудио, валидируется по MIME type/size, транскрибируется через OpenAI, затем transcript отправляется в chat model
- если transcript пустой, бот отвечает fallback-сообщением: `I could not recognize the voice message.`

## Operational Limits

Текущие защитные ограничения:

- фото: до `10 MB`
- голосовые: до `20 MB`
- voice MIME types: `audio/ogg`, `audio/mpeg`, `audio/mp3`, `audio/wav`, `audio/x-wav`, `audio/mp4`

Если вложение слишком большое или неподдерживаемое, пользователь получает безопасный ответ без проброса внутренней ошибки.

## Failure Behavior

- ошибки валидации вложений -> пользователь получает понятный ответ в чате
- пустая транскрипция -> fallback-ответ из service layer
- ошибки Telegram/OpenAI во время runtime логируются и пробрасываются выше; сейчас для них нет отдельного graceful recovery reply
- ошибки старта polling приводят к исключению, но HTTP-сессия бота теперь закрывается корректно

## Testing

Проект использует `unittest`, не `pytest`.

Запуск тестов:

```bash
uv run python -m unittest discover -s tests -v
```

Проверка покрытия:

```bash
uv run coverage run -m unittest discover -s tests
uv run coverage report
```

Текущее покрытие: `91%`.

## Runtime Notes

- используется `polling`, не webhook
- FSM storage: `MemoryStorage`
- текущее состояние подходит для одиночного процесса; для horizontal scaling или persistent state нужен внешний storage

## Security Notes

- секреты должны храниться только в env-файлах или секретном хранилище
- `.env` исключен из git
- входящие вложения ограничены по размеру и типу до передачи в OpenAI
- после компрометации токенов их нужно перевыпустить
