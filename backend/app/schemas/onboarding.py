from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ── Enums ──────────────────────────────────────────────────────────────────

class GoalCategory(str, Enum):
    career        = "career"
    fitness       = "fitness"
    relationships = "relationships"
    mental_health = "mental_health"
    discipline    = "discipline"
    finances      = "finances"
    school        = "school"
    creativity    = "creativity"
    other         = "other"

class TargetTimeframe(str, Enum):
    one_month    = "1_month"
    three_months = "3_months"
    six_months   = "6_months"
    one_year     = "1_year"
    ongoing      = "ongoing"

class StressorCategory(str, Enum):
    work            = "work"
    school          = "school"
    relationships   = "relationships"
    family          = "family"
    money           = "money"
    health          = "health"
    loneliness      = "loneliness"
    burnout         = "burnout"
    motivation      = "motivation"
    time_management = "time_management"
    other           = "other"

class StressorFrequency(str, Enum):
    daily                  = "daily"
    several_times_per_week = "several_times_per_week"
    weekly                 = "weekly"
    occasionally           = "occasionally"

class HabitFrequency(str, Enum):
    daily        = "daily"
    three_per_week = "3x_per_week"
    five_per_week  = "5x_per_week"
    weekly       = "weekly"
    as_needed    = "as_needed"

class TrackingType(str, Enum):
    boolean  = "boolean"
    numeric  = "numeric"
    duration = "duration"
    text     = "text"


# ── Input schemas ──────────────────────────────────────────────────────────

class GoalCreate(BaseModel):
    category:           GoalCategory
    title:              str = Field(..., min_length=2, max_length=200)
    why_it_matters:     str = Field(..., min_length=5)
    success_definition: str = Field(..., min_length=5)
    target_timeframe:   TargetTimeframe


class StressorCreate(BaseModel):
    category:    StressorCategory
    description: str = Field(..., min_length=5)
    intensity:   int = Field(..., ge=1, le=10)
    frequency:   StressorFrequency


class HabitCreate(BaseModel):
    name:                 str = Field(..., min_length=2, max_length=100)
    desired_frequency:    HabitFrequency
    positive_or_negative: str = Field(..., pattern="^(positive|negative)$")
    tracking_type:        TrackingType
    schedule_type:        str = Field(
        default="unscheduled",
        pattern="^(daily|specific_days|x_per_week|unscheduled)$",
    )
    schedule_days:        Optional[str] = Field(
        None,
        description="Comma-separated weekdays 0=Mon..6=Sun, e.g. '0,2,5'. Only for specific_days.",
    )
    goal_id:              Optional[str] = None


class BaselineRatings(BaseModel):
    mood_baseline:              int = Field(..., ge=1, le=10)
    energy_baseline:            int = Field(..., ge=1, le=10)
    stress_baseline:            int = Field(..., ge=1, le=10)
    confidence_baseline:        int = Field(..., ge=1, le=10)
    discipline_baseline:        int = Field(..., ge=1, le=10)
    life_satisfaction_baseline: int = Field(..., ge=1, le=10)


class OnboardingCreate(BaseModel):
    goals:            list[GoalCreate]    = Field(..., min_length=1, max_length=3)
    stressors:        list[StressorCreate] = Field(default_factory=list, max_length=5)
    habits:           list[HabitCreate]   = Field(..., min_length=3, max_length=8)
    baseline_ratings: BaselineRatings


class OnboardingPatch(BaseModel):
    """All sections optional — only supplied sections are replaced."""
    goals:            Optional[list[GoalCreate]]    = Field(None, max_length=3)
    stressors:        Optional[list[StressorCreate]] = Field(None, max_length=5)
    habits:           Optional[list[HabitCreate]]   = Field(None, max_length=8)
    baseline_ratings: Optional[BaselineRatings]     = None


# ── Response schemas ───────────────────────────────────────────────────────

class GoalResponse(BaseModel):
    id:                 str
    category:           str
    title:              str
    why_it_matters:     str
    success_definition: str
    target_timeframe:   str
    status:             Optional[str] = "active"
    cadence_per_week:   Optional[int] = None
    schedule_days:      Optional[str] = None
    duration_weeks:     Optional[int] = None
    end_date:           Optional[str] = None
    created_at:         datetime
    updated_at:         Optional[datetime] = None
    model_config = {"from_attributes": True}


class StressorResponse(BaseModel):
    id:          str
    category:    str
    description: str
    intensity:   int
    frequency:   str
    created_at:  datetime
    model_config = {"from_attributes": True}


class HabitResponse(BaseModel):
    id:                   str
    name:                 str
    desired_frequency:    str
    positive_or_negative: str
    tracking_type:        str
    schedule_type:        Optional[str]
    schedule_days:        Optional[str]
    goal_id:              Optional[str]
    created_at:           datetime
    model_config = {"from_attributes": True}


class OnboardingResponse(BaseModel):
    goals:            list[GoalResponse]
    stressors:        list[StressorResponse]
    habits:           list[HabitResponse]
    baseline_ratings: Optional[BaselineRatings]
    completed_at:     Optional[datetime]
    model_config = {"from_attributes": True}
