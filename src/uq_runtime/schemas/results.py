"""Result models for analysis, events, and policy decisions."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from uq_runtime.schemas.records import CapabilityLevel, CapabilityReport


class PrimaryScoreType(str, Enum):
    G_NLL = "g_nll"
    REALIZED_NLL = "realized_nll"


class EventSeverity(str, Enum):
    INFO = "info"
    WARN = "warn"
    HIGH = "high"
    CRITICAL = "critical"


class Action(str, Enum):
    CONTINUE = "continue"
    CONTINUE_WITH_ANNOTATION = "continue_with_annotation"
    REGENERATE_SEGMENT = "regenerate_segment"
    RETRY_STEP = "retry_step"
    RETRY_STEP_WITH_CONSTRAINTS = "retry_step_with_constraints"
    DRY_RUN_VERIFY = "dry_run_verify"
    ASK_USER_CONFIRMATION = "ask_user_confirmation"
    BLOCK_EXECUTION = "block_execution"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    EMIT_WEBHOOK = "emit_webhook"
    CUSTOM = "custom"


class Event(BaseModel):
    type: str
    severity: EventSeverity
    segment_id: str | None = None
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class SegmentMetrics(BaseModel):
    token_count: int = 0
    nll: float = 0.0
    avg_surprise: float = 0.0
    max_surprise: float = 0.0
    p95_surprise: float = 0.0
    tail_surprise_mean: float = 0.0
    mean_margin_log: float | None = None
    min_margin_log: float | None = None
    low_margin_rate: float | None = None
    low_margin_run_max: int | None = None
    mean_entropy_hat: float | None = None
    max_entropy_hat: float | None = None
    high_entropy_rate: float | None = None
    high_entropy_run_max: int | None = None
    off_top1_rate: float | None = None
    off_topk_rate: float | None = None
    off_top1_run_max: int | None = None
    any_off_topk: bool = False


class SegmentResult(BaseModel):
    id: str
    kind: str
    priority: str
    text: str
    token_span: tuple[int, int]
    primary_score: float
    metrics: SegmentMetrics
    events: list[Event] = Field(default_factory=list)
    recommended_action: Action = Action.CONTINUE
    metadata: dict[str, Any] = Field(default_factory=dict)


class Diagnostics(BaseModel):
    warnings: list[str] = Field(default_factory=list)
    mode_reason: str | None = None
    token_count: int = 0


class Decision(BaseModel):
    action: Action
    rationale: str
    segment_actions: dict[str, Action] = Field(default_factory=dict)
    events: list[Event] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UQResult(BaseModel):
    primary_score: float
    primary_score_type: PrimaryScoreType
    mode: str
    capability_level: CapabilityLevel
    capability_report: CapabilityReport
    segments: list[SegmentResult]
    events: list[Event]
    action: Action
    diagnostics: Diagnostics = Field(default_factory=Diagnostics)
    decision: Decision | None = None

