from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    occupation: str = Field(..., min_length=1, max_length=150)
    interests: list[str] = Field(..., min_length=1, max_length=10)
    hobbies: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("name", "occupation", mode="before")
    @classmethod
    def strip_str(cls, v: str) -> str:
        return v.strip()

    @field_validator("interests", "hobbies", mode="before")
    @classmethod
    def clean_tags(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for tag in v:
            tag = tag.strip()[:50]
            lower = tag.lower()
            if tag and lower not in seen:
                seen.add(lower)
                result.append(tag)
        return result

    @field_validator("interests")
    @classmethod
    def interests_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("interests must have at least 1 item")
        return v


class UserRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    occupation: str
    interests: list[str]
    hobbies: list[str]


class FeedRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: int
    title: str
    summary: str
    source: str
    url: str
    topic: str
    image_url: str
    published_date: str
    liked: bool
    fetched_at: datetime


class EventRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: int
    name: str
    date: str
    location: str
    type: str
    url: str
    reason: str
    image_url: str
    liked: bool
    fetched_at: datetime
