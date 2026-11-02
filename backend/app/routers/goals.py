from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.onboarding import GoalResponse
from app.schemas.goals import (
    GoalCreateRequest,
    GoalUpdateRequest,
    GoalProgressResponse,
    SetGoalHabitsRequest,
)
from app.services import goals as goals_service
from app.services.auth import get_current_user

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("/progress", response_model=GoalProgressResponse)
def get_goal_progress(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Return weekly adherence for all active goals.

    Registered before /{goal_id} so FastAPI doesn't treat 'progress' as an ID.
    """
    return goals_service.get_goals_progress(db, user_id=current_user.id)


@router.get("", response_model=list[GoalResponse])
def list_goals(
    status:       str | None = Query(None, description="Filter by status: active|archived|completed"),
    db:           Session    = Depends(get_db),
    current_user: User       = Depends(get_current_user),
):
    return goals_service.get_goals(db, user_id=current_user.id, status=status)


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(
    data:         GoalCreateRequest,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    return goals_service.create_goal(db, user_id=current_user.id, data=data)


@router.get("/{goal_id}", response_model=GoalResponse)
def get_goal(
    goal_id:      str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    goal = goals_service.get_goal(db, goal_id=goal_id, user_id=current_user.id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.put("/{goal_id}/habits")
def set_goal_habits(
    goal_id:      str,
    data:         SetGoalHabitsRequest,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Set the habits linked to a goal.

    Replaces the current set — habits in the list get goal_id set, habits
    previously linked but not in the list get goal_id cleared.
    Returns the updated list of linked habits.
    """
    linked = goals_service.set_goal_habits(
        db, goal_id=goal_id, user_id=current_user.id, habit_ids=data.habit_ids
    )
    return {"goal_id": goal_id, "linked_habits": [{"id": h.id, "name": h.name} for h in linked]}


@router.put("/{goal_id}", response_model=GoalResponse)
def update_goal(
    goal_id:      str,
    data:         GoalUpdateRequest,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    goal = goals_service.update_goal(db, goal_id=goal_id, user_id=current_user.id, data=data)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal
