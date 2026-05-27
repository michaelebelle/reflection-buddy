"""Onboarding CRUD and LLM context formatting.

The ``build_llm_context`` function is the key export — it converts a user's
onboarding data into a structured text block that can be prepended to any LLM
call to personalise reflection questions, trend summaries, and memory retrieval.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.onboarding import UserOnboarding, UserGoal, UserStressor, UserHabit
from app.schemas.onboarding import OnboardingCreate, OnboardingPatch, OnboardingResponse, BaselineRatings


# ── Read ───────────────────────────────────────────────────────────────────

def get_onboarding(db: Session, user_id: str) -> OnboardingResponse | None:
    """Return all onboarding data for the user, or None if not yet completed."""
    meta = db.query(UserOnboarding).filter(UserOnboarding.user_id == user_id).first()
    if not meta:
        return None

    goals     = db.query(UserGoal).filter(UserGoal.user_id == user_id).all()
    stressors = db.query(UserStressor).filter(UserStressor.user_id == user_id).all()
    habits    = db.query(UserHabit).filter(UserHabit.user_id == user_id).all()

    return OnboardingResponse(
        goals=goals,
        stressors=stressors,
        habits=habits,
        baseline_ratings=BaselineRatings(
            mood_baseline=meta.mood_baseline,
            energy_baseline=meta.energy_baseline,
            stress_baseline=meta.stress_baseline,
            confidence_baseline=meta.confidence_baseline,
            discipline_baseline=meta.discipline_baseline,
            life_satisfaction_baseline=meta.life_satisfaction_baseline,
        ),
        completed_at=meta.completed_at,
    )


# ── Write ──────────────────────────────────────────────────────────────────

def save_onboarding(db: Session, user_id: str, data: OnboardingCreate) -> OnboardingResponse:
    """Create or fully replace a user's onboarding data.

    Deletes all existing goals/stressors/habits for the user before inserting
    the new set — this keeps POST idempotent for re-submissions.
    """
    _clear_all(db, user_id)

    # Goals
    for g in data.goals:
        db.add(UserGoal(user_id=user_id, **g.model_dump()))

    # Stressors
    for s in data.stressors:
        db.add(UserStressor(user_id=user_id, **s.model_dump()))

    # Habits
    for h in data.habits:
        db.add(UserHabit(user_id=user_id, **h.model_dump()))

    # Baseline ratings (upsert on the meta row)
    meta = db.query(UserOnboarding).filter(UserOnboarding.user_id == user_id).first()
    ratings = data.baseline_ratings
    if meta:
        for field, value in ratings.model_dump().items():
            setattr(meta, field, value)
    else:
        meta = UserOnboarding(user_id=user_id, **ratings.model_dump())
        db.add(meta)

    db.commit()
    return get_onboarding(db, user_id)


def patch_onboarding(db: Session, user_id: str, data: OnboardingPatch) -> OnboardingResponse | None:
    """Partially update onboarding — only replaces the sections that are provided."""
    meta = db.query(UserOnboarding).filter(UserOnboarding.user_id == user_id).first()
    if not meta:
        return None  # Must POST first

    if data.goals is not None:
        db.query(UserGoal).filter(UserGoal.user_id == user_id).delete()
        for g in data.goals:
            db.add(UserGoal(user_id=user_id, **g.model_dump()))

    if data.stressors is not None:
        db.query(UserStressor).filter(UserStressor.user_id == user_id).delete()
        for s in data.stressors:
            db.add(UserStressor(user_id=user_id, **s.model_dump()))

    if data.habits is not None:
        db.query(UserHabit).filter(UserHabit.user_id == user_id).delete()
        for h in data.habits:
            db.add(UserHabit(user_id=user_id, **h.model_dump()))

    if data.baseline_ratings is not None:
        for field, value in data.baseline_ratings.model_dump().items():
            setattr(meta, field, value)

    db.commit()
    return get_onboarding(db, user_id)


# ── LLM context formatter ──────────────────────────────────────────────────

def build_llm_context(db: Session, user_id: str) -> str:
    """Format onboarding data into a structured text block for LLM injection.

    Returns an empty string if the user hasn't completed onboarding — callers
    should handle this gracefully (just omit the context block from the prompt).

    Example output:
        User Goals:
        - Career: Get an AI engineering job. Success means interview-ready and
          applying consistently. Target: 3 months.

        Current Stressors:
        - Work stress (intensity 8/10, daily): Feeling stuck and overextended.

        Tracked Habits:
        - deep_work — positive, target 5x/week (boolean)

        Baseline Ratings:
        - Mood: 6/10 | Energy: 5/10 | Stress: 7/10
        - Confidence: 6/10 | Discipline: 5/10 | Life Satisfaction: 6/10
    """
    data = get_onboarding(db, user_id)
    if not data:
        return ""

    lines: list[str] = []

    # Goals
    if data.goals:
        lines.append("User Goals:")
        for g in data.goals:
            tf = g.target_timeframe.replace("_", " ")
            lines.append(
                f"- {g.category.title()}: {g.title}. "
                f"Success means {g.success_definition.rstrip('.')}. "
                f"Target: {tf}."
            )
        lines.append("")

    # Stressors
    if data.stressors:
        lines.append("Current Stressors:")
        for s in data.stressors:
            freq = s.frequency.replace("_", " ")
            lines.append(
                f"- {s.category.title()} stress "
                f"(intensity {s.intensity}/10, {freq}): "
                f"{s.description.rstrip('.')}."
            )
        lines.append("")

    # Habits
    if data.habits:
        lines.append("Tracked Habits:")
        for h in data.habits:
            freq = h.desired_frequency.replace("_", " ")
            lines.append(
                f"- {h.name} — {h.positive_or_negative}, "
                f"target {freq} ({h.tracking_type})"
            )
        lines.append("")

    # Baseline ratings
    if data.baseline_ratings:
        r = data.baseline_ratings
        lines.append("Baseline Ratings:")
        lines.append(
            f"- Mood: {r.mood_baseline}/10 | "
            f"Energy: {r.energy_baseline}/10 | "
            f"Stress: {r.stress_baseline}/10"
        )
        lines.append(
            f"- Confidence: {r.confidence_baseline}/10 | "
            f"Discipline: {r.discipline_baseline}/10 | "
            f"Life Satisfaction: {r.life_satisfaction_baseline}/10"
        )

    return "\n".join(lines)
