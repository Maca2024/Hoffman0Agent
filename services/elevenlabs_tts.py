"""ElevenLabs Text-to-Speech bridge for the Hofmann Agent.

Converts text responses to speech audio using the ElevenLabs API.
Supports streaming audio for real-time voice output.
"""

from __future__ import annotations

import logging
from io import BytesIO

import httpx

logger = logging.getLogger(__name__)

# Default voice — "Rachel" (warm, calm, suitable for consciousness guide)
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"

# Voice settings optimized for a consciousness guide
DEFAULT_VOICE_SETTINGS = {
    "stability": 0.65,
    "similarity_boost": 0.75,
    "style": 0.35,
    "use_speaker_boost": True,
}


class ElevenLabsTTSError(Exception):
    """Raised when TTS conversion fails."""


class ElevenLabsTTS:
    """ElevenLabs Text-to-Speech client."""

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(
        self,
        api_key: str,
        voice_id: str = DEFAULT_VOICE_ID,
        model_id: str = "eleven_multilingual_v2",
    ) -> None:
        self._api_key = api_key
        self._voice_id = voice_id
        self._model_id = model_id
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def text_to_speech(
        self,
        text: str,
        output_format: str = "mp3_44100_128",
    ) -> bytes:
        """Convert text to speech audio.

        Args:
            text: Text to convert to speech.
            output_format: Audio format (mp3_44100_128, pcm_16000, etc.)

        Returns:
            Audio bytes in the requested format.
        """
        url = f"/text-to-speech/{self._voice_id}"
        payload = {
            "text": text,
            "model_id": self._model_id,
            "voice_settings": DEFAULT_VOICE_SETTINGS,
        }

        try:
            response = await self._client.post(
                url,
                json=payload,
                params={"output_format": output_format},
            )
            response.raise_for_status()
            return response.content
        except httpx.HTTPStatusError as exc:
            logger.error("ElevenLabs TTS error: %s %s", exc.response.status_code, exc.response.text[:200])
            raise ElevenLabsTTSError(f"TTS failed: {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            logger.error("ElevenLabs connection error: %s", exc)
            raise ElevenLabsTTSError("Connection to ElevenLabs failed") from exc

    async def text_to_speech_stream(self, text: str):
        """Stream TTS audio chunks for real-time playback.

        Yields audio chunks as they arrive from the API.
        """
        url = f"/text-to-speech/{self._voice_id}/stream"
        payload = {
            "text": text,
            "model_id": self._model_id,
            "voice_settings": DEFAULT_VOICE_SETTINGS,
        }

        try:
            async with self._client.stream(
                "POST",
                url,
                json=payload,
                params={"output_format": "mp3_44100_128"},
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(chunk_size=1024):
                    yield chunk
        except httpx.HTTPStatusError as exc:
            logger.error("ElevenLabs stream error: %s", exc.response.status_code)
            raise ElevenLabsTTSError(f"TTS stream failed: {exc.response.status_code}") from exc

    async def get_voices(self) -> list[dict]:
        """List available voices."""
        try:
            response = await self._client.get("/voices")
            response.raise_for_status()
            return response.json().get("voices", [])
        except httpx.HTTPError as exc:
            logger.error("Failed to list voices: %s", exc)
            return []

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
