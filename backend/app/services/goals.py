"""Goals CRUD and progress calculation.

Progress is determined by counting completed habit_logs for habits linked to
each goal (via UserHabit.goal_id FK) within the current calendar week.
No LLM calls — all deterministic.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.onboarding import UserGoal, UserHabit
from app.models.checkin import HabitLog
from app.schemas.goals import GoalCreateRequest, GoalUpdateRequest, GoalProgressItem, GoalProgressResponse

logger = logging.getLogger(__name__)


# ── Read ───────────────────────────────────────────────────────────────────

def get_goals(
    db: Session,
    user_id: str,
    status: str | None = None,
) -> list[UserGoal]:
    q = db.query(UserGoal).filter(UserGoal.user_id == user_id)
    if status:
        q = q.filter(UserGoal.status == status)
    else:
        # Default: exclude archived so callers get active + completed
        q = q.filter(UserGoal.status != "archived")
    return q.order_by(UserGoal.created_at.asc()).all()


def get_goal(db: Session, goal_id: str, user_id: str) -> UserGoal | None:
    return (
        db.query(UserGoal)
        .filter(UserGoal.id == goal_id, UserGoal.user_id == user_id)
        .first()
    )


# ── Write ──────────────────────────────────────────────────────────────────

def create_goal(db: Session, user_id: str, data: GoalCreateRequest) -> UserGoal:
    goal = UserGoal(
        user_id            = user_id,
        category           = data.category,
        title              = data.title,
        why_it_matters     = data.why_it_matters,
        success_definition = data.success_definition,
        target_timeframe   = data.target_timeframe,
        status             = "active",
        cadence_per_week   = data.cadence_per_week,
        schedule_days      = data.schedule_days,
        duration_weeks     = data.duration_weeks,
        end_date           = _compute_end_date(data.end_date, data.duration_weeks),
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def update_goal(
    db: Session,
    goal_id: str,
    user_id: str,
    data: GoalUpdateRequest,
) -> UserGoal | None:
    goal = get_goal(db, goal_id, user_id)
    if not goal:
        return None

    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(goal, field, value)

    # Recompute end_date if duration_weeks was updated but end_date was not explicitly set
    if "duration_weeks" in update_fields and "end_date" not in update_fields:
        goal.end_date = _compute_end_date(None, data.duration_weeks)

    db.commit()
    db.refresh(goal)
    return goal


# ── Progress ───────────────────────────────────────────────────────────────

def get_goals_progress(db: Session, user_id: str) -> GoalProgressResponse:
    """Return weekly adherence for all active goals.

    Progress = completed habit_logs for habits linked to each goal within the
    current Mon–Sun week.  Goals without linked habits get 0 completions.
    """
    today      = date.today()
    week_start = today - timedelta(days=today.weekday())    # Monday
    week_end   = week_start + timedelta(days=6)             # Sunday
    week_start_str = week_start.isoformat()
    week_end_str   = week_end.isoformat()

    goals = (
        db.query(UserGoal)
        .filter(UserGoal.user_id == user_id, UserGoal.status == "active")
        .order_by(UserGoal.created_at.asc())
        .all()
    )

    items: list[GoalProgressItem] = []
    for goal in goals:
        habits = (
            db.query(UserHabit)
            .filter(UserHabit.user_id == user_id, UserHabit.goal_id == goal.id)
            .all()
        )
        habit_ids = [h.id for h in habits]

        completed_this_week = 0
        if habit_ids:
            completed_this_week = (
                db.query(HabitLog)
                .filter(
                    HabitLog.user_id   == user_id,
                    HabitLog.habit_id.in_(habit_ids),
                    HabitLog.date      >= week_start_str,
                    HabitLog.date      <= week_end_str,
                    HabitLog.completed == True,
                )
                .count()
            )

        target = goal.cadence_per_week or 0
        pct    = round(min((completed_this_week / target * 100) if target > 0 else 0, 100), 1)

        items.append(GoalProgressItem(
            goal_id             = goal.id,
            goal_title          = goal.title,
            goal_category       = goal.category,
            status              = goal.status or "active",
            target_per_week     = target,
            completed_this_week = completed_this_week,
            progress_pct        = pct,
            linked_habit_count  = len(habits),
            end_date            = goal.end_date,
            duration_weeks      = goal.duration_weeks,
            cadence_per_week    = goal.cadence_per_week,
            schedule_days       = goal.schedule_days,
        ))

    return GoalProgressResponse(
        week_start = week_start_str,
        week_end   = week_end_str,
        goals      = items,
    )


# ── Helpers ────────────────────────────────────────────────────────────────

def _compute_end_date(explicit_end: str | None, duration_weeks: int | None) -> str | None:
    """Return an end date string.

    Explicit end_date wins; falls back to today + duration_weeks; None if neither provided.
    """
    if explicit_end:
        return explicit_end
    if duration_weeks:
        return (date.today() + timedelta(weeks=duration_weeks)).isoformat()
    return None
