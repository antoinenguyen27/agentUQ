---
title: Records and Results
description: Data models returned by adapters and the analyzer, including results, segments, events, and capability reporting.
slug: /reference/results-and-records
sidebar_position: 12
---

# Records and Results

## `GenerationRecord` (`Stable`)

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

## `CapabilityReport` (`Stable`)

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

## `UQResult` (`Stable`)

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

- Links: [Reading results](../concepts/reading_results.md)

## `Decision` (`Stable`)

- Import: `from agentuq import Decision` or `from agentuq.schemas import Decision`
- Signature: `Decision(*, action, rationale, segment_actions=..., events=..., metadata=...)`

| Field | Type | Notes |
| --- | --- | --- |
| `action` | `Action` | Step-level recommended action. |
| `rationale` | `str` | Plain-English explanation of why the action was chosen. |
| `segment_actions` | `dict[str, Action]` | Per-segment action map keyed by segment ID. |
| `events` | `list[Event]` | Events considered by policy. |
| `metadata` | `dict[str, Any]` | Extra policy metadata when present. |

## `Event` (`Stable`)

- Import: `from agentuq.schemas import Event`
- Signature: `Event(*, type, severity, segment_id=None, message, details=...)`

| Field | Type | Notes |
| --- | --- | --- |
| `type` | `str` | Event code such as `LOW_MARGIN_CLUSTER` or `SCHEMA_INVALID`. |
| `severity` | `EventSeverity` | `info`, `warn`, `high`, or `critical`. |
| `segment_id` | `str \| None` | Associated segment when applicable. |
| `message` | `str` | Human-readable explanation. |
| `details` | `dict[str, Any]` | Threshold comparisons and other structured details. |

## `SegmentResult` (`Stable`)

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

## `SegmentMetrics` (`Stable`)

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

- Links: [Reading results](../concepts/reading_results.md)

## `StructuredBlock` (`Stable`)

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

## `TopToken` (`Stable`)

- Import: `from agentuq.schemas import TopToken`
- Signature: `TopToken(*, token, logprob)`

| Field | Type | Notes |
| --- | --- | --- |
| `token` | `str` | Candidate token text. |
| `logprob` | `float` | Candidate token logprob. |

## User-visible enums (`Stable`)

### `PrimaryScoreType`

- Import: `from agentuq.schemas.results import PrimaryScoreType`
- Values: `g_nll`, `realized_nll`
- Purpose: identifies whether `primary_score` is canonical greedy NLL or realized-path NLL

### `EventSeverity`

- Import: `from agentuq.schemas.results import EventSeverity`
- Values: `info`, `warn`, `high`, or `critical`
- Purpose: event severity levels used in `Event.severity`

### `CapabilityLevel`

- Import: `from agentuq.schemas.records import CapabilityLevel`
- Values: `full`, `selected_only`, `none`
- Purpose: computed capability tier exposed on `CapabilityReport.level` and `UQResult.capability_level`

