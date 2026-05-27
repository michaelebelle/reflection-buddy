"""Onboarding data models — goals, stressors, habits, and baseline ratings.

All four tables are keyed by user_id and designed so individual rows can be
queried for trend analysis and injected into LLM context blocks.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserOnboarding(Base):
    """Baseline self-ratings and completion flag.  One row per user."""

    __tablename__ = "user_onboarding"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # 1–10 baseline ratings — anchors for future trend analysis
    mood_baseline             = Column(Integer, nullable=False)
    energy_baseline           = Column(Integer, nullable=False)
    stress_baseline           = Column(Integer, nullable=False)
    confidence_baseline       = Column(Integer, nullable=False)
    discipline_baseline       = Column(Integer, nullable=False)
    life_satisfaction_baseline = Column(Integer, nullable=False)

    completed_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at   = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)


class UserGoal(Base):
    """Active goals — up to 3 per user.  Compared against journal entries by AI."""

    __tablename__ = "user_goals"

    id         = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id    = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category   = Column(String(50),  nullable=False)   # career | fitness | relationships | …
    title      = Column(String(200), nullable=False)
    why_it_matters     = Column(Text, nullable=False)
    success_definition = Column(Text, nullable=False)
    target_timeframe   = Column(String(50), nullable=False)  # 1_month | 3_months | …
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


class UserStressor(Base):
    """Current stressors — up to 5 per user.  Used to surface recurring patterns."""

    __tablename__ = "user_stressors"

    id          = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id     = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category    = Column(String(50), nullable=False)   # work | school | relationships | …
    description = Column(Text,       nullable=False)
    intensity   = Column(Integer,    nullable=False)   # 1–10
    frequency   = Column(String(50), nullable=False)   # daily | several_times_per_week | …
    created_at  = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


class UserHabit(Base):
    """Habits to track — 3–8 per user.  Used for streaks, correlations, AI insights."""

    __tablename__ = "user_habits"

    id                   = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id              = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name                 = Column(String(100), nullable=False)
    desired_frequency    = Column(String(50),  nullable=False)  # daily | 3x_per_week | …
    positive_or_negative = Column(String(20),  nullable=False)  # positive | negative
    tracking_type        = Column(String(20),  nullable=False)  # boolean | numeric | duration | text
    created_at           = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
