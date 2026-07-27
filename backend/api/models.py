from typing import Optional
from pydantic import BaseModel, Field


class AddToQueueRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    play_now: bool = False


class VolumeRequest(BaseModel):
    volume: float = Field(ge=0.0, le=100.0)


class RepeatRequest(BaseModel):
    repeat: str = "off"


class RadioToggleRequest(BaseModel):
    enabled: bool


class MoodPlayRequest(BaseModel):
    mood_id: str
    custom_text: Optional[str] = None
    play_now: bool = True


class UpdateProfileRequest(BaseModel):
    user_id: str = "web_guest"
    bio: Optional[str] = Field(None, max_length=200)


class ReorderQueueRequest(BaseModel):
    from_index: int = Field(ge=0)
    to_index: int = Field(ge=0)


class SeekRequest(BaseModel):
    position_ms: int = Field(ge=0)


class MuteRequest(BaseModel):
    muted: bool
