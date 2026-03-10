# API Reference

AgentUQ's canonical API reference lives on this page. It is a curated reference, but it is audited against the implemented codebase rather than treated as a lightweight overview.

## How to read this page

- `Stable`: intended long-term public surface for normal library use
- `Advanced`: real supported surface, but narrower, more caveat-heavy, or less central to the default integration loop

## Not covered here

This page does not document internal implementation modules such as segmentation internals, metric helpers, adapter base protocols, rendering display internals, or low-level utility helpers. It focuses on public entrypoints and user-visible models.

## Coverage inventory

This page is audited against these implemented sources of truth:

- `agentuq.__all__`: `Action`, `Analyzer`, `CapabilityReport`, `Decision`, `GenerationRecord`, `PolicyEngine`, `TolerancePreset`, `UQConfig`, `UQResult`, `print_result_rich`, `render_result`, `render_result_rich`, `resolve_thresholds`
- `agentuq.adapters.__all__`: `FireworksAdapter`, `GeminiAdapter`, `LiteLLMAdapter`, `OpenAIAgentsAdapter`, `OpenAIChatAdapter`, `OpenAIResponsesAdapter`, `OpenRouterAdapter`, `TogetherAdapter`, `model_settings_with_logprobs`, `probe_litellm_capability`, `probe_openrouter_model`
- `agentuq.integrations.__all__`: `UQMiddleware`, `analyze_after_model_call`, `enrich_graph_state`, `guard_before_tool_execution`, `should_interrupt_before_tool`
- `agentuq.schemas.__all__`: `Action`, `CapabilityReport`, `Decision`, `Event`, `GenerationRecord`, `SegmentResult`, `StructuredBlock`, `TolerancePreset`, `TopToken`, `UQConfig`, `UQResult`, `resolve_thresholds`
- additional audited public surfaces: `agentuq.request_params.request_params`, `agentuq.adapters.openai_agents.latest_raw_response`, and public error types in `agentuq.schemas.errors`

Use [Reading results](reading_results.md), [Policies](policies.md), [Tolerance](tolerance.md), [Canonical vs realized](canonical_vs_realized.md), [Troubleshooting](troubleshooting.md), and [Provider and framework capabilities](provider_capabilities.md) for the deeper behavioral and conceptual explanation behind these interfaces.

## Stable Root API

### `Analyzer` (`Stable`)

- Import: `from agentuq import Analyzer`
- Signature: `Analyzer(config: UQConfig | None = None)`
- Purpose: shared analysis engine for scoring, segmentation, event emission, capability enforcement, and decision generation
- Key call: `analyze_step(record: GenerationRecord, capability: CapabilityReport | None = None) -> UQResult`
- Returns / output: `analyze_step(...)` returns a fully populated `UQResult`, including `result.decision`
- Caveats: mode selection and fail-loud behavior depend on `UQConfig`; see [Canonical vs realized](canonical_vs_realized.md) and [Troubleshooting](troubleshooting.md)

### `UQConfig` (`Stable`)

