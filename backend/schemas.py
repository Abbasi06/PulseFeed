from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    occupation: str = Field(..., min_length=1, max_length=150)
    selected_chips: list[str] = Field(..., min_length=1, max_length=5)
    field: str = ""
    sub_fields: list[str] = Field(default_factory=list)

    @field_validator("name", "occupation", mode="before")
    @classmethod
    def strip_str(cls, v: str) -> str:
        return v.strip()

    @field_validator("selected_chips", mode="before")
    @classmethod
    def clean_tags(cls, v: list[str]) -> list[str]:
        if not isinstance(v, list):
            return v
        seen: set[str] = set()
        result: list[str] = []
        for tag in v:
            tag = tag.strip()[:50]
            lower = tag.lower()
            if tag and lower not in seen:
                seen.add(lower)
                result.append(tag)
        return result

    @field_validator("selected_chips")
    @classmethod
    def chips_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("must select at least 1 chip")
        if len(v) > 5:
            raise ValueError("can select a maximum of 5 chips")
        return v


class UserUpdate(BaseModel):
    """Schema for PUT /users/{id} — selected_chips is optional (preserved if omitted)."""

    name: str = Field(..., min_length=1, max_length=100)
    occupation: str = Field(..., min_length=1, max_length=150)
    selected_chips: list[str] | None = None
    field: str = ""
    sub_fields: list[str] = Field(default_factory=list)
    preferred_formats: list[str] = Field(default_factory=list)

    @field_validator("name", "occupation", mode="before")
    @classmethod
    def strip_str(cls, v: str) -> str:
        return v.strip()

    @field_validator("selected_chips", mode="before")
    @classmethod
    def clean_tags(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        if not isinstance(v, list):
            return v
        seen: set[str] = set()
        result: list[str] = []
        for tag in v:
            tag = tag.strip()[:50]
            lower = tag.lower()
            if tag and lower not in seen:
                seen.add(lower)
                result.append(tag)
        return result

    @field_validator("selected_chips")
    @classmethod
    def chips_not_empty(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        if not v:
            raise ValueError("must select at least 1 chip")
        if len(v) > 5:
            raise ValueError("can select a maximum of 5 chips")
        return v


class UserRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    occupation: str
    field: str
    selected_chips: list[str]
    sub_fields: list[str]
    preferred_formats: list[str]


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


class TopRead(BaseModel):
    title: str
    url: str
    source: str


class BriefRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: int
    headline: str
    signals: list[str]
    top_reads: list[TopRead]
    watch: list[str]
    generated_at: datetime
