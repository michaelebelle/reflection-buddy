from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class JournalEntryCreate(BaseModel):
    content: str = Field(..., min_length=1, description="Main journal entry text")
    mood: Optional[str] = Field(None, max_length=50)
    energy_level: Optional[int] = Field(None, ge=1, le=10)
    q_what_happened: Optional[str] = None
    q_how_felt: Optional[str] = None
    q_learned: Optional[str] = None
    q_improve_tomorrow: Optional[str] = None

    @field_validator("content")
    @classmethod
    def content_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Content cannot be blank")
        return v.strip()


class JournalEntryUpdate(BaseModel):
    """All fields optional — only supplied fields are updated (PATCH semantics)."""
    content: Optional[str] = Field(None, min_length=1)
    mood: Optional[str] = Field(None, max_length=50)
    energy_level: Optional[int] = Field(None, ge=1, le=10)
    q_what_happened: Optional[str] = None
    q_how_felt: Optional[str] = None
    q_learned: Optional[str] = None
    q_improve_tomorrow: Optional[str] = None


class JournalEntryResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    content: str
    mood: Optional[str]
    energy_level: Optional[int]
    q_what_happened: Optional[str]
    q_how_felt: Optional[str]
    q_learned: Optional[str]
    q_improve_tomorrow: Optional[str]
    created_by: Optional[str]
    updated_by: Optional[str]

    # Future: add ai_summary, themes, generated_prompts here as they're built

    model_config = {"from_attributes": True}


class JournalEntryList(BaseModel):
    entries: list[JournalEntryResponse]
    total: int
    skip: int
    limit: int


class SemanticSearchResult(BaseModel):
    """A single entry returned from semantic search."""
    id: str
    content: str
    mood: Optional[str]
    created_at: datetime
    similarity: float  # 0.0 (unrelated) → 1.0 (identical)


class SemanticSearchResponse(BaseModel):
    query: str
    results: list[SemanticSearchResult]


class PromptResponse(BaseModel):
    """Reflection questions tailored to the writer's recent journal history."""
    mood_context: Optional[str]  # The mood that shaped these prompts (None = no mood found)
    prompts: list[str]           # Exactly 4 question strings, one per reflection field
    source: str = "default"      # "ai" | "heuristic" | "default" — for UI badges / debugging
