"""Claude API integration for the Hofmann 9D Agent."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

import anthropic

logger = logging.getLogger(__name__)


class ClaudeServiceError(Exception):
    """Raised when the Claude API returns an unrecoverable error."""


class ClaudeService:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6") -> None:
        """Initialize Anthropic client.

        Args:
            api_key: Anthropic API key.
            model: Model ID to use for all requests.
        """
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def analyze(
        self,
        message: str,
        system_prompt: str,
        conversation_history: list[dict] | None = None,
        max_tokens: int = 4096,
    ) -> str:
        """Send a message to Claude and return the full text response.

        Args:
            message: The user message to send.
            system_prompt: The 9D system prompt to use.
            conversation_history: Prior turns as a list of
                ``{"role": "user"|"assistant", "content": str}`` dicts.
            max_tokens: Maximum tokens in the response.

        Returns:
            The assistant's response as a plain string.

        Raises:
            ClaudeServiceError: On API errors that cannot be retried.
        """
        messages = self._build_messages(message, conversation_history)

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages,
            )
        except anthropic.APIStatusError as exc:
            logger.error("Claude API status error: %s %s", exc.status_code, exc.message)
            raise ClaudeServiceError(f"API error {exc.status_code}: {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            logger.error("Claude API connection error: %s", exc)
            raise ClaudeServiceError("Connection to Claude API failed") from exc

        return response.content[0].text

    async def stream_analyze(
        self,
        message: str,
        system_prompt: str,
        conversation_history: list[dict] | None = None,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """Stream a Claude response token by token.

        Yields individual text deltas as they arrive from the API.
        Suitable for real-time voice and streaming UI.

        Args:
            message: The user message to send.
            system_prompt: The 9D system prompt to use.
            conversation_history: Prior turns as a list of
                ``{"role": "user"|"assistant", "content": str}`` dicts.
            max_tokens: Maximum tokens in the response.

        Yields:
            Text delta strings as they stream from the API.

        Raises:
            ClaudeServiceError: On API errors that cannot be retried.
        """
        messages = self._build_messages(message, conversation_history)

        try:
            async with self._client.messages.stream(
                model=self._model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except anthropic.APIStatusError as exc:
            logger.error("Claude stream API status error: %s %s", exc.status_code, exc.message)
            raise ClaudeServiceError(f"API error {exc.status_code}: {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            logger.error("Claude stream connection error: %s", exc)
            raise ClaudeServiceError("Connection to Claude API failed") from exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_messages(
        message: str,
        conversation_history: list[dict] | None,
    ) -> list[dict]:
        """Combine conversation history with the new user message.

        Args:
            message: The current user message.
            conversation_history: Existing turns (may be None or empty).

        Returns:
            A messages list ready for the Anthropic API.
        """
        messages: list[dict] = []

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": message})
        return messages
