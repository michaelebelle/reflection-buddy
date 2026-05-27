"""AI-powered reflection prompt generation using the Anthropic API.

Usage
-----
    from app.services.ai_prompts import ReflectionPromptGenerator

    generator = ReflectionPromptGenerator()
    questions = generator.generate(recent_entries, current_mood="anxious")
    # → ["What specific...", "How did you...", ...]

The class is designed to be easy to tune:

  • Edit the constants at the top of the class to change model, how many
    entries are fed as context, how many questions are generated, etc.

  • Override ``_generate_raw`` to swap in a different LLM provider without
    touching any other logic.

  • The ``generate`` method returns gracefully (falls back to DEFAULT_PROMPTS)
    whenever the API key isn't set or the API call fails — the rest of the
    app keeps working even if AI is unavailable.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

from app.config import settings

if TYPE_CHECKING:
    # Avoid a hard import at module level so the app starts fine when
    # `anthropic` isn't installed (e.g. during a fresh local setup).
    from app.models.journal import JournalEntry

logger = logging.getLogger(__name__)

# ── Fallback prompts (used when AI is unavailable) ──────────────────────────
# These are the same defaults already in journal.py — kept here too so this
# module is self-contained and can be tested independently.
_DEFAULT_PROMPTS = [
    "What happened today that you want to remember?",
    "How are you feeling, and what's driving that feeling?",
    "What's one thing you learned or noticed about yourself?",
    "What do you want to do differently tomorrow?",
]


class ReflectionPromptGenerator:
    """Generate personalised reflection questions for a user's journal entry.

    ── Configuration ──────────────────────────────────────────────────────────
    Edit these class-level constants to tune behavior without touching the
    logic below.
    """

    # The Anthropic model to use.
    # claude-haiku-4-5  → cheapest/fastest, great for question generation
    # claude-sonnet-4-6 → better nuance, ~15x more expensive
    # claude-opus-4-7   → most capable, ~25x more expensive (overkill here)
    MODEL: str = "claude-haiku-4-5"

    # How many of the user's most recent journal entries to feed as context.
    # More entries → richer questions, but higher token cost.
    MAX_CONTEXT_ENTRIES: int = 5

    # Exactly how many reflection questions to generate per call.
    QUESTION_COUNT: int = 4

    # The system prompt shapes Claude's persona and output format.
    # Keep the JSON instruction — the parser below depends on it.
    SYSTEM_PROMPT: str = """You are a thoughtful, empathetic journaling coach. \
Your job is to generate personalised reflection questions that help people \
develop genuine self-awareness and grow from their experiences.

Guidelines:
- Ask questions that are open-ended and introspective, not yes/no
- Build on specific details the user mentioned — never ask generic questions
- Match the emotional tone of their entries: be gentle when they're struggling,
  curious when they're exploring, celebratory when they're thriving
- Focus on patterns across multiple entries when you can spot them
- Avoid clichés like "how did that make you feel?" — go deeper
- Keep each question to one sentence

Respond with ONLY a valid JSON array of exactly {count} strings, like:
["Question 1?", "Question 2?", "Question 3?", "Question 4?"]

