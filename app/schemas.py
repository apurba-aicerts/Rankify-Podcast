"""Pydantic schemas for API requests and responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# PodcastScript (ephemeral — not stored in DB except snapshot on Podcast)
# ---------------------------------------------------------------------------


def _strip_nonempty(value: str, field: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field} must not be empty or whitespace")
    return cleaned


class Speaker(BaseModel):
    name: str = Field(description="Speaker name")
    voice_id: str = Field(description="TTS voice ID")

    @field_validator("name", "voice_id")
    @classmethod
    def strip_required(cls, value: str) -> str:
        return _strip_nonempty(value, "field")


class DialogueTurn(BaseModel):
    speaker: str
    text: str

    @field_validator("speaker", "text")
    @classmethod
    def strip_required(cls, value: str) -> str:
        return _strip_nonempty(value, "field")


class PodcastScript(BaseModel):
    title: str
    description: str
    speakers: List[Speaker]
    dialogue: List[DialogueTurn]

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        return _strip_nonempty(value, "title")

    @field_validator("description", mode="before")
    @classmethod
    def strip_description(cls, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()


# ---------------------------------------------------------------------------
# Outline (generation-only — coverage contract before script writing)
# ---------------------------------------------------------------------------


class OutlinePoint(BaseModel):
    claim: str = Field(description="One claim, definition, step, finding, or argument from the source")
    source_hint: str = Field(description="Short heading or quote fragment anchoring the point in the source")

    @field_validator("claim", "source_hint")
    @classmethod
    def strip_required(cls, value: str) -> str:
        return _strip_nonempty(value, "field")


class OutlineSection(BaseModel):
    title: str = Field(description="Section title from the source structure when possible")
    points: List[OutlinePoint] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        return _strip_nonempty(value, "title")


class PodcastOutline(BaseModel):
    title: str = Field(description="Working title derived from the source")
    sections: List[OutlineSection] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        return _strip_nonempty(value, "title")


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _strip_nonempty(value, "name")

    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = Field(None, pattern="^(active|archived)$")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return _strip_nonempty(value, "name")

    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None


class ProjectCounts(BaseModel):
    finished_podcasts: int = 0
    unfinished: int = 0
    total_items: int = 0


class ProjectSummary(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    status: str
    counts: ProjectCounts
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Backward-compatible alias for create/patch responses
ProjectResponse = ProjectSummary


class ProjectListResponse(BaseModel):
    projects: List[ProjectSummary]
    total: int
    totals: ProjectCounts


# ---------------------------------------------------------------------------
# Podcasts
# ---------------------------------------------------------------------------


class PodcastSummary(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    status: str = "ready"
    error_message: Optional[str] = None
    audio_url: Optional[str] = None
    script_id: Optional[UUID] = None
    created_at: datetime


class PodcastResponse(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: Optional[str] = None
    status: str = "ready"
    error_message: Optional[str] = None
    s3_key: Optional[str] = None
    audio_url: Optional[str] = None
    script_id: Optional[UUID] = None
    tts_model: str
    tts_metadata: Optional[dict[str, Any]] = None
    podcast_script_snapshot: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class PodcastListResponse(BaseModel):
    podcasts: List[PodcastSummary]
    total: int


class PodcastUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return _strip_nonempty(value, "title")

    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None


class GeneratePodcastRequest(BaseModel):
    podcast_script: PodcastScript
    tts_model: str = Field(default="gemini-2.5-flash-preview-tts")


class GeneratePodcastScriptResponse(BaseModel):
    success: bool
    message: str
    podcast_script: Optional[PodcastScript] = None


class GeneratePodcastResponse(BaseModel):
    success: bool
    message: str
    podcast: Optional[PodcastSummary] = None


# ---------------------------------------------------------------------------
# Stored podcast scripts (DB)
# ---------------------------------------------------------------------------


class ScriptCreateResponse(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    script: Optional[PodcastScript] = None
    text_model: str
    tts_model: str
    source_filename: Optional[str] = None
    auto_generate_podcast: bool = False
    created_at: datetime
    updated_at: datetime


class ScriptUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    script: Optional[PodcastScript] = None
    tts_model: Optional[str] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return _strip_nonempty(value, "title")

    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None


class ScriptListResponse(BaseModel):
    scripts: List[ScriptCreateResponse]
    total: int


class GeneratePodcastFromScriptRequest(BaseModel):
    tts_model: Optional[str] = None
    script: Optional[PodcastScript] = None


class ProjectItem(BaseModel):
    id: UUID
    kind: str  # "script" | "podcast"
    phase: str  # writing_script | script_ready | generating_audio | ready | failed
    title: str
    description: Optional[str] = None
    error_message: Optional[str] = None
    audio_url: Optional[str] = None
    script: Optional[PodcastScript] = None
    tts_model: Optional[str] = None
    text_model: Optional[str] = None
    script_id: Optional[UUID] = None  # script UUID — always set (same as id when kind == "script")
    created_at: datetime
    updated_at: datetime


class ProjectDetailResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    status: str
    counts: ProjectCounts
    items: List[ProjectItem] = []
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Voices / models (utility)
# ---------------------------------------------------------------------------


class VoiceInfo(BaseModel):
    id: str
    name: str
    description: str
    s3_key: Optional[str] = None
    audio_url: Optional[str] = None
    sample_available: bool
    sample_url: Optional[str] = Field(
        None,
        description="Deprecated — use audio_url",
    )


class VoicesResponse(BaseModel):
    voices: List[VoiceInfo]
    total: int


class ModelInfo(BaseModel):
    id: str
    name: str
    description: str


class ModelsResponse(BaseModel):
    text_models: List[ModelInfo]
    tts_models: List[ModelInfo]
    text_total: int
    tts_total: int
    limit: int = 10
    cached_at: Optional[datetime] = None


class TextModelsResponse(BaseModel):
    models: List[ModelInfo]
    total: int
    limit: int = 10
    cached_at: Optional[datetime] = None


class TtsModelsResponse(BaseModel):
    models: List[ModelInfo]
    total: int
    limit: int = 10
    cached_at: Optional[datetime] = None
