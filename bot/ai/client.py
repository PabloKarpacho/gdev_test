import base64
from importlib import import_module
from io import BytesIO
from collections.abc import Sequence
from typing import Protocol


class SupportsAsyncInvoke(Protocol):
    """Async chat model interface used by the application."""

    async def ainvoke(self, messages: Sequence[object]) -> object: ...


class SupportsTranscriptionsAPI(Protocol):
    """Audio transcription interface exposed by the OpenAI client."""

    async def create(self, *, model: str, file: BytesIO, response_format: str) -> object: ...


class SupportsAudioAPI(Protocol):
    """Nested audio API container exposed by the OpenAI client."""

    transcriptions: SupportsTranscriptionsAPI


class SupportsTranscriptionClient(Protocol):
    """Async transcription client contract used by the chat client."""

    audio: SupportsAudioAPI


def get_langchain_message_types() -> tuple[type[object], type[object]]:
    """
    ### Purpose
    Load LangChain message classes lazily.

    ### Parameters
    - **None**: The function imports message types on demand.

    ### Returns
    - **tuple[type, type]**: System and human message classes.
    """

    message_module = import_module("langchain_core.messages")
    return message_module.SystemMessage, message_module.HumanMessage


class AIClient(Protocol):
    """
    ### Purpose
    Describe the contract used by the chat service to interact with AI models.

    ### Parameters
    - **Protocol**: Python typing protocol base class.

    ### Returns
    - **AIClient**: Structural typing contract.
    """

    async def respond_to_text(self, prompt: str) -> str: ...

    async def respond_to_photo(
        self,
        prompt: str,
        photo_bytes: bytes,
        mime_type: str,
    ) -> str: ...

    async def transcribe_voice(self, audio_bytes: bytes, filename: str) -> str: ...

    async def respond_to_voice(self, transcript: str) -> str: ...


class OpenAIChatClient:
    """
    ### Purpose
    Wrap `langchain_openai.ChatOpenAI` and OpenAI audio transcription in one service.

    ### Parameters
    - **llm** (object): Async LangChain chat model with `ainvoke`.
    - **transcription_client** (object): Async OpenAI client with `audio.transcriptions.create`.
    - **system_prompt** (str): System prompt for all assistant responses.
    - **transcription_model** (str): OpenAI transcription model name.

    ### Returns
    - **OpenAIChatClient**: Ready-to-use AI client implementation.
    """

    def __init__(
        self,
        llm: SupportsAsyncInvoke,
        transcription_client: SupportsTranscriptionClient,
        system_prompt: str,
        transcription_model: str,
    ) -> None:
        self._llm = llm
        self._transcription_client = transcription_client
        self._system_prompt = system_prompt
        self._transcription_model = transcription_model

    async def respond_to_text(self, prompt: str) -> str:
        """
        ### Purpose
        Generate a text-only response through the LangChain chat model.

        ### Parameters
        - **prompt** (str): User text prompt.

        ### Returns
        - **str**: Assistant response text.
        """

        SystemMessage, HumanMessage = get_langchain_message_types()
        response = await self._llm.ainvoke(
            [
                SystemMessage(content=self._system_prompt),
                HumanMessage(content=prompt),
            ]
        )
        return self._extract_text(response)

    async def respond_to_photo(
        self,
        prompt: str,
        photo_bytes: bytes,
        mime_type: str,
    ) -> str:
        """
        ### Purpose
        Generate a response that uses both a user prompt and a photo attachment.

        ### Parameters
        - **prompt** (str): User prompt or generated image instruction.
        - **photo_bytes** (bytes): Raw image bytes downloaded from Telegram.
        - **mime_type** (str): MIME type of the image.

        ### Returns
        - **str**: Assistant response text.
        """

        SystemMessage, HumanMessage = get_langchain_message_types()
        encoded_photo = base64.b64encode(photo_bytes).decode("utf-8")
        response = await self._llm.ainvoke(
            [
                SystemMessage(content=self._system_prompt),
                HumanMessage(
                    content=[
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "base64": encoded_photo,
                            "mime_type": mime_type,
                        },
                    ]
                ),
            ]
        )
        return self._extract_text(response)

    async def transcribe_voice(self, audio_bytes: bytes, filename: str) -> str:
        """
        ### Purpose
        Convert a Telegram voice message into text.

        ### Parameters
        - **audio_bytes** (bytes): Raw voice note bytes.
        - **filename** (str): Filename used for the OpenAI upload payload.

        ### Returns
        - **str**: Transcript text extracted from the audio.
        """

        buffer = BytesIO(audio_bytes)
        buffer.name = filename
        response = await self._transcription_client.audio.transcriptions.create(
            model=self._transcription_model,
            file=buffer,
            response_format="text",
        )
        if isinstance(response, str):
            return response.strip()
        return getattr(response, "text", "").strip()

    async def respond_to_voice(self, transcript: str) -> str:
        """
        ### Purpose
        Generate a reply for a transcribed voice message.

        ### Parameters
        - **transcript** (str): Text extracted from the voice note.

        ### Returns
        - **str**: Assistant response text.
        """

        return await self.respond_to_text(
            f"The user sent a voice message. Transcript:\n{transcript}"
        )

    @staticmethod
    def _extract_text(response: object) -> str:
        """
        ### Purpose
        Normalize text content returned by the LLM client.

        ### Parameters
        - **response** (object): Response object returned by the LLM client.

        ### Returns
        - **str**: Plain text assistant response.
        """

        content = getattr(response, "content", response)
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            text_chunks: list[str] = []
            for block in content:
                if isinstance(block, str):
                    normalized = block.strip()
                elif isinstance(block, dict):
                    if block.get("type") != "text":
                        normalized = ""
                    else:
                        normalized = str(block.get("text", "")).strip()
                else:
                    normalized = str(getattr(block, "text", "")).strip()

                if normalized:
                    text_chunks.append(normalized)

            if text_chunks:
                return "\n".join(text_chunks)

        return str(content).strip()


def build_openai_chat_client(
    *,
    api_key: str,
    model_name: str,
    transcription_model: str,
    system_prompt: str,
) -> OpenAIChatClient:
    """
    ### Purpose
    Create the production AI client backed by `langchain_openai` and OpenAI.

    ### Parameters
    - **api_key** (str): OpenAI API key.
    - **model_name** (str): Chat model name for `ChatOpenAI`.
    - **transcription_model** (str): Audio transcription model name.
    - **system_prompt** (str): System prompt used for each response.

    ### Returns
    - **OpenAIChatClient**: Configured production AI client.
    """

    from langchain_openai import ChatOpenAI
    from openai import AsyncOpenAI

    llm = ChatOpenAI(
        api_key=api_key,
        model=model_name,
        temperature=0,
    )
    transcription_client = AsyncOpenAI(api_key=api_key)
    return OpenAIChatClient(
        llm=llm,
        transcription_client=transcription_client,
        system_prompt=system_prompt,
        transcription_model=transcription_model,
    )
