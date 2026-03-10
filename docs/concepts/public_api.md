# Public API

AgentUQ is intentionally small at the public surface.

Most users only need four pieces:

- `UQConfig` to choose mode, policy, and tolerance
- an adapter to capture provider responses
- `Analyzer` to produce a `UQResult`
- `result.decision` to drive runtime behavior

## Recommended entry points

From the package root:

- `Analyzer`
- `UQConfig`
- `UQResult`
- `Decision`
- `CapabilityReport`
- `GenerationRecord`
- `render_result`, `render_result_rich`, `print_result_rich`
- `resolve_thresholds`

These are the public entry points re-exported from `uq_runtime`.

Provider-specific adapters and some enums live in submodules.

Common examples:

- `uq_runtime.adapters.openai_responses.OpenAIResponsesAdapter`
- `uq_runtime.adapters.openai_chat.OpenAIChatAdapter`
- `uq_runtime.schemas.results.Action`

## Core flow

The main workflow is:

```python
from uq_runtime import Analyzer, UQConfig
from uq_runtime.adapters.openai_responses import OpenAIResponsesAdapter

adapter = OpenAIResponsesAdapter()
analyzer = Analyzer(UQConfig(policy="balanced", tolerance="strict"))

record = adapter.capture(response, request_meta)
capability = adapter.capability_report(response, request_meta)
result = analyzer.analyze_step(record, capability)
decision = result.decision
```

## Public objects

### `UQConfig`

Primary configuration object.

Most important fields:

- `mode`: `auto`, `canonical`, or `realized`
- `policy`: default action behavior after events are emitted
- `tolerance`: event sensitivity preset
- `thresholds`: optional numeric overrides
- `custom_rules`: optional declarative action overrides
- `capability`: fail-loud and degraded-mode behavior

For most integrations, start with:

```python
UQConfig(policy="balanced", tolerance="strict")
```

Use [Policies](policies.md) and [Tolerance](tolerance.md) to tune from there.

### `GenerationRecord`

Provider-normalized record of one model step.

Key contents:

- emitted text
- selected tokens and selected-token logprobs
- top-k logprobs when available
- structured blocks such as output text or tool-call metadata
- request metadata such as temperature, top-p, and deterministic hints

Most users do not construct this manually. Adapters do it for you.

### `CapabilityReport`

Observed runtime capability for the step.

Important fields include:

- capability level: `full`, `selected_only`, or `none`
- whether token logprobs and top-k were actually returned
- whether structured blocks were observed
- degraded reason when the response did not match the requested capability

See [Capability tiers](capability_tiers.md).

### `UQResult`

Primary analysis result.

Important fields:

- `primary_score`
- `primary_score_type`
- `mode`
- `capability_level`
- `segments`
- `events`
- `action`
- `decision`
- `resolved_thresholds`
- `diagnostics`

This is the object you inspect, log, render, and route on.

### `Decision`

Policy output attached to `result.decision`.

Important fields:

- `action`: overall recommended action for the step
- `rationale`: plain-English explanation of why that action was chosen
- `segment_actions`: per-segment action map
- `events`: top-level events attached to the step

This is the object you branch on in your runtime loop.

### `Action`

Action enum used by `Decision.action`, `Decision.segment_actions`, and `segment.recommended_action`.

Import path:

```python
from uq_runtime.schemas.results import Action
```

## Rendering helpers

`UQResult` includes convenience methods:

- `result.pretty(...)`
- `result.rich_renderable(...)`
- `result.rich_console_render(...)`

These are for human-readable diagnostics. They do not replace the structured fields on `UQResult`.

See [Reading results](reading_results.md).

## Adapter path

The canonical direct-provider workflow is explicit:

- choose the adapter
- capture manually
- call `Analyzer` yourself
- decide how to store or route the result

## Advanced public surface

### `resolve_thresholds`

Useful when you want to inspect the fully merged threshold table for a preset plus overrides.

### `PolicyEngine`

Public, but usually not the first thing to reach for.

Most users should let `Analyzer` produce `result.decision` directly and only inspect `PolicyEngine` behavior through config and docs.

## What is intentionally not the public workflow

The public docs assume:

- adapters produce `GenerationRecord`
- `Analyzer` produces `UQResult`
- `result.decision` is the public decision path

You should not need to subclass internal scoring logic or reconstruct events by hand for normal use.

For decision routing and intervention strategies, see [Acting on decisions](acting_on_decisions.md).
