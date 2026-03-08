"""Configuration models."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

PRIORITY_LEVELS = ("critical_action", "important_action", "informational", "low_priority")


class PolicyPreset(str, Enum):
    BALANCED = "balanced"
    CONSERVATIVE = "conservative"
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"


class TolerancePreset(str, Enum):
    STRICT = "strict"
    BALANCED = "balanced"
    LENIENT = "lenient"


class CapabilityConfig(BaseModel):
    require_logprobs: bool = True
    require_topk: bool = False
    fail_on_missing_logprobs: bool = True
    fail_on_missing_topk: bool = False
    allow_degraded_mode: bool = True
    block_without_signal_for_critical: bool = False


class ThresholdConfig(BaseModel):
    low_margin_log: dict[str, float] | None = None
    entropy: dict[str, float] | None = None
    spike_surprise: dict[str, float] | None = None
    tail_surprise: dict[str, float] | None = None
    off_top1_rate: dict[str, float] | None = None
    action_head_surprise: dict[str, float] | None = None
    min_run: int | None = None

    @field_validator(
        "low_margin_log",
        "entropy",
        "spike_surprise",
        "tail_surprise",
        "off_top1_rate",
        "action_head_surprise",
    )
    @classmethod
    def validate_priority_keys(cls, value: dict[str, float] | None) -> dict[str, float] | None:
        if value is None:
            return value
        invalid = sorted(set(value) - set(PRIORITY_LEVELS))
        if invalid:
            allowed = ", ".join(PRIORITY_LEVELS)
            raise ValueError(f"Unknown priority override keys: {', '.join(invalid)}. Allowed: {allowed}.")
        return value

    @field_validator("min_run")
    @classmethod
    def validate_min_run(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("min_run must be at least 1 when provided.")
        return value


class SegmentationConfig(BaseModel):
    enable_json_leaf_segmentation: bool = True
    enable_react_segmentation: bool = True
    enable_sql_segmentation: bool = True
    enable_browser_dsl_segmentation: bool = True
    enable_code_segmentation: bool = True
    fallback_line_split: bool = True


class IntegrationConfig(BaseModel):
    strict_openrouter_require_parameters: bool = True
    annotate_framework_metadata: bool = True


class CustomRule(BaseModel):
    when: dict[str, Any]
    then: str


class UQConfig(BaseModel):
    mode: Literal["auto", "canonical", "realized"] = "auto"
    policy: PolicyPreset = PolicyPreset.BALANCED
    tolerance: TolerancePreset = TolerancePreset.BALANCED
    thresholds: ThresholdConfig = Field(default_factory=ThresholdConfig)
    segmentation: SegmentationConfig = Field(default_factory=SegmentationConfig)
    integrations: IntegrationConfig = Field(default_factory=IntegrationConfig)
    capability: CapabilityConfig = Field(default_factory=CapabilityConfig)
    custom_rules: list[CustomRule] = Field(default_factory=list)
    deterministic: bool | None = None
    canonical_temperature_max: float = 0.0
    canonical_top_p_min: float = 1.0
    retries_allowed: int = 1


THRESHOLD_PRESETS: dict[TolerancePreset, dict[str, dict[str, float] | int]] = {
    TolerancePreset.STRICT: {
        "low_margin_log": {
            "critical_action": 0.45,
            "important_action": 0.35,
            "informational": 0.25,
            "low_priority": 0.20,
        },
        "entropy": {
            "critical_action": 1.00,
            "important_action": 1.25,
            "informational": 1.50,
            "low_priority": 1.50,
        },
        "spike_surprise": {
            "critical_action": 3.0,
            "important_action": 3.5,
            "informational": 4.5,
            "low_priority": 5.0,
        },
        "tail_surprise": {
            "critical_action": 1.6,
            "important_action": 2.0,
            "informational": 2.6,
            "low_priority": 3.0,
        },
        "off_top1_rate": {
            "critical_action": 0.10,
            "important_action": 0.20,
            "informational": 0.35,
            "low_priority": 0.45,
        },
        "action_head_surprise": {
            "critical_action": 1.2,
            "important_action": 1.8,
            "informational": 2.6,
            "low_priority": 3.0,
        },
        "min_run": 1,
    },
    TolerancePreset.BALANCED: {
        "low_margin_log": {
            "critical_action": 0.35,
            "important_action": 0.25,
            "informational": 0.15,
            "low_priority": 0.10,
        },
        "entropy": {
            "critical_action": 1.20,
            "important_action": 1.50,
            "informational": 1.80,
            "low_priority": 1.80,
        },
        "spike_surprise": {
            "critical_action": 3.5,
            "important_action": 4.0,
            "informational": 5.0,
            "low_priority": 6.0,
        },
        "tail_surprise": {
            "critical_action": 2.0,
            "important_action": 2.4,
            "informational": 3.0,
            "low_priority": 3.4,
        },
        "off_top1_rate": {
            "critical_action": 0.20,
            "important_action": 0.30,
            "informational": 0.50,
            "low_priority": 0.60,
        },
        "action_head_surprise": {
            "critical_action": 1.6,
            "important_action": 2.1,
            "informational": 3.0,
            "low_priority": 3.5,
        },
        "min_run": 2,
    },
    TolerancePreset.LENIENT: {
        "low_margin_log": {
            "critical_action": 0.25,
            "important_action": 0.18,
            "informational": 0.10,
            "low_priority": 0.08,
        },
        "entropy": {
            "critical_action": 1.40,
            "important_action": 1.70,
            "informational": 2.10,
            "low_priority": 2.10,
        },
        "spike_surprise": {
            "critical_action": 4.0,
            "important_action": 4.5,
            "informational": 5.5,
            "low_priority": 6.5,
        },
        "tail_surprise": {
            "critical_action": 2.4,
            "important_action": 2.8,
            "informational": 3.4,
            "low_priority": 3.8,
        },
        "off_top1_rate": {
            "critical_action": 0.30,
            "important_action": 0.40,
            "informational": 0.60,
            "low_priority": 0.70,
        },
        "action_head_surprise": {
            "critical_action": 2.0,
            "important_action": 2.5,
            "informational": 3.4,
            "low_priority": 4.0,
        },
        "min_run": 3,
    },
}


def _merge_metric(
    base: dict[str, float],
    override: dict[str, float] | None,
) -> dict[str, float]:
    merged = dict(base)
    if override:
        merged.update(override)
    return merged


def resolve_thresholds(
    tolerance: TolerancePreset,
    overrides: ThresholdConfig | None = None,
) -> ThresholdConfig:
    preset = THRESHOLD_PRESETS[tolerance]
    overrides = overrides or ThresholdConfig()
    return ThresholdConfig(
        low_margin_log=_merge_metric(preset["low_margin_log"], overrides.low_margin_log),
        entropy=_merge_metric(preset["entropy"], overrides.entropy),
        spike_surprise=_merge_metric(preset["spike_surprise"], overrides.spike_surprise),
        tail_surprise=_merge_metric(preset["tail_surprise"], overrides.tail_surprise),
        off_top1_rate=_merge_metric(preset["off_top1_rate"], overrides.off_top1_rate),
        action_head_surprise=_merge_metric(preset["action_head_surprise"], overrides.action_head_surprise),
        min_run=overrides.min_run if overrides.min_run is not None else int(preset["min_run"]),
    )
