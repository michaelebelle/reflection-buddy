from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.onboarding import UserHabit
from app.models.user import User
from app.schemas.checkin import (
    HabitLogCreate,
    HabitLogUpdate,
    HabitLogResponse,
    TodayCheckInsResponse,
)
from app.services import checkin as checkin_service
from app.services.auth import get_current_user

router = APIRouter(prefix="/check-ins", tags=["check-ins"])


@router.get("/today", response_model=TodayCheckInsResponse)
def get_today_check_ins(
    date: str | None = Query(
        None,
        description=(
            "Override the target date as YYYY-MM-DD. "
            "Pass the user's local date to avoid server-timezone issues. "
            "Defaults to the server's local date."
        ),
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all habits scheduled for today, with any existing log for each.

    Use the `date` query parameter to pass the user's local date — this avoids
    timezone mismatches between the server and the browser.
    """
    return checkin_service.get_today_check_ins(db, user_id=current_user.id, date_str=date)


@router.post("", response_model=HabitLogResponse, status_code=status.HTTP_201_CREATED)
def create_check_in(
    body: HabitLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record a check-in for a habit on a specific date.

    If a log already exists for this (habit, date), it is updated in place.
    This makes POST idempotent — safe to call multiple times.
    """
    # Verify the habit belongs to the requesting user
    habit = (
        db.query(UserHabit)
        .filter(UserHabit.id == body.habit_id, UserHabit.user_id == current_user.id)
        .first()
    )
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")

    return checkin_service.create_log(db, user_id=current_user.id, data=body)


@router.put("/{log_id}", response_model=HabitLogResponse)
def update_check_in(
    log_id: str,
    body: HabitLogUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the completed status or note on an existing check-in log."""
    log = checkin_service.update_log(db, log_id=log_id, user_id=current_user.id, data=body)
    if not log:
        raise HTTPException(status_code=404, detail="Check-in log not found")
    return log