- Import: `from agentuq import UQConfig`
- Signature: `UQConfig(*, mode='auto', policy=PolicyPreset.BALANCED, tolerance=TolerancePreset.BALANCED, thresholds=..., segmentation=..., integrations=..., capability=..., custom_rules=..., deterministic=None, canonical_temperature_max=0.0, canonical_top_p_min=1.0, retries_allowed=1)`
- Purpose: top-level configuration model for analysis mode, policy, thresholds, segmentation, and capability behavior
- Key fields: `mode`, `policy`, `tolerance`, `thresholds`, `capability`, `custom_rules`
- Returns / output: plain Pydantic model consumed by `Analyzer` and integration helpers
- Caveats: `deterministic`, `canonical_temperature_max`, and `canonical_top_p_min` are advanced override-style fields; see [Config Models](#config-models)

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
- Caveats: `whole_response_score` is not the decision source of truth; see [Reading results](reading_results.md)

### `Decision` (`Stable`)

- Import: `from agentuq import Decision`
- Signature: `Decision(*, action, rationale, segment_actions=..., events=..., metadata=...)`
- Purpose: policy output attached to `result.decision`
- Key fields: `action`, `rationale`, `segment_actions`, `events`
- Returns / output: step-level action plus per-segment action mapping
- Caveats: this is the primary branching object for runtime routing; see [Acting on decisions](acting_on_decisions.md)

### `CapabilityReport` (`Stable`)

- Import: `from agentuq import CapabilityReport`
- Signature: `CapabilityReport(*, selected_token_logprobs=False, topk_logprobs=False, topk_k=None, structured_blocks=False, function_call_structure=False, provider_declared_support=None, request_attempted_logprobs=False, request_attempted_topk=None, degraded_reason=None)`
- Purpose: observed capability summary for the analyzed step
- Key fields: `selected_token_logprobs`, `topk_logprobs`, `topk_k`, `degraded_reason`
- Returns / output: surfaced directly on `UQResult.capability_report`
- Caveats: capability is determined from actual observed behavior, not just the request intent; see [Provider and framework capabilities](provider_capabilities.md)

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
- Caveats: use presets before reaching for raw numeric threshold edits; see [Tolerance](tolerance.md)

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
- Caveats: normal usage should rely on `Analyzer` to populate `result.decision`; see [Policies](policies.md)

## Config Models

### `UQConfig` (`Stable`)

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

- Links: [Policies](policies.md), [Tolerance](tolerance.md), [Canonical vs realized](canonical_vs_realized.md)

### `CapabilityConfig` (`Stable`)

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

### `ThresholdConfig` (`Stable`)

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

### `SegmentationConfig` (`Stable`)

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

- Caveats: segmentation is intentionally conservative; see [Segmentation](segmentation.md)

### `IntegrationConfig` (`Advanced`)

- Import: `from agentuq.schemas.config import IntegrationConfig`
- Signature: `IntegrationConfig(*, strict_openrouter_require_parameters=True, annotate_framework_metadata=True)`
- Purpose: integration-oriented configuration surface exposed on `UQConfig`

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `strict_openrouter_require_parameters` | `bool` | `True` | Present on the config model for integration-facing policy, not a first-line direct-provider tuning knob. |
| `annotate_framework_metadata` | `bool` | `True` | Present on the config model for framework metadata behavior; current quickstarts still route explicitly through integration helpers. |

### `CustomRule` (`Stable`)

- Import: `from agentuq.schemas.config import CustomRule`
- Signature: `CustomRule(*, when: dict[str, Any], then: str)`
- Purpose: declarative action override evaluated before built-in policy logic

| Field | Type | Notes |
| --- | --- | --- |
| `when` | `dict[str, Any]` | Supported keys in the current implementation are `segment_kind`, `segment_priority`, `events_any`, and `severity_at_least`. |
| `then` | `str` | Action value to return when the rule matches. |

- Links: [Policies](policies.md)

## Records And Results

### `GenerationRecord` (`Stable`)

- Import: `from agentuq import GenerationRecord` or `from agentuq.schemas import GenerationRecord`
- Signature:

```python
GenerationRecord(
    *,
    provider,
    transport,
    model,
    request_id=None,
    temperature=None,
    top_p=None,
    max_tokens=None,
    stream=None,
    step_kind=None,
    raw_text=None,
    selected_tokens=list[str](),
    selected_logprobs=None,
    top_logprobs=None,
    structured_blocks=list[StructuredBlock](),
    metadata=dict[str, Any](),
)
```

- Purpose: normalized provider/framework payload for one step

| Field | Type | Notes |
| --- | --- | --- |
| `provider` | `str` | Normalized provider label such as `openai`, `openrouter`, `gemini`, or `together`. |
| `transport` | `str` | Surface label for the capture path. |
| `model` | `str` | Model name as returned or inferred. |
| `request_id` | `str \| None` | Upstream request identifier when available. |
| `temperature` | `float \| None` | Captured decoding metadata used in mode selection. |
| `top_p` | `float \| None` | Captured decoding metadata used in mode selection. |
| `max_tokens` | `int \| None` | Optional max token/request budget metadata. |
| `stream` | `bool \| None` | Whether the upstream call was streamed. |
| `step_kind` | `str \| None` | Optional workflow-specific step label. |
| `raw_text` | `str \| None` | Full emitted text when available. |
| `selected_tokens` | `list[str]` | Emitted tokens in order. |
| `selected_logprobs` | `list[float] \| None` | Selected-token logprobs aligned to `selected_tokens`. |
| `top_logprobs` | `list[list[TopToken]] \| None` | Top-k token alternatives aligned to `selected_tokens`. |
| `structured_blocks` | `list[StructuredBlock]` | Structural blocks such as output text, JSON, or tool calls. |
| `metadata` | `dict[str, Any]` | Request/adapter metadata such as logprob request intent and deterministic hints. |

### `CapabilityReport` (`Stable`)

- Import: `from agentuq import CapabilityReport` or `from agentuq.schemas import CapabilityReport`
- Signature:

```python
CapabilityReport(
    *,
    selected_token_logprobs=False,
    topk_logprobs=False,
    topk_k=None,
    structured_blocks=False,
    function_call_structure=False,
    provider_declared_support=None,
    request_attempted_logprobs=False,
    request_attempted_topk=None,
    degraded_reason=None,
)
```

- Purpose: observed capability of the current step

| Field | Type | Notes |
| --- | --- | --- |
| `selected_token_logprobs` | `bool` | Whether selected-token logprobs were actually available. |
| `topk_logprobs` | `bool` | Whether top-k logprobs were actually available. |
| `topk_k` | `int \| None` | Returned top-k width when known. |
| `structured_blocks` | `bool` | Whether structured blocks were observed. |
| `function_call_structure` | `bool` | Whether function/tool call structure was present. |
| `provider_declared_support` | `bool \| None` | Optional declared support from a probe or adapter hint. |
| `request_attempted_logprobs` | `bool` | Whether the request attempted to ask for logprobs. |
| `request_attempted_topk` | `int \| None` | Requested top-k width when known. |
| `degraded_reason` | `str \| None` | Human-readable degradation reason. |

- Output behavior: computed property `level` returns a `CapabilityLevel`

### `UQResult` (`Stable`)

- Import: `from agentuq import UQResult` or `from agentuq.schemas import UQResult`
- Signature:

```python
UQResult(
    *,
    primary_score,
    primary_score_type,
    mode,
    capability_level,
    capability_report,
    segments,
    events,
    action,
    diagnostics=Diagnostics(),
    decision=None,
    resolved_thresholds=None,
)
```

- Purpose: top-level analysis result

| Field | Type | Notes |
| --- | --- | --- |
| `primary_score` | `float` | Whole-step score for the selected probability object. |
| `primary_score_type` | `PrimaryScoreType` | `g_nll` or `realized_nll`. |
| `mode` | `str` | Resolved analysis mode. |
| `capability_level` | `CapabilityLevel` | `full`, `selected_only`, or `none`. |
| `capability_report` | `CapabilityReport` | Full capability details. |
| `segments` | `list[SegmentResult]` | Segmented analysis units. |
| `events` | `list[Event]` | Top-level and segment-derived events. |
| `action` | `Action` | Overall recommended action. |
| `diagnostics` | `Diagnostics` | Warnings, mode reason, and token count. |
| `decision` | `Decision \| None` | Policy output, normally populated by `Analyzer`. |
| `resolved_thresholds` | `ThresholdConfig \| None` | Fully merged thresholds used for evaluation. |

- Key methods:
  `pretty(...) -> str`
  `rich_renderable(...) -> Any`
  `rich_console_render(...) -> None`

- Links: [Reading results](reading_results.md)

### `Decision` (`Stable`)

- Import: `from agentuq import Decision` or `from agentuq.schemas import Decision`
- Signature: `Decision(*, action, rationale, segment_actions=..., events=..., metadata=...)`

| Field | Type | Notes |
| --- | --- | --- |
| `action` | `Action` | Step-level recommended action. |
| `rationale` | `str` | Plain-English explanation of why the action was chosen. |
| `segment_actions` | `dict[str, Action]` | Per-segment action map keyed by segment ID. |
| `events` | `list[Event]` | Events considered by policy. |
| `metadata` | `dict[str, Any]` | Extra policy metadata when present. |

### `Event` (`Stable`)

- Import: `from agentuq.schemas import Event`
- Signature: `Event(*, type, severity, segment_id=None, message, details=...)`

| Field | Type | Notes |
| --- | --- | --- |
| `type` | `str` | Event code such as `LOW_MARGIN_CLUSTER` or `SCHEMA_INVALID`. |
| `severity` | `EventSeverity` | `info`, `warn`, `high`, or `critical`. |
| `segment_id` | `str \| None` | Associated segment when applicable. |
| `message` | `str` | Human-readable explanation. |
| `details` | `dict[str, Any]` | Threshold comparisons and other structured details. |

### `SegmentResult` (`Stable`)

- Import: `from agentuq.schemas import SegmentResult`
- Signature: `SegmentResult(*, id, kind, priority, text, token_span, primary_score, metrics, events=..., recommended_action=Action.CONTINUE, metadata=...)`

| Field | Type | Notes |
| --- | --- | --- |
| `id` | `str` | Segment identifier used in `segment_actions`. |
| `kind` | `str` | Segment kind such as `sql_clause` or `final_answer_text`. |
| `priority` | `str` | Priority bucket such as `critical_action` or `informational`. |
| `text` | `str` | Segment text preview / content. |
| `token_span` | `tuple[int, int]` | Token span in the emitted sequence. |
| `primary_score` | `float` | Segment-level score over the selected probability object. |
| `metrics` | `SegmentMetrics` | Grouped numeric diagnostics. |
| `events` | `list[Event]` | Triggered events for the segment. |
| `recommended_action` | `Action` | Segment-level action recommendation. |
| `metadata` | `dict[str, Any]` | Segment-specific metadata such as tool name or JSON path. |

### `SegmentMetrics` (`Stable`)

- Import: `from agentuq.schemas.results import SegmentMetrics`
- Signature: `SegmentMetrics(*, token_count=0, nll=0.0, avg_surprise=0.0, max_surprise=0.0, p95_surprise=0.0, tail_surprise_mean=0.0, mean_margin_log=None, min_margin_log=None, low_margin_rate=None, low_margin_run_max=None, mean_entropy_hat=None, max_entropy_hat=None, high_entropy_rate=None, high_entropy_run_max=None, off_top1_rate=None, off_topk_rate=None, off_top1_run_max=None, any_off_topk=False)`

| Field | Type | Notes |
| --- | --- | --- |
| `token_count` | `int` | Number of tokens in the segment. |
| `nll` | `float` | Total negative log-likelihood for the segment. |
| `avg_surprise` | `float` | Mean token surprise. |
| `max_surprise` | `float` | Largest single-token surprise. |
| `p95_surprise` | `float` | 95th percentile surprise. |
| `tail_surprise_mean` | `float` | Mean surprise over the riskiest tail. |
| `mean_margin_log` | `float \| None` | Mean log-margin between emitted token and nearest alternative. |
| `min_margin_log` | `float \| None` | Smallest observed log-margin. |
| `low_margin_rate` | `float \| None` | Fraction of low-margin tokens. |
| `low_margin_run_max` | `int \| None` | Longest contiguous low-margin run. |
| `mean_entropy_hat` | `float \| None` | Mean approximate top-k entropy. |
| `max_entropy_hat` | `float \| None` | Maximum approximate top-k entropy. |
| `high_entropy_rate` | `float \| None` | Fraction of high-entropy tokens. |
| `high_entropy_run_max` | `int \| None` | Longest contiguous high-entropy run. |
| `off_top1_rate` | `float \| None` | Fraction of tokens that diverged from local top-1. |
| `off_topk_rate` | `float \| None` | Fraction of emitted tokens missing from returned top-k. |
| `off_top1_run_max` | `int \| None` | Longest contiguous off-top1 run. |
| `any_off_topk` | `bool` | Whether any emitted token fell outside returned top-k. |

- Links: [Reading results](reading_results.md)

### `StructuredBlock` (`Stable`)

- Import: `from agentuq.schemas import StructuredBlock`
- Signature: `StructuredBlock(*, type, text=None, name=None, arguments=None, format=None, char_start=None, char_end=None, metadata=...)`

| Field | Type | Notes |
| --- | --- | --- |
| `type` | `str` | Block type such as `output_text`, `function_call`, `tool_call`, `json`, or `structured_output`. |
| `text` | `str \| None` | Primary text content when present. |
| `name` | `str \| None` | Tool or function name when present. |
| `arguments` | `str \| None` | Tool argument payload when present. |
| `format` | `str \| None` | Optional structured format label. |
| `char_start` | `int \| None` | Start char offset in `raw_text` when grounded. |
| `char_end` | `int \| None` | End char offset in `raw_text` when grounded. |
| `metadata` | `dict[str, Any]` | Adapter-specific metadata such as `token_grounded`. |

### `TopToken` (`Stable`)

- Import: `from agentuq.schemas import TopToken`
- Signature: `TopToken(*, token, logprob)`

| Field | Type | Notes |
| --- | --- | --- |
| `token` | `str` | Candidate token text. |
| `logprob` | `float` | Candidate token logprob. |

### User-visible enums (`Stable`)

#### `PrimaryScoreType`

- Import: `from agentuq.schemas.results import PrimaryScoreType`
- Values: `g_nll`, `realized_nll`
- Purpose: identifies whether `primary_score` is canonical greedy NLL or realized-path NLL

#### `EventSeverity`

- Import: `from agentuq.schemas.results import EventSeverity`
- Values: `info`, `warn`, `high`, `critical`
- Purpose: event severity levels used in `Event.severity`

#### `CapabilityLevel`

- Import: `from agentuq.schemas.records import CapabilityLevel`
- Values: `full`, `selected_only`, `none`
- Purpose: computed capability tier exposed on `CapabilityReport.level` and `UQResult.capability_level`

## Adapters

All adapter classes are re-exported from `agentuq.adapters`.

### `OpenAIResponsesAdapter` (`Stable`)

- Import: `from agentuq.adapters import OpenAIResponsesAdapter`
- Signature:
  `OpenAIResponsesAdapter()`
  `capture(response, request_meta=None) -> GenerationRecord`
  `capability_report(response, request_meta=None) -> CapabilityReport`
- Purpose: normalize OpenAI Responses API payloads into `GenerationRecord`
- Required / expected input shape: Responses-style objects or dict-like payloads with `output[]`, `message` items, and requested `message.output_text.logprobs`
- Returns / output: normalized text blocks, tokens, logprobs, and structural function/tool call blocks
- Caveat: tool/function call items are captured structurally; token-grounded scoring is limited to message text
- Links: [OpenAI quickstart](../quickstarts/openai.md)

### `OpenAIChatAdapter` (`Stable`)

- Import: `from agentuq.adapters import OpenAIChatAdapter`
- Signature:
  `OpenAIChatAdapter()`
  `capture(response, request_meta=None) -> GenerationRecord`
  `capability_report(response, request_meta=None) -> CapabilityReport`
- Purpose: normalize OpenAI Chat Completions payloads
- Required / expected input shape: chat completion responses with message content and `choices[0].logprobs.content` when requested
- Returns / output: flattened message text, logprob-aligned tokens, and structural tool call metadata
- Caveat: OpenAI-family `tool_calls` are structural only unless the upstream surface provides explicit grounding
- Links: [OpenAI quickstart](../quickstarts/openai.md)

### `OpenRouterAdapter` (`Stable`)

- Import: `from agentuq.adapters import OpenRouterAdapter`
- Signature:
  `OpenRouterAdapter()`
  `capture(response, request_meta=None) -> GenerationRecord`
  `capability_report(response, request_meta=None) -> CapabilityReport`
- Purpose: normalize OpenRouter's OpenAI-compatible chat payloads while preserving routed-capability reporting
- Required / expected input shape: OpenAI-compatible chat responses plus request metadata describing requested logprob parameters
- Returns / output: `GenerationRecord` and capability reporting that reflects actual returned capability
- Caveat: a request may be accepted even when the routed backend does not return the requested token details; prefer `provider.require_parameters=true`
- Links: [OpenRouter quickstart](../quickstarts/openrouter.md), [Provider and framework capabilities](provider_capabilities.md)

### `LiteLLMAdapter` (`Stable`)

- Import: `from agentuq.adapters import LiteLLMAdapter`
- Signature:
  `LiteLLMAdapter()`
  `capture(response, request_meta=None) -> GenerationRecord`
  `capability_report(response, request_meta=None) -> CapabilityReport`
- Purpose: normalize LiteLLM responses while preserving upstream capability signals
- Required / expected input shape: `litellm.completion(...)` style responses or dict-like equivalents
- Returns / output: `GenerationRecord`, capability report, and optional convenience `from_response(...)` classmethod behavior
- Caveat: silent parameter dropping can hide unsupported logprob requests; prefer `drop_params=False`
- Links: [LiteLLM quickstart](../quickstarts/litellm.md)

### `GeminiAdapter` (`Stable`)

- Import: `from agentuq.adapters import GeminiAdapter`
- Signature:
  `GeminiAdapter()`
  `capture(response, request_meta=None) -> GenerationRecord`
  `capability_report(response, request_meta=None) -> CapabilityReport`
- Purpose: normalize Gemini `generate_content` responses
- Required / expected input shape: payloads with `responseLogprobs`, chosen candidates, and optional top candidates when requested
- Returns / output: selected tokens, selected-token logprobs, top candidates, and normalized text blocks
- Caveat: Gemini uses `topP` rather than `top_p` in request metadata, and no chosen-token logprobs means no top-k diagnostics
- Links: [Gemini quickstart](../quickstarts/gemini.md)

### `FireworksAdapter` (`Stable`)

- Import: `from agentuq.adapters import FireworksAdapter`
- Signature:
  `FireworksAdapter()`
  `capture(response, request_meta=None) -> GenerationRecord`
  `capability_report(response, request_meta=None) -> CapabilityReport`
- Purpose: normalize Fireworks chat completions
- Required / expected input shape: OpenAI-compatible chat payloads or older Fireworks logprob variants
- Returns / output: normalized record and capability report
- Caveat: prefers `choices[0].logprobs.content`, but falls back to older token-array variants when needed
- Links: [Fireworks quickstart](../quickstarts/fireworks.md)

### `TogetherAdapter` (`Stable`)

- Import: `from agentuq.adapters import TogetherAdapter`
- Signature:
  `TogetherAdapter()`
  `capture(response, request_meta=None) -> GenerationRecord`
  `capability_report(response, request_meta=None) -> CapabilityReport`
- Purpose: normalize Together chat completions
- Required / expected input shape: `choices[0].logprobs` token arrays and top-logprob maps
- Returns / output: normalized text, tokens, logprobs, and capability report
- Caveat: Together requests `logprobs=k` rather than separate `top_logprobs`
- Links: [Together quickstart](../quickstarts/together.md)

### `OpenAIAgentsAdapter` (`Stable`)

- Import: `from agentuq.adapters import OpenAIAgentsAdapter`
- Signature:
  `OpenAIAgentsAdapter()`
  `capture(response, request_meta=None) -> GenerationRecord`
  `capability_report(response, request_meta=None) -> CapabilityReport`
- Purpose: adapt OpenAI Agents SDK raw Responses objects through the Responses normalization path
- Required / expected input shape: raw Responses payloads exposed by the Agents SDK, not the higher-level run result wrapper itself
- Returns / output: same normalized record/capability shape as the Responses adapter
- Caveat: this helper assumes the SDK still exposes raw Responses payloads for analysis
- Links: [OpenAI Agents quickstart](../quickstarts/openai_agents.md)

### `model_settings_with_logprobs` (`Advanced`)

- Import: `from agentuq.adapters import model_settings_with_logprobs`
- Signature: `model_settings_with_logprobs(*, top_logprobs=5, include_output_text_logprobs=True, **kwargs) -> dict[str, Any]`
- Purpose: produce an Agents SDK `ModelSettings` kwargs dict that requests output-text logprobs
- Key parameters: `top_logprobs`, `include_output_text_logprobs`, plus passthrough keyword args such as `temperature` and `top_p`
- Returns / output: plain dictionary suitable for `ModelSettings(**settings)`
- Caveat: this helper is specific to the OpenAI Agents SDK `ModelSettings` surface, not raw `OpenAI().responses.create(...)`

### `latest_raw_response` (`Advanced`)

- Import: `from agentuq.adapters.openai_agents import latest_raw_response`
- Signature: `latest_raw_response(run_result) -> Any`
- Purpose: extract the latest raw Responses object from an OpenAI Agents SDK run result
- Required / expected input shape: run result object exposing `raw_responses`
- Returns / output: the last raw Responses payload
- Caveat: raises `ValueError` if `raw_responses` is unavailable

### `probe_openrouter_model` (`Advanced`)

- Import: `from agentuq.adapters import probe_openrouter_model`
- Signature: `probe_openrouter_model(model: str, supported_parameters: list[str] | None = None) -> dict[str, Any]`
- Purpose: build a declared-capability hint for OpenRouter model routing
- Key parameters: `model`, optional `supported_parameters`
- Returns / output: plain dictionary describing declared parameter support
- Caveat: this is a caller-supplied capability hint, not proof that the routed backend will actually return token details

### `probe_litellm_capability` (`Advanced`)

- Import: `from agentuq.adapters import probe_litellm_capability`
- Signature: `probe_litellm_capability(model: str, provider: str | None = None, supported_openai_params: list[str] | None = None) -> dict[str, Any]`
- Purpose: build a declared-capability hint for LiteLLM routing
- Key parameters: `model`, optional `provider`, optional `supported_openai_params`
- Returns / output: plain dictionary describing declared support
- Caveat: this helper reflects caller-provided support metadata; the actual returned payload still determines runtime capability

## Integrations

All exported integration helpers are re-exported from `agentuq.integrations`.

### `UQMiddleware` (`Stable`)

- Import: `from agentuq.integrations import UQMiddleware`
- Signature:
  `UQMiddleware(model, uq: UQConfig | None = None)`
  `invoke(*args, **kwargs) -> Any`
  `ainvoke(*args, **kwargs) -> Any`
- Purpose: wrap a LangChain-style model and attach `uq_result` to `response.response_metadata`
- Intended insertion point: immediately around the model call in LangChain-style workflows
- Returns / output: original framework response with serialized `uq_result` stored in response metadata
- Caveat: this helper depends on what the framework preserved in `response_metadata`; see [Provider and framework capabilities](provider_capabilities.md)
- Links: [LangChain quickstart](../quickstarts/langchain.md)

### `analyze_after_model_call` (`Advanced`)

- Import: `from agentuq.integrations import analyze_after_model_call`
- Signature: `analyze_after_model_call(response, config: UQConfig, request_meta: dict | None = None, *, model=None) -> UQResult`
- Purpose: normalize a framework response, analyze it, and attach serialized `uq_result` back onto the response metadata
- Intended insertion point: immediately after a model node or framework model invocation
- Returns / output: `UQResult`
- Caveat: request metadata may be inferred from the model and response metadata when not provided explicitly

### `guard_before_tool_execution` (`Advanced`)

- Import: `from agentuq.integrations import guard_before_tool_execution`
- Signature: `guard_before_tool_execution(tool_name: str, uq_result: UQResult) -> Action`
- Purpose: map a tool name to the segment action for an explicitly grounded tool segment
- Intended insertion point: just before a tool call in frameworks that already hold a `UQResult`
- Returns / output: `Action`
- Caveat: returns `continue` when there is no grounded tool segment for the named tool

### `enrich_graph_state` (`Stable`)

- Import: `from agentuq.integrations import enrich_graph_state`
- Signature: `enrich_graph_state(state: dict[str, Any], response, config: UQConfig, request_meta: dict | None = None) -> dict[str, Any]`
- Purpose: analyze a framework response and store serialized `uq_result` on copied graph state
- Intended insertion point: immediately after a LangGraph model node
- Returns / output: new state dict with `uq_result`
- Caveat: this helper does not itself block tool execution; callers still branch on the stored result or use the narrower boolean helper
- Links: [LangGraph quickstart](../quickstarts/langgraph.md)

### `should_interrupt_before_tool` (`Stable`)

- Import: `from agentuq.integrations import should_interrupt_before_tool`
- Signature: `should_interrupt_before_tool(tool_name: str, state: dict[str, Any]) -> bool`
- Purpose: narrow boolean guard for tool execution from graph state
- Intended insertion point: before a tool node when `uq_result` is already stored on state
- Returns / output: `True` for grounded tool-facing actions that should interrupt, otherwise `False`
- Caveat: this helper is intentionally narrow and depends on explicit grounded tool segments; most OpenAI-compatible tool flows should branch on `result.decision.action` instead
- Links: [LangGraph quickstart](../quickstarts/langgraph.md), [Acting on decisions](acting_on_decisions.md)

## Advanced Utilities And Errors

### `request_params` (`Advanced`)

- Import: `from agentuq.request_params import request_params`
- Signature: `request_params(provider: str, mode: str = "auto", topk: int = 5, transport: str | None = None) -> dict`
- Purpose: convenience helper for provider-specific request parameter defaults
- Key parameters: `provider` in `openai | openrouter | litellm | gemini | fireworks | together`, optional OpenAI `transport` in `responses | chat`, `mode` in `auto | canonical | realized`, `topk`
- Returns / output: provider-specific request metadata dictionary
- Caveat: this helper sets request intent, not actual provider capability; unsupported providers or invalid OpenAI transport values raise `ValueError`

### Error base class (`Advanced`)

- Import: `from agentuq.schemas.errors import AgentUQError`
- Purpose: base exception carrying actionable metadata
- Structured fields: `message`, `provider`, `transport`, `model`, `requested_params`, `observed_capability`, `remediation`
- Output behavior: stringifies into a joined, operator-readable error message

### Public error types (`Advanced`)

All public error types inherit from `AgentUQError` and live in `agentuq.schemas.errors`.

| Error | When it is used |
| --- | --- |
| `LogprobsNotRequestedError` | Logprobs were required but not requested. |
| `SelectedTokenLogprobsUnavailableError` | Selected-token logprobs were requested but not returned. |
| `TopKLogprobsUnavailableError` | Top-k logprobs were required but unavailable. |
| `ProviderDroppedRequestedParameterError` | Requested logprob parameters appear to have been dropped by the provider or route. |
| `ModelCapabilityUnknownProbeRequired` | Capability probing is required before making a stronger assumption. |
| `UnsupportedForCanonicalModeError` | Canonical mode was requested but strict greedy conditions were not established. |
| `CapabilityProbeFailedError` | Capability probe flow failed. |

- Caveat: these types are most useful in fail-loud or integration-heavy deployments; see [Troubleshooting](troubleshooting.md)
