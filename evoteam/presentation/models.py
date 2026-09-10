"""Versioned public envelope. Domain objects are projected, never mutated."""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class EvidenceEnvelope(BaseModel):
    schema_version: Literal["1"] = "1"
    source_kind: Literal["current_database"] = "current_database"
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    code_commit: str | None = None
    data: dict[str, Any]
    missing_refs: list[str] = Field(default_factory=list)
