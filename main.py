"""Hofmann Agent — FastAPI application.

9D Psychedelic Consciousness Agent backed by Claude.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Annotated  # noqa: F401 — kept for future Field constraints

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from services.claude_service import ClaudeService, ClaudeServiceError
from services.elevenlabs_tts import ElevenLabsTTS, ElevenLabsTTSError
from services.knowledge_loader import KnowledgeBase
from services.memory import MemoryManager
from services.prompt_builder import PromptBuilder

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

_KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"

_knowledge_base = KnowledgeBase(_KNOWLEDGE_DIR)
_prompt_builder = PromptBuilder(_knowledge_base)
_claude = ClaudeService(api_key=os.environ["ANTHROPIC_API_KEY"])

# ElevenLabs TTS — optional (voice features disabled if key not set)
_elevenlabs_key = os.environ.get("ELEVENLABS_API_KEY", "")
_tts: ElevenLabsTTS | None = ElevenLabsTTS(api_key=_elevenlabs_key) if _elevenlabs_key else None

# Memory — Supabase optional, in-memory always available
_supabase_client = None
_supabase_url = os.environ.get("SUPABASE_URL", "")
_supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
if _supabase_url and _supabase_key:
    try:
        from supabase import create_client
        _supabase_client = create_client(_supabase_url, _supabase_key)
        logger.info("Supabase connected — persistent memory enabled")
    except Exception as exc:
        logger.warning("Supabase init failed: %s — using in-memory only", exc)

_memory = MemoryManager(supabase_client=_supabase_client)

# ---------------------------------------------------------------------------
# App & middleware
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Hofmann Agent",
    description="9D Psychedelic Consciousness Agent",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_PUBLIC_DIR = Path(__file__).parent / "public"


# ---------------------------------------------------------------------------
# Root route serves index.html
# ---------------------------------------------------------------------------

@app.get("/")
async def serve_root():
    from fastapi.responses import HTMLResponse
    index_file = _PUBLIC_DIR / "index.html"
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))


if _PUBLIC_DIR.exists():
    app.mount("/public", StaticFiles(directory=str(_PUBLIC_DIR)), name="public")

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str
    dimensions: list[int] = [1]
    dose: str = "common"
    session_id: str | None = None
    language: str = "nl"


class ChatResponse(BaseModel):
    response: str
    dimensions_active: list[int]
    session_id: str


class AnalyzeRequest(BaseModel):
    topic: str
    depth: str = "common"
    dimensions: list[int] = []


class AnalyzeResponse(BaseModel):
    analysis: str
    dimensions_used: list[int]
    interference_patterns: list[str]


class VoiceChatRequest(BaseModel):
    message: str
    dimensions: list[int] = [1]
    dose: str = "common"
    session_id: str | None = None
    language: str = "nl"


class VoiceChatResponse(BaseModel):
    text_response: str
    audio_available: bool
    session_id: str


class DimensionInfo(BaseModel):
    id: int
    name: str
    description: str
    substance: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health() -> dict:
    """Basic liveness check."""
    return {
        "status": "ok",
        "version": "2.0.0",
        "features": {
            "chat": True,
            "voice": _tts is not None,
            "tts": _tts is not None,
            "memory": _memory.layers,
        },
    }


@app.get("/api/dimensions", response_model=list[DimensionInfo])
async def get_dimensions() -> list[DimensionInfo]:
    """Return metadata for all 9 consciousness dimensions."""
    raw = _knowledge_base.get_dimensions()
    return [DimensionInfo(**d) for d in raw]


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """Single-turn or multi-turn text chat with the 9D agent.

    Pass a ``session_id`` from a previous response to continue a conversation.
    Omit it (or pass ``null``) to start a fresh session.
    """
    _validate_dimensions(req.dimensions)

    session_id = req.session_id or str(uuid.uuid4())
    history = await _memory.get_context(session_id)

    # Enrich prompt with learned insights
    learned_context = await _memory.get_dimension_context(req.dimensions)
    system_prompt = _prompt_builder.build_system_prompt(
        dimensions=req.dimensions,
        dose=req.dose,
        language=req.language,
    )
    if learned_context:
        system_prompt += f"\n\n## Learned Context\n{learned_context}"

    try:
        response_text = await _claude.analyze(
            message=req.message,
            system_prompt=system_prompt,
            conversation_history=history,
        )
    except ClaudeServiceError as exc:
        logger.error("Claude error during chat: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Upstream AI service unavailable. Try again shortly.",
        ) from exc

    # Save to all memory layers
    await _memory.save(session_id, "user", req.message, req.dimensions, req.dose, req.language, "text")
    await _memory.save(session_id, "assistant", response_text, req.dimensions, req.dose, req.language, "text")
    await _memory.learn_from_exchange(session_id, req.message, response_text, req.dimensions, req.dose)
    await _memory.persistent.update_session(
        session_id, req.dimensions, req.dose, req.language,
        len(_memory.conversation.get(session_id)),
    )

    return ChatResponse(
        response=response_text,
        dimensions_active=req.dimensions,
        session_id=session_id,
    )


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    """Deep 9D analysis of any topic.

    When ``dimensions`` is empty, all 9 dimensions are activated (full spectrum).
    """
    dimensions = req.dimensions if req.dimensions else list(range(1, 10))
    _validate_dimensions(dimensions)

    system_prompt = _prompt_builder.build_system_prompt(
        dimensions=dimensions,
        dose=req.depth,
        language="en",
        mode="text",
    )

    prompt = (
        f"[9D:FULL_SPECTRUM @{req.depth}] "
        f"Perform a complete multi-dimensional analysis of the following topic:\n\n"
        f"{req.topic}"
    )

    try:
        raw_analysis = await _claude.analyze(
            message=prompt,
            system_prompt=system_prompt,
        )
    except ClaudeServiceError as exc:
        logger.error("Claude error during analysis: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Upstream AI service unavailable. Try again shortly.",
        ) from exc

    interference_patterns = _extract_interference_patterns(raw_analysis)

    return AnalyzeResponse(
        analysis=raw_analysis,
        dimensions_used=dimensions,
        interference_patterns=interference_patterns,
    )


# ---------------------------------------------------------------------------
# Voice endpoints
# ---------------------------------------------------------------------------


@app.post("/api/voice/chat", response_model=VoiceChatResponse)
async def voice_chat(req: VoiceChatRequest) -> VoiceChatResponse:
    """Voice-optimized chat — generates short response + TTS audio."""
    _validate_dimensions(req.dimensions)

    session_id = req.session_id or str(uuid.uuid4())
    history = await _memory.get_context(session_id)

    system_prompt = _prompt_builder.build_system_prompt(
        dimensions=req.dimensions,
        dose=req.dose,
        language=req.language,
        mode="voice",
    )

    try:
        response_text = await _claude.analyze(
            message=req.message,
            system_prompt=system_prompt,
            conversation_history=history,
            max_tokens=500,
        )
    except ClaudeServiceError as exc:
        logger.error("Claude error during voice chat: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Upstream AI service unavailable.",
        ) from exc

    # Save to all memory layers
    await _memory.save(session_id, "user", req.message, req.dimensions, req.dose, req.language, "voice")
    await _memory.save(session_id, "assistant", response_text, req.dimensions, req.dose, req.language, "voice")
    await _memory.learn_from_exchange(session_id, req.message, response_text, req.dimensions, req.dose)
    await _memory.persistent.update_session(
        session_id, req.dimensions, req.dose, req.language,
        len(_memory.conversation.get(session_id)),
    )

    return VoiceChatResponse(
        text_response=response_text,
        audio_available=_tts is not None,
        session_id=session_id,
    )


class TTSRequest(BaseModel):
    text: str


@app.post("/api/voice/tts")
async def text_to_speech(req: TTSRequest):
    """Convert text to speech audio via ElevenLabs.

    Returns MP3 audio bytes.
    """
    from fastapi.responses import Response

    if not _tts:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ElevenLabs TTS not configured. Set ELEVENLABS_API_KEY.",
        )
    if not req.text.strip():
        raise HTTPException(status_code=422, detail="No text provided.")

    try:
        audio_bytes = await _tts.text_to_speech(req.text)
    except ElevenLabsTTSError as exc:
        logger.error("TTS error: %s", exc)
        raise HTTPException(status_code=502, detail="TTS conversion failed.") from exc

    return Response(content=audio_bytes, media_type="audio/mpeg")


# ---------------------------------------------------------------------------
# WebSocket — streaming chat
# ---------------------------------------------------------------------------


@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket) -> None:
    """Stream chat responses token by token.

    Client sends a JSON object:
    ``{"message": str, "dimensions": list[int], "dose": str, "language": str}``

    Server emits JSON frames:
    - ``{"type": "token", "content": "<delta>"}`` — text as it streams
    - ``{"type": "done", "content": ""}`` — signals end of response
    - ``{"type": "error", "content": "<message>"}`` — on failure
    - ``{"type": "dimension_shift", "content": "<dim_label>"}`` — emitted once
      before streaming begins to announce which dimensions are active
    """
    await websocket.accept()

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await _ws_send(websocket, "error", "Invalid JSON payload")
                continue

            message: str = payload.get("message", "")
            dimensions: list[int] = payload.get("dimensions", [1])
            dose: str = payload.get("dose", "common")
            language: str = payload.get("language", "nl")

            if not message:
                await _ws_send(websocket, "error", "Empty message")
                continue

            try:
                _validate_dimensions(dimensions)
            except HTTPException as exc:
                await _ws_send(websocket, "error", exc.detail)
                continue

            system_prompt = _prompt_builder.build_system_prompt(
                dimensions=dimensions,
                dose=dose,
                language=language,
            )

            # Announce which dimensions are active before streaming
            dim_label = "+".join(f"D{d}" for d in dimensions)
            await _ws_send(websocket, "dimension_shift", dim_label)

            try:
                async for token in _claude.stream_analyze(
                    message=message,
                    system_prompt=system_prompt,
                ):
                    await _ws_send(websocket, "token", token)
            except ClaudeServiceError as exc:
                logger.error("Stream error: %s", exc)
                await _ws_send(websocket, "error", "AI service error — reconnect and retry")
                continue

            await _ws_send(websocket, "done", "")

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate_dimensions(dimensions: list[int]) -> None:
    """Raise 422 if any dimension number is outside the valid 1-9 range."""
    if not dimensions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one dimension must be specified.",
        )
    invalid = [d for d in dimensions if d < 1 or d > 9]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Dimension values must be between 1 and 9. Invalid: {invalid}",
        )


def _extract_interference_patterns(text: str) -> list[str]:
    """Best-effort extraction of interference patterns from a 9D analysis.

    Looks for the canonical ``## Interference Field`` section produced by the
    9D output protocol. Falls back to an empty list when the section is absent.
    """
    lines = text.splitlines()
    patterns: list[str] = []
    in_section = False

    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("## interference"):
            in_section = True
            continue
        if in_section:
            if stripped.startswith("## "):
                break
            if stripped:
                patterns.append(stripped.lstrip("-–• "))

    return patterns


async def _ws_send(websocket: WebSocket, msg_type: str, content: str) -> None:
    """Serialize and send a typed message frame over a WebSocket."""
    await websocket.send_text(json.dumps({"type": msg_type, "content": content}))
