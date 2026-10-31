"""Strict API contracts for the ZARRY general-assistant gateway."""
from __future__ import annotations

from typing import Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AssistantRequest(StrictModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: Optional[UUID] = None
    request_id: UUID = Field(default_factory=uuid4)


class AssistantResponse(StrictModel):
    request_id: UUID
    conversation_id: UUID
    response: str = Field(min_length=1, max_length=30000)
    provider: str = Field(min_length=1, max_length=80)
    fallback_used: bool = False


class ImageRequest(StrictModel):
    prompt: str = Field(min_length=1, max_length=2000)
    request_id: UUID = Field(default_factory=uuid4)
    size: Literal["1024x1024", "1024x768", "768x1024"] = "1024x1024"


class ImageResponse(StrictModel):
    request_id: UUID
    image_url: str = Field(min_length=1, max_length=2048)
    provider: str = Field(min_length=1, max_length=80)
    fallback_used: bool = False
