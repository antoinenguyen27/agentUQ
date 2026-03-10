---
title: Root API
description: Stable and advanced exports re-exported from the top-level AgentUQ package.
slug: /reference/root-api
sidebar_position: 10
---

# Root API

This page covers the top-level public exports from `agentuq`.

## Stable Root API

### `Analyzer` (`Stable`)

- Import: `from agentuq import Analyzer`
- Signature: `Analyzer(config: UQConfig | None = None)`
- Purpose: shared analysis engine for scoring, segmentation, event emission, capability enforcement, and decision generation
- Key call: `analyze_step(record: GenerationRecord, capability: CapabilityReport | None = None) -> UQResult`
- Returns / output: `analyze_step(...)` returns a fully populated `UQResult`, including `result.decision`
- Caveats: mode selection and fail-loud behavior depend on `UQConfig`; see [Canonical vs realized](../concepts/canonical_vs_realized.md) and [Troubleshooting](../concepts/troubleshooting.md)

### `UQConfig` (`Stable`)

- Import: `from agentuq import UQConfig`
- Signature: `UQConfig(*, mode='auto', policy=PolicyPreset.BALANCED, tolerance=TolerancePreset.BALANCED, thresholds=..., segmentation=..., integrations=..., capability=..., custom_rules=..., deterministic=None, canonical_temperature_max=0.0, canonical_top_p_min=1.0, retries_allowed=1)`
- Purpose: top-level configuration model for analysis mode, policy, thresholds, segmentation, and capability behavior
- Key fields: `mode`, `policy`, `tolerance`, `thresholds`, `capability`, `custom_rules`
- Returns / output: plain Pydantic model consumed by `Analyzer` and integration helpers
- Caveats: `deterministic`, `canonical_temperature_max`, and `canonical_top_p_min` are advanced override-style fields; see [Config models](config-models.md)

### `Action` (`Stable`)

- Import: `from agentuq import Action`
- Purpose: action enum for step-level and segment-level recommendations
- Values: `continue`, `continue_with_annotation`, `regenerate_segment`, `retry_step`, `retry_step_with_constraints`, `dry_run_verify`, `ask_user_confirmation`, `block_execution`, `escalate_to_human`, `emit_webhook`, `custom`
- Returns / output: used by `Decision.action`, `Decision.segment_actions`, and `SegmentResult.recommended_action`
- Caveats: the built-in presets use the core runtime actions most heavily; the more workflow-specific values are mainly for custom dispatch

### `UQResult` (`Stable`)

- Import: `from agentuq import UQResult`
- Signature: `UQResult(*, primary_score, primary_score_type, mode, capability_level, capability_report, segments, events, action, diagnostics=..., decision=None, resolved_thresholds=None)`
- Purpose: complete structured result for one analyzed step
- Key methods:
  `pretty(verbosity='summary', show_thresholds='triggered') -> str`
  `rich_renderable(verbosity='summary', show_thresholds='triggered') -> Any`
  `rich_console_render(console=None, verbosity='summary', show_thresholds='triggered') -> None`
- Returns / output: carries both structured fields and convenience rendering helpers
- Caveats: `whole_response_score` is not the decision source of truth; see [Reading results](../concepts/reading_results.md)

### `Decision` (`Stable`)

- Import: `from agentuq import Decision`
- Signature: `Decision(*, action, rationale, segment_actions=..., events=..., metadata=...)`
- Purpose: policy output attached to `result.decision`
- Key fields: `action`, `rationale`, `segment_actions`, `events`
- Returns / output: step-level action plus per-segment action mapping
- Caveats: this is the primary branching object for runtime routing; see [Acting on decisions](../concepts/acting_on_decisions.md)

### `CapabilityReport` (`Stable`)

- Import: `from agentuq import CapabilityReport`
- Signature: `CapabilityReport(*, selected_token_logprobs=False, topk_logprobs=False, topk_k=None, structured_blocks=False, function_call_structure=False, provider_declared_support=None, request_attempted_logprobs=False, request_attempted_topk=None, degraded_reason=None)`
- Purpose: observed capability summary for the analyzed step
- Key fields: `selected_token_logprobs`, `topk_logprobs`, `topk_k`, `degraded_reason`
- Returns / output: surfaced directly on `UQResult.capability_report`
- Caveats: capability is determined from actual observed behavior, not just the request intent; see [Provider and framework capabilities](../concepts/provider_capabilities.md)

### `GenerationRecord` (`Stable`)

- Import: `from agentuq import GenerationRecord`
- Signature: `GenerationRecord(*, provider, transport, model, request_id=None, temperature=None, top_p=None, max_tokens=None, stream=None, step_kind=None, raw_text=None, selected_tokens=..., selected_logprobs=None, top_logprobs=None, structured_blocks=..., metadata=...)`
- Purpose: provider-normalized record consumed by `Analyzer`
- Key fields: `raw_text`, `selected_tokens`, `selected_logprobs`, `top_logprobs`, `structured_blocks`, `metadata`
- Returns / output: usually produced by adapters, not by hand
- Caveats: request metadata drives canonical-vs-realized mode selection and some capability checks

### `TolerancePreset` (`Stable`)

- Import: `from agentuq import TolerancePreset`
- Purpose: preset enum for event sensitivity
- Values: `strict`, `balanced`, `lenient`
- Returns / output: accepted by `UQConfig.tolerance` and `resolve_thresholds(...)`
- Caveats: use presets before reaching for raw numeric threshold edits; see [Tolerance](../concepts/tolerance.md)

### Rendering helpers (`Stable`)

- Import: `from agentuq import render_result, render_result_rich, print_result_rich`
- Signatures:
  `render_result(result: UQResult, verbosity='summary', show_thresholds='triggered') -> str`
  `render_result_rich(result: UQResult, verbosity='summary', show_thresholds='triggered') -> Any`
  `print_result_rich(result: UQResult, console=None, verbosity='summary', show_thresholds='triggered') -> None`
- Purpose: render `UQResult` into plain-text or Rich-compatible output
- Key parameters: `verbosity` in `compact | summary | debug`, `show_thresholds` in `none | triggered | all`
- Returns / output: plain text string or Rich output objects / console printing
- Caveats: Rich rendering requires the optional `rich` dependency; plain-text output is the canonical rendering contract

### `resolve_thresholds` (`Stable`)

- Import: `from agentuq import resolve_thresholds`
- Signature: `resolve_thresholds(tolerance: TolerancePreset, overrides: ThresholdConfig | None = None) -> ThresholdConfig`
- Purpose: compute the merged threshold table for a tolerance preset plus overrides
- Key parameters: `tolerance`, optional `overrides`
- Returns / output: resolved `ThresholdConfig`
- Caveats: useful for inspection and debugging; most callers should prefer presets over raw threshold tuning

### `PolicyEngine` (`Advanced`)

- Import: `from agentuq import PolicyEngine`
- Signature: `PolicyEngine(config: UQConfig)`
- Purpose: direct access to policy mapping logic
- Key call: `decide(result: UQResult) -> Decision`
- Returns / output: `Decision` object derived from segment events and policy configuration
- Caveats: normal usage should rely on `Analyzer` to populate `result.decision`; see [Policies](../concepts/policies.md)

