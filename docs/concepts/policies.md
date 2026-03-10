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

The default policy presets currently emit the core runtime actions such as `continue`, `continue_with_annotation`, `regenerate_segment`, `retry_step`, `retry_step_with_constraints`, `dry_run_verify`, `ask_user_confirmation`, and `block_execution`. The more integration-specific actions such as `escalate_to_human`, `emit_webhook`, and `custom` are mainly intended for `custom_rules` and userland dispatch.

## How to use actions in a real loop

The policy engine already writes the recommended action into:

- `result.decision.action` for the overall step
- `result.decision.segment_actions` for per-segment actions
- `segment.recommended_action` on each emitted segment

In practice:

- `continue` means proceed normally
- `continue_with_annotation` means proceed, but attach the result to logs or traces
- `regenerate_segment` means retry only the risky leaf or clause if your framework can do structured repair
- `retry_step` and `retry_step_with_constraints` mean rerun the model step
- `dry_run_verify`, `ask_user_confirmation`, and `block_execution` should be treated as protective gates before side effects

See [Acting on decisions](acting_on_decisions.md) for a fuller loop pattern.

## Which lever to change

Reach for configuration in this order:

1. `policy` if you want different default actions
2. `tolerance` if you want events to fire earlier or later
3. `thresholds` if you need numeric tuning for one metric or priority class
4. `custom_rules` if the defaults are mostly right but one segment/event case needs a specific override

## Custom rule example

```python
from agentuq import UQConfig

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

## Supported custom-rule semantics

The current implementation supports declarative `custom_rules` only. Each rule is matched against a segment before the built-in policy logic runs.

Supported `when` keys:

- `segment_kind`
- `segment_priority`
- `events_any`
- `severity_at_least`

Matching behavior:

- rules are checked in list order
- the first matching rule wins
- if no rule matches, built-in preset logic applies

Example:

```python
config = UQConfig(
    policy="balanced",
    custom_rules=[
        {
            "when": {
                "segment_kind": "browser_selector",
                "events_any": ["LOW_MARGIN_CLUSTER", "LOW_PROB_SPIKE"],
            },
            "then": "ask_user_confirmation",
        },
        {
            "when": {
                "segment_priority": "critical_action",
                "severity_at_least": "critical",
            },
            "then": "block_execution",
        },
    ],
)
```

Use `custom_rules` when the global preset is mostly correct but your workflow has a sharper requirement for one span type.

## What belongs where

| Field | Purpose | Typical user | Runtime effect |
| --- | --- | --- | --- |
| `policy` | Choose the default response to emitted events | Most users | Changes recommended actions |
| `tolerance` | Choose how easily events are emitted | Most users | Changes event sensitivity |
| `thresholds` | Override specific numeric trigger values | Advanced users | Overrides parts of the selected tolerance preset |
| `custom_rules` | Override default actions for matching cases | Advanced users | Overrides built-in policy actions |

## Practical defaults

- Start with `policy="balanced"` and `tolerance="strict"` for side-effectful workflows.
- Use `policy="conservative"` when you prefer confirmations and blocking over retries.
- Only start tuning `thresholds` after you have inspected a few real traces and know which metric is too sensitive.
