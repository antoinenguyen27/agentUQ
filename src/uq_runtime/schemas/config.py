"""Configuration models."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class PolicyPreset(str, Enum):
    BALANCED = "balanced"
    CONSERVATIVE = "conservative"
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"


class CapabilityConfig(BaseModel):
    require_logprobs: bool = True
    require_topk: bool = False
    fail_on_missing_logprobs: bool = True
    fail_on_missing_topk: bool = False
    allow_degraded_mode: bool = True
    block_without_signal_for_critical: bool = False


class ThresholdConfig(BaseModel):
    low_margin_log: dict[str, float] = Field(
        default_factory=lambda: {
            "critical_action": 0.35,
            "important_action": 0.25,
            "informational": 0.15,
            "low_priority": 0.10,
        }
    )
    entropy: dict[str, float] = Field(
        default_factory=lambda: {
            "critical_action": 1.20,
            "important_action": 1.50,
            "informational": 1.80,
            "low_priority": 1.80,
        }
    )
    spike_surprise: dict[str, float] = Field(
        default_factory=lambda: {
            "critical_action": 3.5,
            "important_action": 4.0,
            "informational": 5.0,
            "low_priority": 6.0,
        }
    )
    tail_surprise: dict[str, float] = Field(
        default_factory=lambda: {
            "critical_action": 2.0,
            "important_action": 2.4,
            "informational": 3.0,
            "low_priority": 3.4,
        }
    )
    off_top1_rate: dict[str, float] = Field(
        default_factory=lambda: {
            "critical_action": 0.20,
            "important_action": 0.30,
            "informational": 0.50,
            "low_priority": 0.60,
        }
    )
    action_head_surprise: dict[str, float] = Field(
        default_factory=lambda: {
            "critical_action": 1.6,
            "important_action": 2.1,
            "informational": 3.0,
            "low_priority": 3.5,
        }
    )
    min_run: int = 2


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
    policy: PolicyPreset | str = PolicyPreset.BALANCED
    thresholds: ThresholdConfig = Field(default_factory=ThresholdConfig)
    segmentation: SegmentationConfig = Field(default_factory=SegmentationConfig)
    integrations: IntegrationConfig = Field(default_factory=IntegrationConfig)
    capability: CapabilityConfig = Field(default_factory=CapabilityConfig)
    custom_rules: list[CustomRule] = Field(default_factory=list)
    deterministic: bool | None = None
    canonical_temperature_max: float = 0.0
    canonical_top_p_min: float = 1.0
    retries_allowed: int = 1
