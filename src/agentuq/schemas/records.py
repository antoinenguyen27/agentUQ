"""Normalized records used across adapters and analysis."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class CapabilityLevel(str, Enum):
    FULL = "full"
    SELECTED_ONLY = "selected_only"
    NONE = "none"


class TopToken(BaseModel):
    token: str
    logprob: float


class StructuredBlock(BaseModel):
    type: str
    text: str | None = None
    name: str | None = None
    arguments: str | None = None
    format: str | None = None
    char_start: int | None = None
    char_end: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GenerationRecord(BaseModel):
    provider: str
    transport: str
    model: str
    request_id: str | None = None
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    stream: bool | None = None
    step_kind: str | None = None
    raw_text: str | None = None
    selected_tokens: list[str] = Field(default_factory=list)
    selected_logprobs: list[float] | None = None
    top_logprobs: list[list[TopToken]] | None = None
    structured_blocks: list[StructuredBlock] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityReport(BaseModel):
    selected_token_logprobs: bool = False
    topk_logprobs: bool = False
    topk_k: int | None = None
    structured_blocks: bool = False
    function_call_structure: bool = False
    provider_declared_support: bool | None = None
    request_attempted_logprobs: bool = False
    request_attempted_topk: int | None = None
    degraded_reason: str | None = None

    @property
    def level(self) -> CapabilityLevel:
        if self.selected_token_logprobs and self.topk_logprobs:
            return CapabilityLevel.FULL
        if self.selected_token_logprobs:
            return CapabilityLevel.SELECTED_ONLY
        return CapabilityLevel.NONE


ModeLiteral = Literal["auto", "canonical", "realized"]

