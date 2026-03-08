# Policies

AgentUQ ships with preset policies and custom rules.

## Presets

- `balanced`: default. Annotate risky prose, regenerate risky leaves, retry or block unstable action heads.
- `conservative`: lower thresholds and more blocking for action-bearing segments.
- `aggressive`: fewer retries and more annotation, except for clearly critical action spans.

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

