"""Habit check-in log.

One row per (user, habit, calendar date).
The UNIQUE constraint prevents duplicate check-ins for the same day.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Text, Boolean, Float, DateTime,
    ForeignKey, UniqueConstraint,
)

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class HabitLog(Base):
    """Records whether a user completed a scheduled habit on a given date."""

    __tablename__ = "habit_logs"

    id       = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id  = Column(String(36), ForeignKey("users.id",        ondelete="CASCADE"), nullable=False, index=True)
    habit_id = Column(String(36), ForeignKey("user_habits.id",  ondelete="CASCADE"), nullable=False)

    # "YYYY-MM-DD" string — works identically on SQLite and Postgres,
    # sorts correctly as a string, and avoids date-type dialect differences.
    date = Column(String(10), nullable=False)

    completed     = Column(Boolean, nullable=False, default=False)
    note          = Column(Text,    nullable=True)
    # Reserved for future numeric/duration tracking types (Phase 5).
    value_numeric = Column(Float,   nullable=True)

    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "habit_id", "date", name="uq_habit_log_user_habit_date"),
    )
