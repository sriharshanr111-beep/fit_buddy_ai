"""Pydantic schemas used to validate user input."""
from pydantic import BaseModel, Field, field_validator

from .config import GOALS, INTENSITIES


class UserInput(BaseModel):
    username: str = Field(..., min_length=1, max_length=60)
    user_id: str = Field(..., min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_.-]+$")
    age: int = Field(..., ge=10, le=100)
    weight: float = Field(..., ge=20, le=300, description="Weight in kg")
    goal: str
    intensity: str

    @field_validator("username", "user_id")
    @classmethod
    def strip_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be empty")
        return v

    @field_validator("goal")
    @classmethod
    def check_goal(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in GOALS:
            raise ValueError(f"goal must be one of: {', '.join(GOALS)}")
        return v

    @field_validator("intensity")
    @classmethod
    def check_intensity(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in INTENSITIES:
            raise ValueError(f"intensity must be one of: {', '.join(INTENSITIES)}")
        return v


class FeedbackRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=40)
    feedback: str = Field(..., min_length=3, max_length=1000)

    @field_validator("user_id", "feedback")
    @classmethod
    def strip_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be empty")
        return v