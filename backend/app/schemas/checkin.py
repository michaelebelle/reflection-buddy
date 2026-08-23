from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class HabitLogCreate(BaseModel):
    habit_id:  str
    date:      str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD")
    completed: bool
    note:      Optional[str] = None


class HabitLogUpdate(BaseModel):
    completed: Optional[bool] = None
    note:      Optional[str]  = None


class HabitLogResponse(BaseModel):
    id:            str
    user_id:       str
    habit_id:      str
    date:          str
    completed:     bool
    note:          Optional[str]
    value_numeric: Optional[float]
    created_at:    datetime
    updated_at:    datetime
    model_config = {"from_attributes": True}


class TodayCheckIn(BaseModel):
    """One card shown in the Goal Check-In section — a due habit + its log (if any)."""
    habit_id:             str
    habit_name:           str
    schedule_type:        str
    schedule_days:        Optional[str]      # "0,2,5" → Mon,Wed,Sat; null if not specific_days
    positive_or_negative: str
    log:                  Optional[HabitLogResponse] = None


class TodayCheckInsResponse(BaseModel):
    date:       str             # "YYYY-MM-DD" of the queried day
    check_ins:  list[TodayCheckIn]
