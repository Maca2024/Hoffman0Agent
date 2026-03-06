"""ElevenLabs Text-to-Speech bridge for the Hofmann Agent.

Per-molecule voice configuration: each substance gets a unique voice
and voice settings tuned to match its consciousness state.
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-molecule voice configuration
# ---------------------------------------------------------------------------
# Each substance gets a voice that matches its character:
#   voice_id, stability, similarity_boost, style, speed

MOLECULE_VOICES: dict[int, dict] = {
    1: {  # LSD — precise, crystalline, clear
        "voice_id": "onwK4e9ZLuTAKqWW03F9",  # Daniel - Steady Broadcaster (British)
        "stability": 0.75,
        "similarity_boost": 0.80,
        "style": 0.20,
    },
    2: {  # DMT — intense, alien, rapid
        "voice_id": "N2lVS1w4EtoT3dr4eOWO",  # Callum - Husky Trickster
        "stability": 0.35,
        "similarity_boost": 0.65,
        "style": 0.60,
    },
    3: {  # Psilocybin — organic, warm, slow
        "voice_id": "cjVigY5qzO86Huf0OWal",  # Eric - Smooth, Trustworthy
        "stability": 0.70,
        "similarity_boost": 0.75,
        "style": 0.30,
    },
    4: {  # Cannabis — laid-back, relaxed, casual
        "voice_id": "CwhRBWXzGAHq8TQ4Fs17",  # Roger - Laid-Back, Casual
        "stability": 0.55,
        "similarity_boost": 0.70,
        "style": 0.40,
    },
    5: {  # Mescaline — deep, ancient, measured
        "voice_id": "pqHfZKP75CvOlQylNhV4",  # Bill - Wise, Mature, Balanced
        "stability": 0.80,
        "similarity_boost": 0.75,
        "style": 0.15,
    },
    6: {  # Ibogaine — direct, confronting, dark
        "voice_id": "pNInz6obpgDQGcFmaJgB",  # Adam - Dominant, Firm
        "stability": 0.60,
        "similarity_boost": 0.80,
        "style": 0.45,
    },
    7: {  # 5-MeO-DMT — near-silent, ethereal, minimal
        "voice_id": "SAz9YHcvj6GT2YYXdXww",  # River - Relaxed, Neutral
        "stability": 0.90,
        "similarity_boost": 0.60,
        "style": 0.05,
    },
    8: {  # MDMA — warm, empathic, heartfelt
        "voice_id": "pFZP5JQG7iQjIQuC4Bku",  # Lily - Velvety Actress (British, warm)
        "stability": 0.55,
        "similarity_boost": 0.85,
        "style": 0.50,
    },
    9: {  # Ketamine — detached, cold, clinical
        "voice_id": "nPczCjzI2devNBz1zQrb",  # Brian - Deep, Resonant
        "stability": 0.85,
        "similarity_boost": 0.70,
        "style": 0.10,
    },
}

# Fallback for unknown dimensions
DEFAULT_VOICE = {
    "voice_id": "onwK4e9ZLuTAKqWW03F9",
    "stability": 0.65,
    "similarity_boost": 0.75,
    "style": 0.35,
}


class ElevenLabsTTSError(Exception):
    """Raised when TTS conversion fails."""


class ElevenLabsTTS:
    """ElevenLabs Text-to-Speech client with per-molecule voice selection."""

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(
        self,
        api_key: str,
        model_id: str = "eleven_multilingual_v2",
    ) -> None:
        self._api_key = api_key
        self._model_id = model_id
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def _get_voice_config(self, dimension: int) -> dict:
        """Get voice configuration for a specific molecule/dimension."""
        return MOLECULE_VOICES.get(dimension, DEFAULT_VOICE)

    async def text_to_speech(
        self,
        text: str,
        dimension: int = 1,
        output_format: str = "mp3_44100_128",
    ) -> bytes:
        """Convert text to speech audio using molecule-specific voice.

        Args:
            text: Text to convert to speech.
            dimension: Active molecule dimension (1-9) for voice selection.
            output_format: Audio format.

        Returns:
            Audio bytes in the requested format.
        """
        config = self._get_voice_config(dimension)
        voice_id = config["voice_id"]
        url = f"/text-to-speech/{voice_id}"

        payload = {
            "text": text,
            "model_id": self._model_id,
            "voice_settings": {
                "stability": config["stability"],
                "similarity_boost": config["similarity_boost"],
                "style": config["style"],
                "use_speaker_boost": True,
            },
        }

        try:
            response = await self._client.post(
                url,
                json=payload,
                params={"output_format": output_format},
            )
            response.raise_for_status()
            logger.info("TTS OK: D%d voice=%s (%d bytes)", dimension, voice_id[:8], len(response.content))
            return response.content
        except httpx.HTTPStatusError as exc:
            logger.error("ElevenLabs TTS error: %s %s", exc.response.status_code, exc.response.text[:200])
            raise ElevenLabsTTSError(f"TTS failed: {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            logger.error("ElevenLabs connection error: %s", exc)
            raise ElevenLabsTTSError("Connection to ElevenLabs failed") from exc

    async def text_to_speech_stream(self, text: str, dimension: int = 1):
        """Stream TTS audio chunks using molecule-specific voice."""
        config = self._get_voice_config(dimension)
        voice_id = config["voice_id"]
        url = f"/text-to-speech/{voice_id}/stream"

        payload = {
            "text": text,
            "model_id": self._model_id,
            "voice_settings": {
                "stability": config["stability"],
                "similarity_boost": config["similarity_boost"],
                "style": config["style"],
                "use_speaker_boost": True,
            },
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

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
