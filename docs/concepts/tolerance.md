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
from uq_runtime.schemas.config import UQConfig

config = UQConfig(
    tolerance="strict",
    thresholds={
        "entropy": {"critical_action": 0.9},
        "min_run": 2,
    },
)
```

Partial overrides are allowed. Any missing values fall back to the selected tolerance preset.
