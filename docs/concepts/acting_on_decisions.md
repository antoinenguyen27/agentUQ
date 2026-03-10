# Acting On Decisions

AgentUQ is most useful when `UQResult` leads directly to a runtime action.

The intended loop is:

1. capture a model response
2. analyze it
3. read `result.decision.action`
4. route the workflow based on that action

## The runtime contract

`Analyzer.analyze_step(...)` already produces a populated `result.decision` in the current implementation.

The two most important fields are:

- `result.decision.action`: the overall recommended action for the step
- `result.decision.segment_actions`: the per-segment action map

The overall action is the highest-severity action selected across segments. The per-segment map is useful when your framework can retry or verify only the risky span.

## Minimal loop

```python
from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig
from uq_runtime.schemas.results import Action

analyzer = Analyzer(UQConfig(policy="balanced", tolerance="strict"))
result = analyzer.analyze_step(record, capability_report)
decision = result.decision

if decision.action == Action.CONTINUE:
    proceed()
elif decision.action == Action.CONTINUE_WITH_ANNOTATION:
    attach_to_trace(result)
    proceed()
elif decision.action == Action.REGENERATE_SEGMENT:
    rerun_only_risky_field(result)
elif decision.action in {Action.RETRY_STEP, Action.RETRY_STEP_WITH_CONSTRAINTS}:
    retry_model_step(result)
elif decision.action == Action.DRY_RUN_VERIFY:
    validate_before_execution(result)
elif decision.action == Action.ASK_USER_CONFIRMATION:
    require_confirmation(result)
elif decision.action == Action.BLOCK_EXECUTION:
    raise RuntimeError("AgentUQ blocked this step before execution")
```

## What each action usually means

- `continue`
  Use the model output as normal.
- `continue_with_annotation`
  Proceed, but attach `result` to logs, traces, or monitoring.
- `regenerate_segment`
  Retry only the risky leaf or clause when the framework supports structured repair.
- `retry_step`
  Retry the whole model call with the same general structure.
- `retry_step_with_constraints`
  Retry the whole step with tighter instructions, lower temperature, schema reminders, or narrower decoding.
- `dry_run_verify`
  Run a safe validator before execution.
  Examples:
  SQL `EXPLAIN`, shell linting, selector existence checks, API argument validation.
- `ask_user_confirmation`
  Pause before side effects and show the risky span to the user or operator.
- `block_execution`
  Fail closed before any external action.
- `escalate_to_human`, `emit_webhook`, `custom`
  Reserved for workflows that want custom dispatch after `Decision` is returned. These are typically produced via `custom_rules` rather than the built-in preset logic.

## Picking the right implementation strategy

The right response depends on what your framework can actually do.

### If your framework supports structured repair

Use `regenerate_segment` for:

- JSON leaves
- tool argument leaves
- browser text fields
- individual SQL clauses when your system can rebuild only that clause safely

This is the highest-leverage path when only one field is risky and the rest of the step is acceptable.

### If your framework only supports whole-step retry

Map both `regenerate_segment` and `retry_step_with_constraints` to a full retry, but keep the distinction in your own prompt logic:

- `regenerate_segment`: retry with instructions that preserve the rest of the structure
- `retry_step_with_constraints`: retry with more global constraints because the action head itself looked unstable

### If the step has side effects

Use the protective actions as hard gates:

- `dry_run_verify` -> run a validator first
- `ask_user_confirmation` -> interrupt before execution
- `block_execution` -> fail closed

This is where AgentUQ has the clearest value over "just log it."

## Framework patterns

### Plain OpenAI / adapter usage

Use AgentUQ immediately after the model response and before any side effect:

```python
response = client.responses.create(...)
record = adapter.capture(response, request_meta)
result = analyzer.analyze_step(record, adapter.capability_report(response, request_meta))

if result.decision.action == Action.DRY_RUN_VERIFY:
    explain_sql_before_running(result)
```

### Wrapped OpenAI client

`UQWrappedOpenAI` already returns both the response and the computed decision.

```python
wrapped = UQWrappedOpenAI(client, UQConfig(policy="conservative", tolerance="strict"))
wrapped_result = wrapped.responses.create(...)

if wrapped_result.decision.action == Action.ASK_USER_CONFIRMATION:
    interrupt_before_side_effect(wrapped_result.result)
```

### LangGraph / LangChain

Attach `uq_result` to state or response metadata right after the model node. Then gate before tool execution.

The built-in helpers currently cover one narrow but important path:

- `enrich_graph_state(...)` stores the result
- `should_interrupt_before_tool(...)` returns `True` for tool-facing actions that should stop execution

If you need broader behavior than a boolean interrupt, read the stored `UQResult` from state and branch on `result.decision.action` directly.

## How to inspect the risky span

Use these fields together:

- `result.decision.action` for the overall step action
- `result.decision.segment_actions` for per-segment actions
- `result.segments` to inspect each segment's `kind`, `text`, `events`, and `recommended_action`
- `result.pretty()` for a human-readable trace or terminal view

This makes it easy to build operator prompts such as:

- "The generated SQL clause looked risky; run `EXPLAIN` before execution."
- "The selector span was uncertain; ask the user to confirm before clicking."
- "Only prose looked mildly uncertain; continue and annotate the trace."

## Which knob to change

Use the config levers in this order:

- `policy`
  Change what happens after events are emitted.
- `tolerance`
  Change how easily events are emitted.
- `thresholds`
  Fine-tune one metric or priority class numerically.
- `custom_rules`
  Override one specific segment/event case without changing the global preset.

This order matters. Most users should not jump straight to numeric threshold tuning.