No extra text, no markdown — just the JSON array."""

    # Temperature for generation (0.0 = deterministic, 1.0 = most creative).
    # 0.8 gives varied questions without going off-the-rails.
    TEMPERATURE: float = 0.8

    # Hard cap on output tokens. 4 questions rarely need more than 300 tokens.
    MAX_TOKENS: int = 500

    # ── Implementation ─────────────────────────────────────────────────────

    def generate(
        self,
        recent_entries: list["JournalEntry"],
        current_mood: str | None = None,
    ) -> list[str]:
        """Return ``QUESTION_COUNT`` reflection questions for the user.

        Falls back to ``_DEFAULT_PROMPTS`` if:
          - ``ANTHROPIC_API_KEY`` is not set
          - The API call raises any exception
          - Claude's response can't be parsed

        Parameters
        ----------
        recent_entries:
            The user's most recent journal entries (pre-filtered to
            ``MAX_CONTEXT_ENTRIES`` by the caller, or this method slices them).
        current_mood:
            Optional mood string (e.g. "anxious") for additional context.
        """
        if not settings.anthropic_api_key:
            logger.debug("ANTHROPIC_API_KEY not set — using default prompts")
            return _DEFAULT_PROMPTS[: self.QUESTION_COUNT]

        entries = recent_entries[: self.MAX_CONTEXT_ENTRIES]

        try:
            user_message = self._build_user_message(entries, current_mood)
            raw = self._generate_raw(user_message)
            questions = self._parse_questions(raw)
            if questions:
                return questions
            logger.warning("AI returned no parseable questions — using defaults")
        except Exception:
            logger.exception("AI prompt generation failed — using defaults")

        return _DEFAULT_PROMPTS[: self.QUESTION_COUNT]

    # ── Private helpers ────────────────────────────────────────────────────

    def _build_user_message(
        self,
        entries: list["JournalEntry"],
        mood: str | None,
    ) -> str:
        """Assemble the user-turn text sent to Claude."""
        parts: list[str] = []

        if mood:
            parts.append(f"Current mood: {mood}\n")

        if not entries:
            parts.append(
                "This is my first journal entry — I haven't written anything yet."
            )
        else:
            parts.append(
                f"Here are my {len(entries)} most recent journal "
                f"{'entry' if len(entries) == 1 else 'entries'}:\n"
            )
            for i, entry in enumerate(entries, 1):
                parts.append(f"--- Entry {i} ---")
                if entry.mood:
                    parts.append(f"Mood: {entry.mood}")
                if entry.title:
                    parts.append(f"Title: {entry.title}")

                # Include whichever text fields exist (some may be None)
                field_labels = [
                    ("q_what_happened",   "What happened"),
                    ("q_how_felt",        "How I felt"),
                    ("q_learned",         "What I learned"),
                    ("q_improve_tomorrow","Tomorrow"),
                    ("content",           "Notes"),
                ]
                for attr, label in field_labels:
                    val = getattr(entry, attr, None)
                    if val and val.strip():
                        parts.append(f"{label}: {val.strip()}")

                parts.append("")  # blank line between entries

        parts.append(
            f"\nPlease generate {self.QUESTION_COUNT} reflection questions "
            "that will help me think more deeply about my experiences."
        )
        return "\n".join(parts)

    def _generate_raw(self, user_message: str) -> str:
        """Call the Anthropic API and return the raw text response.

        Override this method to swap in a different LLM provider — everything
        else (prompt building, parsing, fallback) stays the same.
        """
        import anthropic  # deferred import — only needed when key is present

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        system = self.SYSTEM_PROMPT.format(count=self.QUESTION_COUNT)

        message = client.messages.create(
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )

        # Extract the text block (there may also be a thinking block)
        for block in message.content:
            if block.type == "text":
                return block.text

        return ""

    def _parse_questions(self, raw: str) -> list[str]:
        """Extract a list of question strings from Claude's JSON response.

        Returns an empty list if parsing fails so the caller can fall back
        gracefully.
        """
        if not raw:
            return []

        # Try the whole response first
        try:
            data = json.loads(raw.strip())
            if isinstance(data, list):
                return [str(q).strip() for q in data if str(q).strip()]
        except json.JSONDecodeError:
            pass

        # Claude sometimes wraps JSON in a markdown code block — strip it
        match = re.search(r"\[.*?\]", raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                if isinstance(data, list):
                    return [str(q).strip() for q in data if str(q).strip()]
            except json.JSONDecodeError:
                pass

        logger.warning("Could not parse AI response as JSON: %r", raw[:200])
        return []


# Module-level singleton — import and call directly from journal.py
prompt_generator = ReflectionPromptGenerator()
