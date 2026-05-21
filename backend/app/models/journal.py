import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, Integer, Float, DateTime

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    # Core entry
    content = Column(Text, nullable=False)
    mood = Column(String(50), nullable=True)       # e.g. "happy", "calm", "anxious"
    energy_level = Column(Integer, nullable=True)  # 1–10

    # Reflection questions (stored as separate columns for easy querying)
    q_what_happened = Column(Text, nullable=True)
    q_how_felt = Column(Text, nullable=True)
    q_learned = Column(Text, nullable=True)
    q_improve_tomorrow = Column(Text, nullable=True)

    # Audit trail — who created / last updated this entry.
    # Populated from settings.journal_owner; swap for a real user ID once auth lands.
    created_by = Column(String(100), nullable=True)
    updated_by = Column(String(100), nullable=True)

    # ── Future AI fields ───────────────────────────────────────────────────
    # Uncomment each column as the corresponding AI feature is built.
    # Keeping them here as a roadmap makes migrations straightforward.
    #
    # embedding = Column(Text, nullable=True)          # JSON float list (vector)
    # sentiment_score = Column(Float, nullable=True)   # –1.0 (negative) → 1.0 (positive)
    # ai_summary = Column(Text, nullable=True)         # LLM-generated summary
    # themes = Column(Text, nullable=True)             # JSON string list (detected themes)
    # generated_prompts = Column(Text, nullable=True)  # JSON string list (AI follow-up prompts)
