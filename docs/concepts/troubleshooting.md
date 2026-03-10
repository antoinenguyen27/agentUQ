---
title: Troubleshooting
description: Symptom-based fixes for missing logprobs, degraded capability, sampled runs, and live-test setup issues.
slug: /concepts/troubleshooting
sidebar_position: 11
---

# Troubleshooting

## Requested logprobs but response omitted them

This usually means the model, routed provider, or framework call path did not actually return token details. AgentUQ raises `SelectedTokenLogprobsUnavailableError` by default.

## Top-k unavailable

Primary NLL scoring still works with selected-token logprobs only. AgentUQ emits `MISSING_TOPK` and degrades entropy and rank diagnostics.

If you want earlier event emission on borderline steps, set `tolerance="strict"` or override specific threshold values. If you want different responses to the same events, change `policy`.

For symptom-based tuning guidance, see [Tolerance](tolerance.md) and [Policies](policies.md).

## Canonical mode requested on sampled runs

AgentUQ downgrades to realized mode with `TEMPERATURE_MISMATCH` when degraded mode is allowed, or raises `UnsupportedForCanonicalModeError` when fail-loud behavior is configured. Use explicit greedy settings: `temperature=0` and `top_p=1`, and make sure those settings are visible in the captured request metadata.

## OpenRouter accepted the request but routed to a backend without logprob support

Set `provider.require_parameters=true` for UQ-critical runs and inspect routed provider metadata.

## LiteLLM dropped unsupported params

Do not use parameter dropping in UQ-critical paths. Pass `drop_params=False` and inspect `supported_openai_params` where available.

## Provider returned structure but no token details

Structured outputs without token logprobs are still useful for segmentation, but AgentUQ treats the run as capability tier `none` or degraded depending on config.

For a surface-by-surface view of what each provider or framework currently exposes, see [Provider and framework capabilities](provider_capabilities.md).

## Live tests are being skipped

Live tests are opt-in. Set `AGENTUQ_RUN_LIVE=1` and provide the relevant provider API keys in your local environment. Missing env vars produce explicit skip messages instead of failures.

## How to force fail-loud mode

```python
from agentuq import UQConfig

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
