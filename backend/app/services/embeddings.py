"""Embedding generation service using OpenAI's text-embedding-3-small model.

Usage
-----
    from app.services.embeddings import embedding_service

    vector = embedding_service.generate("I felt really overwhelmed at work today")
    # → list[float] of length 1536, or None if API key not set / call fails

The embedding column in Postgres is a native pgvector `vector(1536)` type,
managed via raw SQL in main.py's migration runner.  This service is
intentionally database-agnostic — it only produces vectors; storing and
searching them is handled in the journal service.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.config import settings

if TYPE_CHECKING:
    from app.models.journal import JournalEntry

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate float vectors from journal entry text.

    ── Configuration ──────────────────────────────────────────────────────────
    Edit these class-level constants to tune behavior.
    """

    # OpenAI embedding model.
    # text-embedding-3-small: 1536 dimensions, $0.02/1M tokens — ideal here.
    # text-embedding-3-large: 3072 dimensions, $0.13/1M tokens — higher quality.
    MODEL: str = "text-embedding-3-small"

    # Must match the model's output size.  Update both if you change MODEL.
    DIMENSIONS: int = 1536

    # Safety truncation — entries are rarely this long, but avoids API errors.
    MAX_INPUT_CHARS: int = 8_000

    # ── Public API ─────────────────────────────────────────────────────────

    def generate(self, text: str) -> list[float] | None:
        """Return a float vector for the given text, or None on any failure.

        Callers treat None as "embedding unavailable" — the entry still saves,
        it just won't appear in semantic search results until re-embedded.
        """
        if not settings.openai_api_key:
            logger.debug("OPENAI_API_KEY not set — skipping embedding generation")
            return None

        if not text or not text.strip():
            return None

        try:
            return self._generate_raw(text[: self.MAX_INPUT_CHARS])
        except Exception:
            logger.exception("Embedding generation failed for text starting: %r", text[:80])
            return None

    def build_entry_text(self, entry: "JournalEntry") -> str:
        """Concatenate all meaningful text fields from an entry for embedding.

        Combining fields gives the model richer context than embedding the
        main content alone — mood vocabulary and reflection answers shift the
        semantic meaning in useful ways.
        """
        parts: list[str] = []

        if entry.mood:
            parts.append(f"Mood: {entry.mood}")
        if entry.content and entry.content.strip():
            parts.append(entry.content.strip())
        for field in ("q_what_happened", "q_how_felt", "q_learned", "q_improve_tomorrow"):
            val = getattr(entry, field, None)
            if val and val.strip():
                parts.append(val.strip())

        return "\n".join(parts)

    def format_for_sql(self, vector: list[float]) -> str:
        """Serialise a float list to pgvector's literal format: '[0.1,0.2,...]'.

        Postgres accepts this string and casts it to vector(1536) automatically.
        """
        return "[" + ",".join(f"{x:.8f}" for x in vector) + "]"

    # ── Private ────────────────────────────────────────────────────────────

    def _generate_raw(self, text: str) -> list[float]:
        """Call the OpenAI embeddings API.

        Override this method to swap embedding providers — everything else
        (build_entry_text, format_for_sql, error handling) stays the same.
        """
        from openai import OpenAI  # deferred import — only needed when key is set

        client = OpenAI(api_key=settings.openai_api_key)
        response = client.embeddings.create(
            model=self.MODEL,
            input=text,
            dimensions=self.DIMENSIONS,
        )
        return response.data[0].embedding


# Module-level singleton
embedding_service = EmbeddingService()
