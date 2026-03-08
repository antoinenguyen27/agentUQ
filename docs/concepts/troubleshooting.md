# Troubleshooting

## Requested logprobs but response omitted them

This usually means the model, routed provider, or framework call path did not actually return token details. AgentUQ raises `SelectedTokenLogprobsUnavailableError` by default.

## Top-k unavailable

Primary NLL scoring still works with selected-token logprobs only. AgentUQ emits `MISSING_TOPK` and degrades entropy and rank diagnostics.

## Canonical mode requested on sampled runs

AgentUQ downgrades to realized mode with `TEMPERATURE_MISMATCH` when degraded mode is allowed, or raises `UnsupportedForCanonicalModeError` when fail-loud behavior is configured. Use explicit greedy settings: `temperature=0`, `top_p=1`, and deterministic metadata.

## OpenRouter accepted the request but routed to a backend without logprob support

Set `provider.require_parameters=true` for UQ-critical runs and inspect routed provider metadata.

## LiteLLM dropped unsupported params

Do not use parameter dropping in UQ-critical paths. Pass `drop_params=False` and inspect `supported_openai_params` where available.

## Provider returned structure but no token details

Structured outputs without token logprobs are still useful for segmentation, but AgentUQ treats the run as capability tier `none` or degraded depending on config.

## How to force fail-loud mode

```python
from uq_runtime.schemas.config import UQConfig

config = UQConfig(
    capability={
        "require_logprobs": True,
        "require_topk": True,
        "fail_on_missing_logprobs": True,
        "fail_on_missing_topk": True,
        "allow_degraded_mode": False,
    }
)
```
