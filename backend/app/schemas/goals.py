"""Schemas for the standalone Goals router (outside onboarding)."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.onboarding import GoalCategory, TargetTimeframe, GoalResponse


class GoalCreateRequest(BaseModel):
    category:           GoalCategory
    title:              str = Field(..., min_length=2, max_length=200)
    why_it_matters:     str = Field(..., min_length=5)
    success_definition: str = Field(..., min_length=5)
    target_timeframe:   TargetTimeframe = TargetTimeframe.three_months
    cadence_per_week:   Optional[int]  = Field(None, ge=1, le=21)
    schedule_days:      Optional[str]  = Field(
        None,
        description="Comma-separated weekdays 0=Mon..6=Sun, e.g. '0,2,4,5'",
    )
    duration_weeks: Optional[int] = Field(None, ge=1, le=104)
    end_date:       Optional[str] = Field(None, description="YYYY-MM-DD override")


class GoalUpdateRequest(BaseModel):
    category:           Optional[GoalCategory]      = None
    title:              Optional[str]               = Field(None, min_length=2, max_length=200)
    why_it_matters:     Optional[str]               = Field(None, min_length=5)
    success_definition: Optional[str]               = Field(None, min_length=5)
    target_timeframe:   Optional[TargetTimeframe]   = None
    status:             Optional[str]               = Field(
        None, pattern="^(active|archived|completed)$"
    )
    cadence_per_week:   Optional[int]               = Field(None, ge=1, le=21)
    schedule_days:      Optional[str]               = None
    duration_weeks:     Optional[int]               = Field(None, ge=1, le=104)
    end_date:           Optional[str]               = None


class GoalProgressItem(BaseModel):
    goal_id:             str
    goal_title:          str
    goal_category:       str
    status:              str
    target_per_week:     int
    completed_this_week: int
    progress_pct:        float
    linked_habit_count:  int
    end_date:            Optional[str]
    duration_weeks:      Optional[int]
    cadence_per_week:    Optional[int]
    schedule_days:       Optional[str]


class GoalProgressResponse(BaseModel):
    week_start: str   # ISO date of Monday
    week_end:   str   # ISO date of Sunday
    goals:      list[GoalProgressItem]


# Re-export so callers can import everything from here
__all__ = [
    "GoalCreateRequest",
    "GoalUpdateRequest",
    "GoalProgressItem",
    "GoalProgressResponse",
    "GoalResponse",
]
