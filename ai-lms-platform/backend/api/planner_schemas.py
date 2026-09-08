import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

VALID_WEEKDAYS = {
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
}

TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class AvailabilityWindowSchema(BaseModel):
    start: str = Field(..., description="Start time in HH:MM format (24h)")
    end: str = Field(..., description="End time in HH:MM format (24h)")

    @field_validator("start", "end")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        v_clean = v.strip()
        if not TIME_PATTERN.match(v_clean):
            raise ValueError(f"Time '{v}' must be in HH:MM 24-hour format (e.g. '18:00').")
        return v_clean

    @model_validator(mode="after")
    def validate_start_before_end(self) -> "AvailabilityWindowSchema":
        start_parts = [int(p) for p in self.start.split(":")]
        end_parts = [int(p) for p in self.end.split(":")]
        start_min = start_parts[0] * 60 + start_parts[1]
        end_min = end_parts[0] * 60 + end_parts[1]
        if start_min >= end_min:
            raise ValueError(f"Window start time ({self.start}) must be earlier than end time ({self.end}).")
        return self


class StudyPreferenceRequest(BaseModel):
    exam_date: date = Field(..., description="Target exam or completion date")
    daily_study_limit_minutes: int = Field(..., description="Maximum study minutes per day")
    available_days: List[str] = Field(..., description="Days of the week available for study")
    availability_windows: List[AvailabilityWindowSchema] = Field(..., description="List of daily availability windows")
    preferred_session_minutes: int = Field(default=60, description="Preferred session chunk size in minutes")

    @field_validator("exam_date")
    @classmethod
    def validate_exam_date_future(cls, v: date) -> date:
        if v <= date.today():
            raise ValueError("Exam date must be in the future.")
        return v

    @field_validator("daily_study_limit_minutes")
    @classmethod
    def validate_daily_limit(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Daily study limit minutes must be greater than 0.")
        return v

    @field_validator("preferred_session_minutes")
    @classmethod
    def validate_preferred_session(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Preferred session minutes must be greater than 0.")
        return v

    @field_validator("available_days")
    @classmethod
    def validate_available_days(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one available study day must be specified.")
        
        normalized: List[str] = []
        seen = set()
        for day in v:
            d_norm = day.strip().lower()
            if d_norm not in VALID_WEEKDAYS:
                raise ValueError(f"'{day}' is not a valid weekday. Allowed: {sorted(list(VALID_WEEKDAYS))}")
            if d_norm in seen:
                raise ValueError(f"Duplicate weekday '{d_norm}' in available days is not allowed.")
            seen.add(d_norm)
            normalized.append(d_norm)
        return normalized

    @field_validator("availability_windows")
    @classmethod
    def validate_windows_not_empty(cls, v: List[AvailabilityWindowSchema]) -> List[AvailabilityWindowSchema]:
        if not v:
            raise ValueError("At least one availability window must be specified.")
        return v

    @model_validator(mode="after")
    def validate_preferred_le_daily(self) -> "StudyPreferenceRequest":
        if self.preferred_session_minutes > self.daily_study_limit_minutes:
            raise ValueError(
                f"Preferred session minutes ({self.preferred_session_minutes}) "
                f"cannot exceed daily study limit ({self.daily_study_limit_minutes})."
            )
        return self


class StudyPreferenceResponse(BaseModel):
    id: int
    user_id: int
    course_id: int
    exam_date: date
    daily_study_limit_minutes: int
    available_days: List[str]
    availability_windows: List[Dict[str, str]]
    preferred_session_minutes: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlanGenerateRequest(BaseModel):
    completed_lesson_ids: Optional[List[int]] = Field(
        default=None,
        description="Optional list of explicitly completed lesson IDs",
    )
    start_date: Optional[date] = Field(
        default=None,
        description="Optional scheduling start date (defaults to today)",
    )


class StudySessionResponse(BaseModel):
    id: int
    study_plan_id: int
    lesson_id: Optional[int] = None
    session_date: date
    start_time: str
    end_time: str
    duration_minutes: int
    session_type: str  # "lesson", "revision"
    status: str        # "scheduled", "completed", "missed"
    priority: str      # "high", "medium", "low"
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class StudyPlanResponse(BaseModel):
    id: int
    user_id: int
    course_id: int
    exam_date: date
    total_planned_minutes: int
    status: str
    sessions: List[StudySessionResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class SessionStatusUpdate(BaseModel):
    status: str = Field(..., description="Updated status: 'scheduled', 'completed', or 'missed'")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        s_clean = v.strip().lower()
        if s_clean not in {"scheduled", "completed", "missed"}:
            raise ValueError("Status must be one of: 'scheduled', 'completed', 'missed'.")
        return s_clean
