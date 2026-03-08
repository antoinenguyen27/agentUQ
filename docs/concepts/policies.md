# Policies

AgentUQ uses `policy` to choose actions after events are emitted. Event sensitivity is configured separately with `tolerance`.

## Presets

- `balanced`: default. Annotate risky prose, regenerate risky leaves, retry or block unstable action heads.
- `conservative`: favor retries, confirmation, and blocking for action-bearing segments.
- `aggressive`: favor annotation or regeneration before confirmation/blocking, except for clearly critical action spans.

## Built-in actions

- `continue`
- `continue_with_annotation`
- `regenerate_segment`
- `retry_step`
- `retry_step_with_constraints`
- `dry_run_verify`
- `ask_user_confirmation`
- `block_execution`
- `escalate_to_human`
- `emit_webhook`
- `custom`

## Custom rule example

```python
from uq_runtime.schemas.config import UQConfig

config = UQConfig(
    policy="balanced",
    tolerance="strict",
    custom_rules=[
        {
            "when": {
                "segment_kind": "sql_clause",
                "events_any": ["LOW_PROB_SPIKE"],
            },
            "then": "dry_run_verify",
        }
    ]
)
```

## What belongs where

| Field | Purpose | Typical user | Runtime effect |
| --- | --- | --- | --- |
| `policy` | Choose the default response to emitted events | Most users | Changes recommended actions |
| `tolerance` | Choose how easily events are emitted | Most users | Changes event sensitivity |
| `thresholds` | Override specific numeric trigger values | Advanced users | Overrides parts of the selected tolerance preset |
| `custom_rules` | Override default actions for matching cases | Advanced users | Overrides built-in policy actions |
