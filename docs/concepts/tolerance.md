# Tolerance

AgentUQ uses `tolerance` to control how easily it emits risk events. Action selection is configured separately with `policy`.

## Presets

- `strict`: emit events earlier. Use for higher-trust workflows and side-effectful steps.
- `balanced`: default. Uses the baseline threshold table.
- `lenient`: emit fewer events. Use when you want less intervention on low-signal steps.

## How presets work

Each preset maps to a full threshold table for:

- `low_margin_log`
- `entropy`
- `spike_surprise`
- `tail_surprise`
- `off_top1_rate`
- `action_head_surprise`
- `min_run`

`balanced` uses the library baseline. `strict` lowers the thresholds that trigger high-surprise style events and raises the thresholds that trigger low-margin style events, making emission more sensitive. `lenient` does the reverse.

## Overrides

You can override individual numeric values without replacing the whole preset:

```python
from agentuq import UQConfig

config = UQConfig(
    tolerance="strict",
    thresholds={
        "entropy": {"critical_action": 0.9},
        "min_run": 2,
    },
)
```

Partial overrides are allowed. Any missing values fall back to the selected tolerance preset.

## Tune from symptoms, not from raw numbers

Most users should not start by editing thresholds directly.

Use this order instead:

1. choose the right `policy`
2. choose the right `tolerance`
3. only then fine-tune `thresholds`
4. use `custom_rules` when one segment/event case needs a specific override

## Symptom-driven tuning guide

### "I am seeing too many prose annotations"

Try first:

- `tolerance="balanced"` or `tolerance="lenient"` if you started on `strict`

Only after that:

- adjust informational thresholds

Do not start by making critical-action thresholds lenient just to reduce prose noise.

### "The system is too passive on risky executable spans"

Try first:

- `tolerance="strict"`
- `policy="conservative"` if the workflow has meaningful side effects

If one span type still needs stronger handling:

- add a `custom_rule` for that segment kind

### "I keep getting confirmations when I would rather retry automatically"

Try first:

- a less conservative `policy`

Then consider:

- `custom_rules` for the specific segment kinds that should regenerate or retry instead of asking for confirmation

### "One metric seems too sensitive"

Only now reach for `thresholds`.

Examples:

- entropy is firing too often on informational prose -> tune `entropy["informational"]`
- low-margin clusters are not firing early enough on critical actions -> tune `low_margin_log["critical_action"]`

Threshold tuning works best when you already know which event is responsible.

### "Only one segment type needs different behavior"

Use `custom_rules`, not a full preset change.

That keeps the rest of the workflow stable while sharpening one special case.

For action behavior, see [Policies](policies.md). For end-to-end routing, see [Acting on decisions](acting_on_decisions.md).
