"""Goal Check-In service.

All scheduling logic is deterministic — no LLM calls here.
Weekday convention: Monday = 0, Sunday = 6 (Python's date.weekday()).
schedule_days stores comma-separated integers in this same convention.
"""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy.orm import Session

from app.models.checkin import HabitLog
from app.models.onboarding import UserHabit
from app.schemas.checkin import HabitLogCreate, HabitLogUpdate

logger = logging.getLogger(__name__)


# ── Scheduling ─────────────────────────────────────────────────────────────

def _is_due(habit: UserHabit, weekday: int) -> bool:
    """Return True if this habit is scheduled for the given weekday (0=Mon, 6=Sun)."""
    stype = habit.schedule_type or "unscheduled"
    if stype == "unscheduled":
        return False
    if stype == "daily":
        return True
    if stype == "specific_days" and habit.schedule_days:
        due_days = {int(d.strip()) for d in habit.schedule_days.split(",") if d.strip()}
        return weekday in due_days
    if stype == "x_per_week":
        # No fixed days — surface every day and let the user check in when they do it.
        return True
    return False


# ── Read ───────────────────────────────────────────────────────────────────

def get_today_check_ins(
    db: Session,
    user_id: str,
    date_str: str | None = None,
) -> dict:
    """Return habits due today, each paired with any existing log for that date.

    Args:
        date_str: Override "today" as YYYY-MM-DD. Useful for testing and
                  for callers that pass the user's local date instead of the
                  server's. Defaults to the server's local date.
    """
    target_date = date.fromisoformat(date_str) if date_str else date.today()
    weekday     = target_date.weekday()   # 0 = Monday, 6 = Sunday
    date_iso    = target_date.isoformat()

    habits     = db.query(UserHabit).filter(UserHabit.user_id == user_id).all()
    due_habits = [h for h in habits if _is_due(h, weekday)]

    # Fetch existing logs for this date in a single query
    habit_ids = [h.id for h in due_habits]
    existing_logs: dict[str, HabitLog] = {}
    if habit_ids:
        logs = (
            db.query(HabitLog)
            .filter(
                HabitLog.user_id  == user_id,
                HabitLog.date     == date_iso,
                HabitLog.habit_id.in_(habit_ids),
            )
            .all()
        )
        existing_logs = {log.habit_id: log for log in logs}

    return {
        "date": date_iso,
        "check_ins": [
            {
                "habit_id":             h.id,
                "habit_name":           h.name,
                "schedule_type":        h.schedule_type or "unscheduled",
                "schedule_days":        h.schedule_days,
                "positive_or_negative": h.positive_or_negative,
                "log":                  existing_logs.get(h.id),
            }
            for h in due_habits
        ],
    }


def get_log(db: Session, log_id: str, user_id: str) -> HabitLog | None:
    return (
        db.query(HabitLog)
        .filter(HabitLog.id == log_id, HabitLog.user_id == user_id)
        .first()
    )


# ── Write ──────────────────────────────────────────────────────────────────

def create_log(db: Session, user_id: str, data: HabitLogCreate) -> HabitLog:
    """Create a check-in log, or update it if one already exists for this habit+date.

    Idempotent — POST /check-ins is safe to call multiple times for the same
    (user, habit, date). The last call wins.
    """
    existing = (
        db.query(HabitLog)
        .filter(
            HabitLog.user_id  == user_id,
            HabitLog.habit_id == data.habit_id,
            HabitLog.date     == data.date,
        )
        .first()
    )
    if existing:
        existing.completed = data.completed
        if data.note is not None:
            existing.note = data.note
        db.commit()
        db.refresh(existing)
        return existing

    log = HabitLog(
        user_id=user_id,
        habit_id=data.habit_id,
        date=data.date,
        completed=data.completed,
        note=data.note,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def update_log(
    db: Session,
    log_id: str,
    user_id: str,
    data: HabitLogUpdate,
) -> HabitLog | None:
    log = get_log(db, log_id, user_id)
    if not log:
        return None
    if data.completed is not None:
        log.completed = data.completed
    if data.note is not None:
        log.note = data.note
    db.commit()
    db.refresh(log)
    return log
