---
title: Config Models
description: Public configuration models for analysis mode, thresholds, segmentation, integrations, and custom rules.
slug: /reference/config-models
sidebar_position: 11
---

# Config Models

## `UQConfig` (`Stable`)

- Import: `from agentuq import UQConfig`
- Signature:

```python
UQConfig(
    *,
    mode="auto",
    policy=PolicyPreset.BALANCED,
    tolerance=TolerancePreset.BALANCED,
    thresholds=ThresholdConfig(),
    segmentation=SegmentationConfig(),
    integrations=IntegrationConfig(),
    capability=CapabilityConfig(),
    custom_rules=list[CustomRule](),
    deterministic=None,
    canonical_temperature_max=0.0,
    canonical_top_p_min=1.0,
    retries_allowed=1,
)
```

- Purpose: top-level analysis and routing config
- Key behavioral notes:
  `mode` accepts `auto | canonical | realized`
  `policy` accepts `balanced | conservative | aggressive | custom`
  `tolerance` accepts `strict | balanced | lenient`
  `deterministic`, `canonical_temperature_max`, and `canonical_top_p_min` are advanced mode-selection overrides

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `mode` | `auto | canonical | realized` | `auto` | Chooses automatic, forced-canonical, or forced-realized mode behavior. |
| `policy` | `PolicyPreset` | `balanced` | Controls action selection after events are emitted. |
| `tolerance` | `TolerancePreset` | `balanced` | Controls how easily events fire. |
| `thresholds` | `ThresholdConfig` | factory | Optional numeric overrides on top of the chosen tolerance preset. |
| `segmentation` | `SegmentationConfig` | factory | Enables or disables major segmentation modes. |
| `integrations` | `IntegrationConfig` | factory | Integration-oriented config surface; not a first-line tuning lever in the current direct-provider loop. |
| `capability` | `CapabilityConfig` | factory | Controls fail-loud and degraded-mode behavior. |
| `custom_rules` | `list[CustomRule]` | factory | Declarative action overrides evaluated before built-in policy logic. |
| `deterministic` | `bool \| None` | `None` | Advanced override used in canonical mode selection when provided. |
| `canonical_temperature_max` | `float` | `0.0` | Advanced threshold for canonical-mode temperature checks. |
| `canonical_top_p_min` | `float` | `1.0` | Advanced threshold for canonical-mode top-p checks. |
| `retries_allowed` | `int` | `1` | Present on the config model, but caller-side retry orchestration remains user-owned in the current implementation. |

- Links: [Policies](../concepts/policies.md), [Tolerance](../concepts/tolerance.md), [Canonical vs realized](../concepts/canonical_vs_realized.md)

## `CapabilityConfig` (`Stable`)

- Import: `from agentuq.schemas.config import CapabilityConfig`
- Signature: `CapabilityConfig(*, require_logprobs=True, require_topk=False, fail_on_missing_logprobs=True, fail_on_missing_topk=False, allow_degraded_mode=True, block_without_signal_for_critical=False)`
- Purpose: capability enforcement and degraded-mode behavior

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `require_logprobs` | `bool` | `True` | Requires logprob request intent in normal flows. |
| `require_topk` | `bool` | `False` | Escalates top-k from optional to required. |
| `fail_on_missing_logprobs` | `bool` | `True` | Raises instead of degrading when selected-token logprobs are missing. |
| `fail_on_missing_topk` | `bool` | `False` | Raises instead of degrading when top-k is missing. |
| `allow_degraded_mode` | `bool` | `True` | Allows downgrade paths instead of immediate failure. |
| `block_without_signal_for_critical` | `bool` | `False` | Blocks critical workflows when no usable token signal is available. |

## `ThresholdConfig` (`Stable`)

- Import: `from agentuq.schemas.config import ThresholdConfig`
- Signature: `ThresholdConfig(*, low_margin_log=None, entropy=None, spike_surprise=None, tail_surprise=None, off_top1_rate=None, action_head_surprise=None, min_run=None)`
- Purpose: override selected threshold tables from the chosen tolerance preset

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `low_margin_log` | `dict[str, float] \| None` | `None` | Overrides low-margin thresholds by priority. |
| `entropy` | `dict[str, float] \| None` | `None` | Overrides entropy thresholds by priority. |
| `spike_surprise` | `dict[str, float] \| None` | `None` | Overrides single-token surprise spike thresholds by priority. |
| `tail_surprise` | `dict[str, float] \| None` | `None` | Overrides tail-risk thresholds by priority. |
| `off_top1_rate` | `dict[str, float] \| None` | `None` | Overrides realized-mode rank drift thresholds by priority. |
| `action_head_surprise` | `dict[str, float] \| None` | `None` | Overrides action-head instability thresholds by priority. |
| `min_run` | `int \| None` | `None` | Minimum contiguous run length for run-based events; must be at least `1` when set. |

- Caveats: override maps only accept the priority keys `critical_action`, `important_action`, `informational`, and `low_priority`

## `SegmentationConfig` (`Stable`)

- Import: `from agentuq.schemas.config import SegmentationConfig`
- Signature: `SegmentationConfig(*, enable_json_leaf_segmentation=True, enable_react_segmentation=True, enable_sql_segmentation=True, enable_browser_dsl_segmentation=True, enable_code_segmentation=True, fallback_line_split=True)`
- Purpose: coarse feature switches for major segmentation modes

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `enable_json_leaf_segmentation` | `bool` | `True` | Enable JSON leaf extraction. |
| `enable_react_segmentation` | `bool` | `True` | Enable explicit ReAct-style block segmentation. |
| `enable_sql_segmentation` | `bool` | `True` | Enable SQL statement and clause segmentation. |
| `enable_browser_dsl_segmentation` | `bool` | `True` | Enable browser DSL detection and argument segmentation. |
| `enable_code_segmentation` | `bool` | `True` | Enable code statement segmentation. |
| `fallback_line_split` | `bool` | `True` | Allow heuristic line-based fallback segmentation when no stronger structure is found. |

- Caveats: segmentation is intentionally conservative; see [Segmentation](../concepts/segmentation.md)

## `IntegrationConfig` (`Advanced`)

- Import: `from agentuq.schemas.config import IntegrationConfig`
- Signature: `IntegrationConfig(*, strict_openrouter_require_parameters=True, annotate_framework_metadata=True)`
- Purpose: integration-oriented configuration surface exposed on `UQConfig`

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `strict_openrouter_require_parameters` | `bool` | `True` | Present on the config model for integration-facing policy, not a first-line direct-provider tuning knob. |
| `annotate_framework_metadata` | `bool` | `True` | Present on the config model for framework metadata behavior; current quickstarts still route explicitly through integration helpers. |

## `CustomRule` (`Stable`)

- Import: `from agentuq.schemas.config import CustomRule`
- Signature: `CustomRule(*, when: dict[str, Any], then: str)`
- Purpose: declarative action override evaluated before built-in policy logic

| Field | Type | Notes |
| --- | --- | --- |
| `when` | `dict[str, Any]` | Supported keys in the current implementation are `segment_kind`, `segment_priority`, `events_any`, and `severity_at_least`. |
| `then` | `str` | Action value to return when the rule matches. |

- Links: [Policies](../concepts/policies.md)

