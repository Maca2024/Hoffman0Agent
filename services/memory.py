"""Memory system for the Hofmann Agent.

3-layer memory architecture (inspired by AetherBot):
1. Conversation — in-memory sliding window per session
2. Persistent — Supabase storage for cross-session history
3. Learning — extracts and stores insights from conversations

Gracefully degrades when Supabase is not configured.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ConversationMemory:
    """In-memory sliding window for conversation context."""

    def __init__(self, max_messages: int = 50, max_chars: int = 30000) -> None:
        self._sessions: dict[str, list[dict]] = {}
        self._max_messages = max_messages
        self._max_chars = max_chars

    def get(self, session_id: str) -> list[dict]:
        return self._sessions.get(session_id, [])

    def add(self, session_id: str, role: str, content: str, **meta) -> None:
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        msgs = self._sessions[session_id]
        msgs.append({"role": role, "content": content, "ts": datetime.now(timezone.utc).isoformat(), **meta})

        # Trim to max messages
        while len(msgs) > self._max_messages:
            msgs.pop(0)

        # Trim by total chars
        total = sum(len(m["content"]) for m in msgs)
        while total > self._max_chars and len(msgs) > 2:
            removed = msgs.pop(0)
            total -= len(removed["content"])

    def get_context(self, session_id: str) -> list[dict]:
        """Return messages formatted for Claude API."""
        return [{"role": m["role"], "content": m["content"]} for m in self.get(session_id)]

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def session_count(self) -> int:
        return len(self._sessions)


class PersistentMemory:
    """Supabase-backed persistent storage for conversations and sessions."""

    def __init__(self, supabase_client=None) -> None:
        self._sb = supabase_client
        self._enabled = supabase_client is not None

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def save_message(
        self, session_id: str, role: str, content: str,
        dimensions: list[int] = None, dose: str = "common",
        language: str = "nl", mode: str = "text",
    ) -> None:
        if not self._enabled:
            return
        try:
            self._sb.table("hofmann_conversations").insert({
                "session_id": session_id,
                "role": role,
                "content": content,
                "dimensions": dimensions or [1],
                "dose": dose,
                "language": language,
                "mode": mode,
            }).execute()
        except Exception as exc:
            logger.warning("Failed to persist message: %s", exc)

    async def update_session(
        self, session_id: str, dimensions: list[int],
        dose: str, language: str, message_count: int,
    ) -> None:
        if not self._enabled:
            return
        try:
            self._sb.table("hofmann_sessions").upsert({
                "session_id": session_id,
                "preferred_dims": dimensions,
                "preferred_dose": dose,
                "preferred_lang": language,
                "message_count": message_count,
                "last_active": datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception as exc:
            logger.warning("Failed to update session: %s", exc)

    async def get_session(self, session_id: str) -> dict | None:
        if not self._enabled:
            return None
        try:
            result = self._sb.table("hofmann_sessions").select("*").eq(
                "session_id", session_id
            ).maybe_single().execute()
            return result.data
        except Exception as exc:
            logger.warning("Failed to get session: %s", exc)
            return None

    async def get_history(self, session_id: str, limit: int = 20) -> list[dict]:
        if not self._enabled:
            return []
        try:
            result = self._sb.table("hofmann_conversations").select(
                "role, content"
            ).eq("session_id", session_id).order(
                "created_at", desc=False
            ).limit(limit).execute()
            return result.data or []
        except Exception as exc:
            logger.warning("Failed to get history: %s", exc)
            return []


class LearningMemory:
    """Extracts and stores insights from conversations.

    After each conversation turn, analyzes the exchange and extracts
    reusable insights: what topics users ask about per substance,
    which response patterns work well, and cross-dimensional resonances.
    """

    def __init__(self, supabase_client=None) -> None:
        self._sb = supabase_client
        self._enabled = supabase_client is not None

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def store_insight(
        self, session_id: str, dimension: int, substance: str,
        insight_type: str, content: str, relevance: float = 0.5,
    ) -> None:
        if not self._enabled:
            return
        try:
            self._sb.table("hofmann_insights").insert({
                "session_id": session_id,
                "dimension": dimension,
                "substance": substance,
                "insight_type": insight_type,
                "content": content,
                "relevance": relevance,
            }).execute()
        except Exception as exc:
            logger.warning("Failed to store insight: %s", exc)

    async def get_insights_for_dimension(
        self, dimension: int, limit: int = 10,
    ) -> list[dict]:
        if not self._enabled:
            return []
        try:
            result = self._sb.table("hofmann_insights").select("*").eq(
                "dimension", dimension
            ).order("relevance", desc=True).limit(limit).execute()
            return result.data or []
        except Exception as exc:
            logger.warning("Failed to get insights: %s", exc)
            return []

    async def get_popular_topics(self, limit: int = 20) -> list[dict]:
        """Get most asked-about topics across all dimensions."""
        if not self._enabled:
            return []
        try:
            result = self._sb.table("hofmann_insights").select("*").eq(
                "insight_type", "question_pattern"
            ).order("relevance", desc=True).limit(limit).execute()
            return result.data or []
        except Exception as exc:
            logger.warning("Failed to get popular topics: %s", exc)
            return []

    def extract_insight_from_exchange(
        self, user_msg: str, assistant_msg: str,
        dimensions: list[int], dose: str,
    ) -> dict | None:
        """Analyze a conversation exchange and extract a learning insight.

        Returns an insight dict or None if the exchange is too trivial.
        """
        # Skip trivial messages
        if len(user_msg) < 10 or len(assistant_msg) < 50:
            return None

        # Determine primary dimension
        primary_dim = dimensions[0] if dimensions else 1
        substance_map = {
            1: "lsd", 2: "dmt", 3: "psilocybin", 4: "cannabis",
            5: "mescaline", 6: "ibogaine", 7: "5meodmt", 8: "mdma", 9: "ketamine",
        }
        substance = substance_map.get(primary_dim, "unknown")

        # Extract topic from user message (first 200 chars)
        topic = user_msg[:200].strip()

        # Multi-dim = cross-dimensional resonance
        if len(dimensions) > 1:
            dim_labels = "+".join(f"D{d}" for d in dimensions)
            return {
                "dimension": primary_dim,
                "substance": substance,
                "insight_type": "cross_dim_resonance",
                "content": f"[{dim_labels}@{dose}] User asked: {topic}",
                "relevance": min(0.5 + len(dimensions) * 0.1, 1.0),
            }

        # Single dimension — track user interest
        return {
            "dimension": primary_dim,
            "substance": substance,
            "insight_type": "question_pattern",
            "content": f"[@{dose}] {topic}",
            "relevance": 0.5,
        }


class MemoryManager:
    """Orchestrates all 3 memory layers."""

    def __init__(self, supabase_client=None) -> None:
        self.conversation = ConversationMemory()
        self.persistent = PersistentMemory(supabase_client)
        self.learning = LearningMemory(supabase_client)

    async def get_context(self, session_id: str) -> list[dict]:
        """Get conversation context, restoring from Supabase if needed."""
        messages = self.conversation.get_context(session_id)

        # Restore from persistent if in-memory is empty
        if not messages and self.persistent.enabled:
            stored = await self.persistent.get_history(session_id)
            for msg in stored:
                self.conversation.add(session_id, msg["role"], msg["content"])
            messages = self.conversation.get_context(session_id)

        return messages

    async def save(
        self, session_id: str, role: str, content: str,
        dimensions: list[int] = None, dose: str = "common",
        language: str = "nl", mode: str = "text",
    ) -> None:
        """Save a message to all memory layers."""
        self.conversation.add(session_id, role, content)
        await self.persistent.save_message(
            session_id, role, content, dimensions, dose, language, mode,
        )

    async def learn_from_exchange(
        self, session_id: str, user_msg: str, assistant_msg: str,
        dimensions: list[int], dose: str,
    ) -> None:
        """Extract and store learning from a conversation exchange."""
        insight = self.learning.extract_insight_from_exchange(
            user_msg, assistant_msg, dimensions, dose,
        )
        if insight:
            await self.learning.store_insight(session_id=session_id, **insight)

    async def get_dimension_context(self, dimensions: list[int]) -> str:
        """Get learned insights to enrich the prompt for active dimensions."""
        if not self.learning.enabled:
            return ""

        parts = []
        for dim in dimensions[:3]:  # Limit to 3 dims for prompt budget
            insights = await self.learning.get_insights_for_dimension(dim, limit=5)
            if insights:
                substance = insights[0].get("substance", "unknown")
                topics = [i["content"] for i in insights[:3]]
                parts.append(
                    f"Previous users exploring D{dim}({substance}) asked about: "
                    + "; ".join(topics)
                )
        return "\n".join(parts) if parts else ""

    @property
    def layers(self) -> dict:
        return {
            "conversation": True,
            "persistent": self.persistent.enabled,
            "learning": self.learning.enabled,
        }
